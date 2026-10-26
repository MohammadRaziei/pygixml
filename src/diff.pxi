# diff.pxi
# --------
# Ordered tree diff for XML/HTML. The algorithm lives in the verbatim C++ block below (matching by
# key / identical subtree / pq-gram similarity, then Chawathe's edit script);
# this file only unpacks arguments and turns the result into Python objects.
# One C++ call does the whole job. Text inside updated nodes can be diffed
# word by word (the same LCS as the tree matching).

from collections import namedtuple

cdef extern from *:
    r"""
// Ordered tree diff for XML/HTML.
//
// Two phases, in the spirit of "Change Detection in Hierarchically Structured
// Information" (Chawathe et al. 1996) and of the findings in Cobena et al.'s
// comparative study of XML diff tools (fast, near-minimal results come from
// per-level LCS, not from global optimal matching):
//
//  1. MATCHING, top-down. For each matched pair of parents, the children are
//     paired by (a) key attribute (e.g. id), (b) identical subtree hash via an
//     LCS over the hash sequences, (c) similarity of what is left in each gap,
//     using pq-gram profiles (pygixml_embed, in embedding.pxi) for elements and character
//     bigrams for text. Optionally (d) unmatched subtrees are re-paired across
//     parents (moves), first by identical hash, then by high pq-gram similarity.
//  2. EDIT SCRIPT, Chawathe's algorithm: walk the new tree breadth-first,
//     inserting / updating / moving nodes of a working copy of the old tree,
//     align the children of every node with an LIS, then delete what's left.
//     Because the working copy really is mutated, the script is correct by
//     construction, and the result is checked against the new tree's hash
//     before returning (a mismatch is a bug, reported as an error).
//
// Text inside updated nodes can additionally be diffed word by word (an LCS over
// word tokens, the same LCS the tree matching uses).
//
// ponytail: the text diff is word-level (readable, and reuses lcs_pairs); a
// character-level Myers diff with semantic clean-up is the upgrade path.
// LCS is an O(n*m) table below a size cap and a greedy monotone
// match above it (DeltaXML-style Myers/Wu O(ND) is the upgrade path);
// elements never get renamed (a different tag is delete + insert); no
// cross-parent move for a subtree that is both moved and edited.

#include <deque>
#include <stdexcept>
#include <unordered_map>


namespace pygixml_diff {

using pygixml_tree::Tree;
using pygixml_tree::Options;
using pygixml_tree::Kind;
using pygixml_tree::ELEM;
using pygixml_tree::TEXT;
using pygixml_tree::COMMENT;
using pygixml_tree::DOC;

struct Config {
    bool moves = true;                // look for subtrees that moved to another parent
    bool text_diff = false;           // attach a word diff to UpdateText
    double threshold = 0.5;           // min similarity to pair two changed siblings
    double move_threshold = 0.8;      // min similarity to pair a moved-and-edited subtree
    int move_min_size = 2;            // smallest subtree considered for moves
    int p = 2, q = 3;                 // pq-gram shape
};

enum ActionKind { INSERT = 0, INSERT_TEXT, DELETE, MOVE, UPDATE_TEXT, SET_ATTRIB, DELETE_ATTRIB };

struct Action {
    int kind = 0;
    std::string path;                 // node acted on (parent for inserts)
    std::string a, b, c;              // see diff.pxi for the meaning per kind
    int pos = -1;
    std::vector<std::pair<int, std::string>> tdiff;   // -1 delete, 0 equal, +1 insert
};

// Dice coefficient of character bigrams -- cheap similarity for text nodes.
static inline double bigram_dice(const std::string& a, const std::string& b) {
    if (a == b) return 1.0;
    if (a.size() < 2 || b.size() < 2) return 0.0;
    std::vector<uint32_t> x, y;
    for (size_t i = 0; i + 1 < a.size(); ++i) x.push_back((static_cast<unsigned char>(a[i]) << 8) | static_cast<unsigned char>(a[i + 1]));
    for (size_t i = 0; i + 1 < b.size(); ++i) y.push_back((static_cast<unsigned char>(b[i]) << 8) | static_cast<unsigned char>(b[i + 1]));
    std::sort(x.begin(), x.end()); std::sort(y.begin(), y.end());
    size_t i = 0, j = 0, inter = 0;
    while (i < x.size() && j < y.size()) {
        if (x[i] == y[j]) { ++inter; ++i; ++j; }
        else if (x[i] < y[j]) ++i; else ++j;
    }
    return 2.0 * static_cast<double>(inter) / static_cast<double>(x.size() + y.size());
}

// ------------------------------------------------------------------ LCS

// Longest common subsequence of two hash sequences, as (i, j) index pairs.
static inline std::vector<std::pair<int, int>> lcs_pairs(const std::vector<uint64_t>& x, const std::vector<uint64_t>& y) {
    std::vector<std::pair<int, int>> out;
    const int n = static_cast<int>(x.size()), m = static_cast<int>(y.size());
    int lo = 0;
    while (lo < n && lo < m && x[lo] == y[lo]) { out.emplace_back(lo, lo); ++lo; }
    int hn = n, hm = m;
    while (hn > lo && hm > lo && x[hn - 1] == y[hm - 1]) { --hn; --hm; }
    std::vector<std::pair<int, int>> tail;
    for (int i = hn, j = hm; i < n; ++i, ++j) tail.emplace_back(i, j);
    const int rn = hn - lo, rm = hm - lo;
    if (rn > 0 && rm > 0) {
        if (static_cast<int64_t>(rn) * rm <= 4000000) {       // exact LCS table
            std::vector<uint16_t> t(static_cast<size_t>(rn + 1) * (rm + 1), 0);
            auto at = [&](int i, int j) -> uint16_t& { return t[static_cast<size_t>(i) * (rm + 1) + j]; };
            for (int i = rn - 1; i >= 0; --i)
                for (int j = rm - 1; j >= 0; --j)
                    at(i, j) = x[lo + i] == y[lo + j] ? at(i + 1, j + 1) + 1 : std::max(at(i + 1, j), at(i, j + 1));
            for (int i = 0, j = 0; i < rn && j < rm;) {
                if (x[lo + i] == y[lo + j]) { out.emplace_back(lo + i, lo + j); ++i; ++j; }
                else if (at(i + 1, j) >= at(i, j + 1)) ++i;
                else ++j;
            }
        } else {                                              // greedy monotone match
            std::unordered_map<uint64_t, std::vector<int>> pos;
            for (int j = lo; j < hm; ++j) pos[y[j]].push_back(j);
            std::unordered_map<uint64_t, size_t> cur;
            int last = lo - 1;
            for (int i = lo; i < hn; ++i) {
                auto it = pos.find(x[i]);
                if (it == pos.end()) continue;
                size_t& c = cur[x[i]];
                while (c < it->second.size() && it->second[c] <= last) ++c;
                if (c < it->second.size()) { out.emplace_back(i, it->second[c]); last = it->second[c]; ++c; }
            }
        }
    }
    out.insert(out.end(), tail.begin(), tail.end());
    return out;
}

// ------------------------------------------------------------------ word diff

// Tokens: runs of word characters, runs of whitespace, single punctuation marks,
// and single characters from the CJK ranges (no spaces to split on there).
static inline std::vector<std::string> tokenize(const std::string& s) {
    std::vector<std::string> out;
    size_t i = 0;
    while (i < s.size()) {
        const size_t start = i;
        const unsigned char c = static_cast<unsigned char>(s[i]);
        if (c < 0x80 && pygixml_html::is_ws(static_cast<char>(c))) {
            while (i < s.size() && pygixml_html::is_ws(s[i])) ++i;
        } else if (c < 0x80 && !pygixml_html::is_alnum(static_cast<char>(c)) && c != '_') {
            ++i;
        } else {
            size_t j = i;
            uint32_t cp = pygixml_html::get_utf8(s, j);
            if (cp >= 0x2E80) i = j;                         // CJK & co: one character per token
            else {
                while (i < s.size()) {
                    const unsigned char d = static_cast<unsigned char>(s[i]);
                    if (d < 0x80 && !(pygixml_html::is_alnum(static_cast<char>(d)) || d == '_')) break;
                    size_t k = i;
                    if (d >= 0x80 && pygixml_html::get_utf8(s, k) >= 0x2E80) break;
                    i = d < 0x80 ? i + 1 : k;
                }
            }
        }
        out.push_back(s.substr(start, i - start));
    }
    return out;
}

// -1 delete, 0 keep, +1 insert pieces; within a changed stretch deletes come first.
static inline std::vector<std::pair<int, std::string>> text_diff(const std::string& a, const std::string& b) {
    std::vector<std::string> ta = tokenize(a), tb = tokenize(b);
    std::vector<uint64_t> ha, hb;
    for (auto& t : ta) ha.push_back(pygixml_tree::hash_str(t));
    for (auto& t : tb) hb.push_back(pygixml_tree::hash_str(t));
    std::vector<std::pair<int, std::string>> out;
    auto add = [&](int op, const std::string& t) {
        if (!out.empty() && out.back().first == op) out.back().second += t;
        else out.emplace_back(op, t);
    };
    size_t i = 0, j = 0;
    for (const auto& pr : lcs_pairs(ha, hb)) {
        for (; i < static_cast<size_t>(pr.first); ++i) add(-1, ta[i]);
        for (; j < static_cast<size_t>(pr.second); ++j) add(1, tb[j]);
        add(0, ta[i++]); ++j;
    }
    for (; i < ta.size(); ++i) add(-1, ta[i]);
    for (; j < tb.size(); ++j) add(1, tb[j]);
    return out;
}

// Longest increasing subsequence; returns the indices (into seq) that are kept.
static inline std::vector<int> lis(const std::vector<int>& seq) {
    std::vector<int> tails, tail_idx, prev(seq.size(), -1);
    for (size_t i = 0; i < seq.size(); ++i) {
        size_t k = std::lower_bound(tails.begin(), tails.end(), seq[i]) - tails.begin();
        if (k == tails.size()) { tails.push_back(seq[i]); tail_idx.push_back(static_cast<int>(i)); }
        else { tails[k] = seq[i]; tail_idx[k] = static_cast<int>(i); }
        prev[i] = k ? tail_idx[k - 1] : -1;
    }
    std::vector<int> keep;
    for (int i = tail_idx.empty() ? -1 : tail_idx.back(); i >= 0; i = prev[i]) keep.push_back(i);
    std::reverse(keep.begin(), keep.end());
    return keep;
}

// ------------------------------------------------------------------ matching

struct Matcher {
    const Tree &A, &B;
    const Config& cfg;
    std::vector<int> m1, m2;                       // partner of each node, or -1
    std::vector<std::vector<uint64_t>> pa, pb;     // lazily computed content profiles
    std::vector<char> ha, hb;
    std::vector<std::pair<int, int>> todo;         // matched pairs whose children still need pairing
    pygixml_embed::Params prm;

    Matcher(const Tree& a, const Tree& b, const Config& c)
        : A(a), B(b), cfg(c), m1(a.n(), -1), m2(b.n(), -1), pa(a.n()), pb(b.n()), ha(a.n(), 0), hb(b.n(), 0) {
        prm.p = c.p; prm.q = c.q; prm.content = true;
    }

    void link(int a, int b) { m1[a] = b; m2[b] = a; }

    void link_identical(int a, int b) {            // equal hashes: same shape, pair node by node
        std::vector<std::pair<int, int>> st{{a, b}};
        while (!st.empty()) {
            auto pr = st.back(); st.pop_back();
            link(pr.first, pr.second);
            const auto &ca = A.children[pr.first], &cb = B.children[pr.second];
            for (size_t i = 0; i < std::min(ca.size(), cb.size()); ++i) st.emplace_back(ca[i], cb[i]);
        }
    }

    const std::vector<uint64_t>& profA(int a) { if (!ha[a]) { pa[a] = pygixml_embed::profile(A, a, prm); ha[a] = 1; } return pa[a]; }
    const std::vector<uint64_t>& profB(int b) { if (!hb[b]) { pb[b] = pygixml_embed::profile(B, b, prm); hb[b] = 1; } return pb[b]; }

    bool compatible(int a, int b) const {
        return A.kind[a] == B.kind[b] && (A.kind[a] != ELEM || A.label[a] == B.label[b]);
    }
    double similarity(int a, int b) {
        if (A.kind[a] == ELEM) return pygixml_embed::dice(profA(a), profB(b));
        return bigram_dice(A.label[a], B.label[b]);
    }

    void pair_up(int a, int b) {                   // matched, maybe changed
        link(a, b);
        if (A.hash[a] == B.hash[b]) link_identical(a, b);
        else todo.emplace_back(a, b);
    }

    // Pair the unmatched nodes of one gap between two anchors.
    void align_gap(const std::vector<int>& la, const std::vector<int>& lb) {
        const int n = static_cast<int>(la.size()), m = static_cast<int>(lb.size());
        std::unordered_map<std::string, int> ca, cb;           // how many of each tag in this gap
        auto tag = [&](const Tree& t, int u) { return std::to_string(t.kind[u]) + (t.kind[u] == ELEM ? t.label[u] : ""); };
        for (int a : la) ++ca[tag(A, a)];
        for (int b : lb) ++cb[tag(B, b)];
        if (static_cast<int64_t>(n) * m > 1000000) {            // big gap: pair by tag, in order
            std::unordered_map<std::string, std::vector<int>> by;
            for (int j = 0; j < m; ++j) by[tag(B, lb[j])].push_back(j);
            std::unordered_map<std::string, size_t> cur;
            int last = -1;
            for (int i = 0; i < n; ++i) {
                auto it = by.find(tag(A, la[i]));
                if (it == by.end()) continue;
                size_t& c = cur[it->first];
                while (c < it->second.size() && it->second[c] <= last) ++c;
                if (c < it->second.size()) { last = it->second[c]; pair_up(la[i], lb[last]); ++c; }
            }
            return;
        }
        std::vector<double> w(static_cast<size_t>(n) * m, 0.0);
        for (int i = 0; i < n; ++i)
            for (int j = 0; j < m; ++j) {
                int a = la[i], b = lb[j];
                if (!compatible(a, b)) continue;
                double s = similarity(a, b);
                bool unique = ca[tag(A, a)] == 1 && cb[tag(B, b)] == 1;   // the only one of its kind: an update
                double need = A.kind[a] == ELEM ? cfg.threshold : 0.4;
                if (s >= need || unique) w[static_cast<size_t>(i) * m + j] = std::max(s, 0.05);
            }
        std::vector<double> t(static_cast<size_t>(n + 1) * (m + 1), 0.0);
        auto at = [&](int i, int j) -> double& { return t[static_cast<size_t>(i) * (m + 1) + j]; };
        for (int i = n - 1; i >= 0; --i)
            for (int j = m - 1; j >= 0; --j) {
                double best = std::max(at(i + 1, j), at(i, j + 1));
                double s = w[static_cast<size_t>(i) * m + j];
                if (s > 0) best = std::max(best, s + at(i + 1, j + 1));
                at(i, j) = best;
            }
        for (int i = 0, j = 0; i < n && j < m;) {
            double s = w[static_cast<size_t>(i) * m + j];
            if (s > 0 && at(i, j) == s + at(i + 1, j + 1)) { pair_up(la[i], lb[j]); ++i; ++j; }
            else if (at(i + 1, j) >= at(i, j + 1)) ++i;
            else ++j;
        }
    }

    void process(int a, int b) {
        const auto &ca = A.children[a], &cb = B.children[b];
        // (a) key attributes: the same id means the same element, wherever it sits
        std::unordered_map<std::string, int> kb;
        for (int j : cb) {
            if (B.kind[j] != ELEM || B.key[j].empty()) continue;
            auto it = kb.find(B.key[j]);
            if (it == kb.end()) kb.emplace(B.key[j], j);
            else it->second = -2;                              // duplicate key: ambiguous, don't use it
        }
        for (int i : ca) {
            if (A.kind[i] != ELEM || A.key[i].empty()) continue;
            auto it = kb.find(A.key[i]);
            if (it == kb.end() || it->second < 0 || m2[it->second] != -1 || m1[i] != -1) continue;
            if (A.label[i] == B.label[it->second]) pair_up(i, it->second);
        }
        // (b) identical subtrees, LCS over hash sequences of what is left
        std::vector<int> ra, rb;
        std::vector<uint64_t> ha_, hb_;
        for (int i : ca) if (m1[i] == -1) { ra.push_back(i); ha_.push_back(A.hash[i]); }
        for (int j : cb) if (m2[j] == -1) { rb.push_back(j); hb_.push_back(B.hash[j]); }
        auto anchors = lcs_pairs(ha_, hb_);
        std::vector<char> ua(ra.size(), 0), ub(rb.size(), 0);
        for (auto& pr : anchors) { link_identical(ra[pr.first], rb[pr.second]); ua[pr.first] = ub[pr.second] = 1; }
        // (c) what is left between consecutive anchors: pair by similarity
        std::vector<std::vector<int>> ga(anchors.size() + 1), gb(anchors.size() + 1);
        size_t g = 0;
        for (size_t i = 0; i < ra.size(); ++i) { if (ua[i]) ++g; else ga[g].push_back(ra[i]); }
        g = 0;
        for (size_t j = 0; j < rb.size(); ++j) { if (ub[j]) ++g; else gb[g].push_back(rb[j]); }
        for (size_t k = 0; k < ga.size(); ++k)
            if (!ga[k].empty() && !gb[k].empty()) align_gap(ga[k], gb[k]);
    }

    void drain() {
        while (!todo.empty()) { auto pr = todo.back(); todo.pop_back(); process(pr.first, pr.second); }
    }

    // (d) subtrees that left their parent: identical ones first, then very similar ones
    void find_moves() {
        std::vector<int> ua, ub;
        for (int a : A.pre) if (m1[a] == -1 && A.parent[a] >= 0 && m1[A.parent[a]] != -1 && static_cast<int>(A.size[a]) >= cfg.move_min_size) ua.push_back(a);
        for (int b : B.pre) if (m2[b] == -1 && B.parent[b] >= 0 && m2[B.parent[b]] != -1 && static_cast<int>(B.size[b]) >= cfg.move_min_size) ub.push_back(b);
        std::unordered_map<uint64_t, std::vector<int>> by;
        for (int b : ub) by[B.hash[b]].push_back(b);
        std::vector<int> rest_a;
        for (int a : ua) {
            auto it = by.find(A.hash[a]);
            bool done = false;
            if (it != by.end())
                for (int b : it->second) if (m2[b] == -1) { link_identical(a, b); done = true; break; }
            if (!done) rest_a.push_back(a);
        }
        std::vector<int> rest_b;
        for (int b : ub) if (m2[b] == -1) rest_b.push_back(b);
        if (static_cast<int64_t>(rest_a.size()) * rest_b.size() <= 250000) {
            for (int a : rest_a) {
                int best = -1; double bs = cfg.move_threshold;
                for (int b : rest_b) {
                    if (m2[b] != -1 || !compatible(a, b) || A.kind[a] != ELEM) continue;
                    double s = similarity(a, b);
                    if (s >= bs) { bs = s; best = b; }
                }
                if (best >= 0) pair_up(a, best);
            }
        }
    }

    void run() {
        link(0, 0);
        todo.emplace_back(0, 0);
        drain();
        if (cfg.moves) { find_moves(); drain(); }
    }
};

// ------------------------------------------------------------------ edit script

struct Script {
    const Tree &A, &B;
    const Config& cfg;
    std::vector<int> w2b, b2w;                    // working-tree node <-> new-tree node
    std::vector<uint8_t> wkind;
    std::vector<std::string> wlabel;
    std::vector<pygixml_tree::Attrs> wattrs;
    std::vector<int> wparent;
    std::vector<std::vector<int>> wchildren;
    std::vector<char> inW, inB, done, below;      // "in order" marks; subtree already created; matched at or below
    std::vector<Action> out;

    Script(const Tree& a, const Tree& b, const Config& c, const std::vector<int>& m1, const std::vector<int>& m2)
        : A(a), B(b), cfg(c), w2b(m1), b2w(m2), wkind(a.kind), wlabel(a.label), wattrs(a.attrs),
          wparent(a.parent), wchildren(a.children), inW(a.n(), 0), inB(b.n(), 0), done(b.n(), 0), below(b.n(), 0) {
        for (size_t i = B.pre.size(); i-- > 0;) {                // does anything at or under this node match?
            int u = B.pre[i];
            if (b2w[u] != -1) below[u] = 1;
            if (below[u] && B.parent[u] >= 0) below[B.parent[u]] = 1;
        }
    }

    // -- paths in the working tree: /ul[1]/li[2]/text()[1]
    std::string path(int w) const {
        std::vector<std::string> steps;
        for (int u = w; wparent[u] >= 0; u = wparent[u]) {
            int k = 0;
            for (int s : wchildren[wparent[u]]) {
                if (wkind[s] == wkind[u] && (wkind[u] != ELEM || wlabel[s] == wlabel[u])) ++k;
                if (s == u) break;
            }
            std::string step = wkind[u] == TEXT ? "text()" : wkind[u] == COMMENT ? "comment()" : wlabel[u];
            steps.push_back(step + "[" + std::to_string(k) + "]");
        }
        std::string p;
        for (size_t i = steps.size(); i-- > 0;) { p += '/'; p += steps[i]; }
        return p.empty() ? "/" : p;
    }

    int index_in_parent(int w) const {
        const auto& ch = wchildren[wparent[w]];
        return static_cast<int>(std::find(ch.begin(), ch.end(), w) - ch.begin());
    }

    int new_node(int kind, const std::string& label, const pygixml_tree::Attrs& attrs, int parent, int pos, int bnode) {
        int w = static_cast<int>(wkind.size());
        wkind.push_back(static_cast<uint8_t>(kind)); wlabel.push_back(label); wattrs.push_back(attrs);
        wparent.push_back(parent); wchildren.emplace_back(); w2b.push_back(bnode); inW.push_back(1);
        wchildren[parent].insert(wchildren[parent].begin() + pos, w);
        b2w[bnode] = w;
        return w;
    }

    // Where in the working parent must the partner of x go? Right after the
    // partner of the closest in-order left sibling.
    int find_pos(int x) const {
        const auto& sibs = B.children[B.parent[x]];
        for (int i = B.idx[x] - 1; i >= 0; --i)
            if (inB[sibs[i]]) return index_in_parent(b2w[sibs[i]]) + 1;
        return 0;
    }

    void detach(int w) {
        auto& ch = wchildren[wparent[w]];
        ch.erase(std::find(ch.begin(), ch.end(), w));
    }

    void move_to(int w, int x, int parent_w) {    // Move(path, new parent path, position)
        Action act; act.kind = MOVE;
        act.path = path(w);
        detach(w);
        act.a = path(parent_w);
        act.pos = find_pos(x);
        wchildren[parent_w].insert(wchildren[parent_w].begin() + act.pos, w);
        wparent[w] = parent_w;
        inW[w] = inB[x] = 1;
        out.push_back(std::move(act));
    }

    void update(int w, int x) {
        if (wkind[w] == TEXT || wkind[w] == COMMENT) {
            if (wlabel[w] != B.label[x]) {
                Action act; act.kind = UPDATE_TEXT; act.path = path(w); act.a = B.label[x]; act.b = wlabel[w];
                if (cfg.text_diff) act.tdiff = text_diff(wlabel[w], B.label[x]);
                out.push_back(std::move(act));
                wlabel[w] = B.label[x];
            }
            return;
        }
        const auto &oa = wattrs[w], &na = B.attrs[x];
        if (oa == na) return;
        std::string p;
        auto emit = [&](int kind, const std::string& name, const std::string& val, const std::string* old) {
            if (p.empty()) p = path(w);
            Action act; act.kind = kind; act.path = p; act.a = name; act.b = val;
            if (old) { act.c = *old; act.pos = 1; } else act.pos = 0;
            out.push_back(std::move(act));
        };
        size_t i = 0, j = 0;
        while (i < oa.size() || j < na.size()) {
            if (j >= na.size() || (i < oa.size() && oa[i].first < na[j].first)) { emit(DELETE_ATTRIB, oa[i].first, oa[i].second, nullptr); ++i; }
            else if (i >= oa.size() || na[j].first < oa[i].first) { emit(SET_ATTRIB, na[j].first, na[j].second, nullptr); ++j; }
            else { if (oa[i].second != na[j].second) emit(SET_ATTRIB, na[j].first, na[j].second, &oa[i].second); ++i; ++j; }
        }
        wattrs[w] = na;
    }

    void insert_fresh(int x, int zw) {            // x has no partner: create it (and, if all fresh, its subtree)
        int k = find_pos(x);
        Action act;
        act.path = path(zw); act.pos = k;
        if (B.kind[x] == TEXT) {
            act.kind = INSERT_TEXT; act.a = B.label[x];
            new_node(TEXT, B.label[x], {}, zw, k, x);
            out.push_back(std::move(act));
            done[x] = 1;
            inB[x] = 1;
            return;
        }
        act.kind = INSERT;
        if (!below[x]) {                          // whole subtree is new: one action, one xml string
            pygixml_tree::serialize(B, x, act.a);
            std::vector<std::pair<int, int>> st{{x, zw}};   // materialise it in the working tree
            bool first_node = true;
            while (!st.empty()) {
                auto pr = st.back(); st.pop_back();
                int w = new_node(B.kind[pr.first], B.label[pr.first], B.attrs[pr.first], pr.second,
                                 first_node ? k : static_cast<int>(wchildren[pr.second].size()), pr.first);
                first_node = false;
                done[pr.first] = 1;
                const auto& ch = B.children[pr.first];
                for (size_t i = ch.size(); i-- > 0;) st.emplace_back(ch[i], w);
            }
        } else {                                  // children are handled one by one, later
            if (B.kind[x] == COMMENT) pygixml_tree::serialize(B, x, act.a);
            else {                                  // the element alone, as an empty tag
                act.a = "<" + B.label[x];
                for (const auto& kv : B.attrs[x]) {
                    act.a += " " + kv.first + "=\"";
                    pygixml_html::escape(act.a, kv.second.data(), kv.second.size(), true);
                    act.a += "\"";
                }
                act.a += "/>";
            }
            new_node(B.kind[x], B.label[x], B.attrs[x], zw, k, x);
        }
        inB[x] = 1;
        out.push_back(std::move(act));
    }

    void align_children(int w, int x) {
        for (int c : wchildren[w]) inW[c] = 0;
        for (int c : B.children[x]) inB[c] = 0;
        std::vector<int> s1;                      // children of w matched to children of x, in w's order
        std::unordered_map<int, int> pos2;        // ... and their position in x's order
        int p = 0;
        for (int c : B.children[x]) if (b2w[c] != -1 && wparent[b2w[c]] == w) pos2[c] = p++;
        std::vector<int> seq;
        for (int c : wchildren[w]) if (w2b[c] != -1 && B.parent[w2b[c]] == x) { s1.push_back(c); seq.push_back(pos2[w2b[c]]); }
        for (int i : lis(seq)) { inW[s1[i]] = 1; inB[w2b[s1[i]]] = 1; }
        for (int b : B.children[x]) {
            if (b2w[b] == -1 || wparent[b2w[b]] != w || inB[b]) continue;
            move_to(b2w[b], b, w);
        }
    }

    void run() {
        std::deque<int> q{0};
        b2w[0] = 0; w2b[0] = 0;
        while (!q.empty()) {
            int x = q.front(); q.pop_front();
            int w;
            if (x == 0) w = 0;
            else {
                int zw = b2w[B.parent[x]];
                if (b2w[x] == -1) { insert_fresh(x, zw); w = b2w[x]; }
                else {
                    w = b2w[x];
                    update(w, x);
                    if (wparent[w] != zw) move_to(w, x, zw);
                }
            }
            if (done[x]) continue;                // fresh subtree: nothing left to do below it
            align_children(w, x);
            for (int c : B.children[x]) q.push_back(c);
        }
        // delete what is left (top-most unmatched nodes only: their subtrees go with them)
        std::vector<int> st{0};
        while (!st.empty()) {
            int u = st.back(); st.pop_back();
            for (size_t i = 0; i < wchildren[u].size();) {
                int c = wchildren[u][i];
                if (w2b[c] == -1) {
                    Action act; act.kind = DELETE; act.path = path(c);
                    out.push_back(std::move(act));
                    wchildren[u].erase(wchildren[u].begin() + i);
                } else { st.push_back(c); ++i; }
            }
        }
        verify();
    }

    // The working tree must now be the new tree. If not, that's a bug here.
    void verify() const {
        std::vector<int> pre, st{0};
        while (!st.empty()) { int u = st.back(); st.pop_back(); pre.push_back(u); for (int c : wchildren[u]) st.push_back(c); }
        std::vector<uint64_t> h(wkind.size(), 0);
        for (size_t i = pre.size(); i-- > 0;) {
            int u = pre[i];
            h[u] = pygixml_tree::node_hash(wkind[u], wlabel[u], wattrs[u], wchildren[u], h);
        }
        if (h[0] != B.hash[0]) throw std::runtime_error("internal error: the edit script does not reproduce the new tree");
    }
};

// ------------------------------------------------------------------ entry points

static inline std::vector<Action> diff(const pugi::xml_node& a, bool a_sib, const pugi::xml_node& b, bool b_sib,
                                       const Options& o, const Config& cfg) {
    Tree A = pygixml_tree::build(a, a_sib, o), B = pygixml_tree::build(b, b_sib, o);
    if (A.hash[0] == B.hash[0]) return {};
    Matcher m(A, B, cfg);
    m.run();
    Script s(A, B, cfg, m.m1, m.m2);
    s.run();
    return std::move(s.out);
}

static inline bool is_equal(const pugi::xml_node& a, bool a_sib, const pugi::xml_node& b, bool b_sib, const Options& o) {
    return pygixml_tree::build(a, a_sib, o).hash[0] == pygixml_tree::build(b, b_sib, o).hash[0];
}

}  // namespace pygixml_diff
    """
    cdef cppclass DiffConfig "pygixml_diff::Config":
        bint moves
        bint text_diff
        double threshold
        double move_threshold
        int move_min_size
        int p
        int q
    cdef cppclass DiffAction "pygixml_diff::Action":
        int kind
        string path
        string a
        string b
        string c
        int pos
        vector[pair[int, string]] tdiff
    vector[DiffAction] diff_cpp "pygixml_diff::diff"(
        const xml_node& a, bint a_sib, const xml_node& b, bint b_sib,
        const TreeOptions& o, const DiffConfig& c) except +
    bint is_equal_cpp "pygixml_diff::is_equal"(
        const xml_node& a, bint a_sib, const xml_node& b, bint b_sib,
        const TreeOptions& o) except +


# Edit actions. Paths look like /ul[1]/li[2]/text()[1] and refer to the tree as
# it is when that action runs (after the earlier ones), in the *normalised*
# view: blank text and (by default) comments are not there.
Insert = namedtuple("Insert", "parent position xml")
Insert.__doc__ = ("Insert the node described by `xml` (a whole new subtree, or just an "
                  "empty element when its children are moved/inserted by later actions) "
                  "as child number `position` (0-based) of `parent`.")
InsertText = namedtuple("InsertText", "parent position text")
InsertText.__doc__ = "Insert a text node as child number `position` of `parent`."
Delete = namedtuple("Delete", "path")
Delete.__doc__ = "Delete the node at `path` (with everything under it)."
Move = namedtuple("Move", "path parent position")
Move.__doc__ = ("Detach the node at `path`, then insert it as child number `position` of "
                "`parent` (`parent` is evaluated after the node has been detached).")
UpdateText = namedtuple("UpdateText", "path text old diff")
UpdateText.__doc__ = ("Replace the text of the node at `path`. `diff` is a list of "
                      "(-1 | 0 | 1, string) = delete / keep / insert pieces when "
                      "text_diff=True, else None.")
SetAttrib = namedtuple("SetAttrib", "path name value old")
SetAttrib.__doc__ = "Set attribute `name` (`old` is None when it is new)."
DeleteAttrib = namedtuple("DeleteAttrib", "path name old")
DeleteAttrib.__doc__ = "Remove attribute `name`."


cdef object _action(DiffAction& x):
    path = x.path.decode("utf-8", "replace")
    a = x.a.decode("utf-8", "replace")
    b = x.b.decode("utf-8", "replace")
    cdef int k = x.kind
    if k == 0:
        return Insert(path, x.pos, a)
    if k == 1:
        return InsertText(path, x.pos, a)
    if k == 2:
        return Delete(path)
    if k == 3:
        return Move(path, a, x.pos)
    if k == 4:
        pieces = [(piece.first, piece.second.decode("utf-8", "replace")) for piece in x.tdiff] if x.tdiff.size() else None
        return UpdateText(path, a, b, pieces)
    if k == 5:
        return SetAttrib(path, a, b, x.c.decode("utf-8", "replace") if x.pos == 1 else None)
    return DeleteAttrib(path, a, b)


def diff(a, b, *, bint ignore_whitespace=True, bint ignore_comments=True, ignore_attrs=(),
         bint class_as_set=True, keys=("id",), bint moves=True, bint text_diff=False,
         double threshold=0.5, double move_threshold=0.8, int move_min_size=2,
         int p=2, int q=3):
    """Edit script that turns tree ``a`` into tree ``b`` (ordered trees).

    Returns a list of :class:`Insert`, :class:`InsertText`, :class:`Delete`,
    :class:`Move`, :class:`UpdateText`, :class:`SetAttrib` and
    :class:`DeleteAttrib`; empty when the trees are equivalent. The script is
    verified inside the call: applying it to ``a`` yields exactly ``b`` (as
    normalised below), otherwise :class:`PygiXMLDiffError` is raised.

    How nodes are paired, per matched pair of parents: elements with the same
    *key* attribute; subtrees with identical hash (an LCS over the hash
    sequences); then whatever is left between those anchors, by pq-gram
    similarity for elements and character-bigram similarity for text. With
    ``moves`` (default), unmatched subtrees are also paired across parents,
    identical ones first and then ones at least ``move_threshold`` similar.

    Normalisation (what counts as "the same", the idea behind html-differ):

    Args:
        a, b: an :class:`XMLNode` or :class:`XMLDocument`. For HTML, pass
            what :func:`parse_html` returns.
        ignore_whitespace: drop blank text; trim and collapse runs of
            whitespace elsewhere.
        ignore_comments: leave comments out of the comparison.
        ignore_attrs: attribute names to ignore; a trailing ``*`` is a prefix
            (``"data-*"``). May be a single string.
        class_as_set: compare ``class`` as a set of names (order and
            repeats don't matter). Attribute order never matters.
        keys: attributes that identify an element (``("id",)`` by default);
            elements with the same key are paired wherever they are.
        moves: detect subtrees moved to another parent.
        text_diff: put a word-level diff in ``UpdateText.diff``.
        threshold: minimum similarity (0..1) to pair two changed siblings
            that are not the only ones of their tag in the gap.
        move_threshold: minimum similarity to pair a moved-*and*-edited subtree.
        move_min_size: smallest subtree (node count) considered for moves.
        p, q: pq-gram shape used for the similarity.

    Raises:
        PygiXMLDiffError: not a node/document, null node, invalid option, or
            an internal consistency failure.
    """
    cdef xml_node fa, fb
    cdef bint sa, sb
    _unpack_tree(a, &fa, &sa)
    _unpack_tree(b, &fb, &sb)
    if not 0.0 <= threshold <= 1.0 or not 0.0 <= move_threshold <= 1.0:
        raise PygiXMLDiffError("threshold and move_threshold must be between 0 and 1")
    if p < 1 or q < 1:
        raise PygiXMLDiffError("p and q must be at least 1")
    cdef TreeOptions o = _tree_options(ignore_whitespace, ignore_comments, class_as_set, ignore_attrs, keys)
    cdef DiffConfig c
    c.moves = moves
    c.text_diff = text_diff
    c.threshold = threshold
    c.move_threshold = move_threshold
    c.move_min_size = move_min_size
    c.p = p
    c.q = q
    cdef vector[DiffAction] acts
    try:
        acts = diff_cpp(fa, sa, fb, sb, o, c)
    except RuntimeError as e:
        raise PygiXMLDiffError(str(e)) from e
    return [_action(x) for x in acts]


def is_equal(a, b, *, bint ignore_whitespace=True, bint ignore_comments=True, ignore_attrs=(),
             bint class_as_set=True):
    """Are two trees equivalent after normalisation? (same options as
    :func:`diff`). One C++ call, linear time: it compares subtree hashes, so
    it is the cheap way to ask "did anything change?" before computing a diff.

    Raises:
        PygiXMLDiffError: not a node/document, or a null node.
    """
    cdef xml_node fa, fb
    cdef bint sa, sb
    _unpack_tree(a, &fa, &sa)
    _unpack_tree(b, &fb, &sb)
    cdef TreeOptions o = _tree_options(ignore_whitespace, ignore_comments, class_as_set, ignore_attrs, ())
    return is_equal_cpp(fa, sa, fb, sb, o)
