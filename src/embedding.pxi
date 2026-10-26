# embedding.pxi
# -------------
# Structural "embeddings" of trees: a tree becomes a bag of hashes (a sparse
# vector), and two bags compare with a Dice coefficient. Also the helpers
# shared with diff.pxi: node unpacking, normalisation options, the error class.
# All work happens in C++ (the verbatim block below: a flat normalised tree with
# subtree hashes, then the embeddings), one call per function.

from libc.stdint cimport uint32_t, uint64_t
from libcpp.utility cimport pair

cdef extern from *:
    r"""
// A flat, normalised copy of an XML/HTML tree for comparison.
//
// Built once in C++ from a pugixml node (no Python in the loop). Normalisation
// is where "html-differ"-style equivalence lives: ignore blank text, collapse
// whitespace, ignore comments, ignore chosen attributes, compare `class` as a
// set, attribute order never matters. Every node carries a 64-bit hash of its
// whole subtree, so "are these two subtrees identical" is one integer compare.
//
// ponytail: subtree hashes are 64-bit and equality is trusted (2^-64 collision
// odds per pair). Upgrade path if that ever matters: verify with a parallel
// walk before linking identical subtrees.

#include <algorithm>
#include <cstdint>
#include <string>
#include <utility>
#include <vector>

#include "pugixml.hpp"

namespace pygixml_tree {

enum Kind : uint8_t { DOC = 0, ELEM = 1, TEXT = 2, COMMENT = 3 };

struct Options {
    bool ignore_whitespace = true;        // drop blank text, trim + collapse runs of whitespace
    bool ignore_comments = true;
    bool class_as_set = true;             // class="b a a" == class="a b"
    std::vector<std::string> ignore_attrs;   // exact names, or a prefix ending in '*'
    std::vector<std::string> keys;           // attributes that identify an element (e.g. "id")
};

using Attrs = std::vector<std::pair<std::string, std::string>>;

// ------------------------------------------------------------------ hashing

static inline uint64_t mix64(uint64_t x) {
    x ^= x >> 30; x *= 0xbf58476d1ce4e5b9ULL;
    x ^= x >> 27; x *= 0x94d049bb133111ebULL;
    x ^= x >> 31;
    return x;
}
static inline uint64_t combine(uint64_t h, uint64_t v) { return mix64(h ^ (v + 0x9e3779b97f4a7c15ULL + (h << 6) + (h >> 2))); }
static inline uint64_t hash_str(const std::string& s, uint64_t seed = 0xcbf29ce484222325ULL) {
    uint64_t h = seed;
    for (unsigned char c : s) { h ^= c; h *= 0x100000001b3ULL; }
    return mix64(h);
}

// Hash of one node given its own data and its children's subtree hashes.
static inline uint64_t node_hash(uint8_t kind, const std::string& label, const Attrs& attrs,
                                 const std::vector<int>& children, const std::vector<uint64_t>& hashes) {
    uint64_t h = hash_str(label, 0x1000 + kind);
    for (const auto& kv : attrs) h = combine(combine(h, hash_str(kv.first)), hash_str(kv.second, 7));
    for (int c : children) h = combine(h, hashes[c]);
    return combine(h, children.size());
}

// ------------------------------------------------------------------- tree

struct Tree {
    std::vector<uint8_t> kind;
    std::vector<std::string> label;        // element name, or text/comment content
    std::vector<Attrs> attrs;              // sorted by name
    std::vector<int> parent, idx;          // idx: position in parent's children
    std::vector<std::vector<int>> children;
    std::vector<uint64_t> hash;            // subtree hash
    std::vector<uint32_t> size;            // nodes in the subtree
    std::vector<std::string> key;          // "name=value" of the first key attribute, else ""
    std::vector<int> pre;                  // live nodes, parents before children (node 0 = document)

    int n() const { return static_cast<int>(kind.size()); }
    int add(uint8_t k, std::string lab, int par) {
        kind.push_back(k); label.push_back(std::move(lab)); attrs.emplace_back();
        parent.push_back(par); idx.push_back(0); children.emplace_back();
        hash.push_back(0); size.push_back(1); key.emplace_back();
        return n() - 1;
    }
};

static inline std::string collapse_ws(const std::string& s) {
    std::string out;
    bool pending = false;
    for (char c : s) {
        if (pygixml_html::is_ws(c)) { pending = !out.empty(); continue; }
        if (pending) { out += ' '; pending = false; }
        out += c;
    }
    return out;
}

static inline bool ignored_attr(const std::string& name, const Options& o) {
    for (const auto& p : o.ignore_attrs) {
        if (!p.empty() && p.back() == '*') { if (name.compare(0, p.size() - 1, p, 0, p.size() - 1) == 0) return true; }
        else if (name == p) return true;
    }
    return false;
}

static inline std::string normalise_class(const std::string& v) {
    std::vector<std::string> words;
    std::string cur;
    for (char c : v) {
        if (pygixml_html::is_ws(c)) { if (!cur.empty()) { words.push_back(cur); cur.clear(); } }
        else cur += c;
    }
    if (!cur.empty()) words.push_back(cur);
    std::sort(words.begin(), words.end());
    words.erase(std::unique(words.begin(), words.end()), words.end());
    std::string out;
    for (auto& w : words) { if (!out.empty()) out += ' '; out += w; }
    return out;
}

// `first`: first top-level node; with `siblings`, every following sibling too
// (a document / a node's children). Without, `first` alone.
static inline Tree build(const pugi::xml_node& first, bool siblings, const Options& o) {
    Tree t;
    t.add(DOC, "", -1);
    struct Frame { pugi::xml_node next; int id; bool one; };
    std::vector<Frame> st;
    st.push_back({first, 0, !siblings});
    while (!st.empty()) {
        Frame& f = st.back();
        if (!f.next) {
            int id = f.id;
            auto& ch = t.children[id];
            if (o.ignore_whitespace) {               // normalise text, drop what becomes blank
                std::vector<int> keep;
                for (int c : ch) {
                    if (t.kind[c] == TEXT) {
                        t.label[c] = collapse_ws(t.label[c]);
                        if (t.label[c].empty()) continue;
                    }
                    keep.push_back(c);
                }
                ch.swap(keep);
            }
            st.pop_back();
            continue;
        }
        pugi::xml_node c = f.next;
        f.next = f.one ? pugi::xml_node() : c.next_sibling();
        int pid = f.id;
        switch (c.type()) {
            case pugi::node_element: {
                int id = t.add(ELEM, c.name(), pid);
                for (pugi::xml_attribute a = c.first_attribute(); a; a = a.next_attribute()) {
                    std::string name = a.name();
                    if (t.key[id].empty())
                        for (const auto& k : o.keys) if (k == name) { t.key[id] = name + "=" + a.value(); break; }
                    if (ignored_attr(name, o)) continue;
                    std::string val = a.value();
                    if (o.class_as_set && name == "class") val = normalise_class(val);
                    t.attrs[id].emplace_back(std::move(name), std::move(val));
                }
                std::sort(t.attrs[id].begin(), t.attrs[id].end());
                t.children[pid].push_back(id);
                st.push_back({c.first_child(), id, false});
                break;
            }
            case pugi::node_pcdata:
            case pugi::node_cdata: {
                const auto& last = t.children[pid];
                if (!last.empty() && t.kind[last.back()] == TEXT) { t.label[last.back()] += c.value(); break; }   // adjacent text merges
                int id = t.add(TEXT, c.value(), pid);          // (add() may reallocate: take no reference across it)
                t.children[pid].push_back(id);
                break;
            }
            case pugi::node_comment:
                if (!o.ignore_comments) { int id = t.add(COMMENT, c.value(), pid); t.children[pid].push_back(id); }
                break;
            default: break;   // doctype, <?pi?>, declaration
        }
    }

    // live nodes in preorder, positions, then hashes/sizes bottom-up
    std::vector<int> stack{0};
    while (!stack.empty()) {
        int u = stack.back(); stack.pop_back();
        t.pre.push_back(u);
        auto& ch = t.children[u];
        for (size_t i = 0; i < ch.size(); ++i) t.idx[ch[i]] = static_cast<int>(i);
        for (size_t i = ch.size(); i-- > 0;) stack.push_back(ch[i]);
    }
    for (size_t i = t.pre.size(); i-- > 0;) {
        int u = t.pre[i];
        for (int c : t.children[u]) t.size[u] += t.size[c];
        t.hash[u] = node_hash(t.kind[u], t.label[u], t.attrs[u], t.children[u], t.hash);
    }
    return t;
}

// XML text of a subtree (used for the `xml` of inserted nodes).
static inline void serialize(const Tree& t, int root, std::string& out) {
    struct Frame { int id; size_t next; };
    std::vector<Frame> st;
    auto open = [&](int u) {
        switch (t.kind[u]) {
            case TEXT: pygixml_html::escape(out, t.label[u].data(), t.label[u].size(), false); return;
            case COMMENT: pygixml_html::append_comment(out, t.label[u].data(), t.label[u].size()); return;
            default: break;
        }
        out += '<'; out += t.label[u];
        for (const auto& kv : t.attrs[u]) {
            out += ' '; out += kv.first; out += "=\"";
            pygixml_html::escape(out, kv.second.data(), kv.second.size(), true);
            out += '"';
        }
        if (t.children[u].empty()) out += "/>";
        else { out += '>'; st.push_back({u, 0}); }
    };
    open(root);
    while (!st.empty()) {
        Frame& f = st.back();
        const auto& ch = t.children[f.id];
        if (f.next < ch.size()) { int c = ch[f.next++]; open(c); }   // may push (f invalid after)
        else { out += "</"; out += t.label[f.id]; out += '>'; st.pop_back(); }
    }
}

}  // namespace pygixml_tree

// Structural "embeddings" of trees: a tree becomes a bag
// (multiset) of 64-bit hashes, and two bags compare with a Dice coefficient.
//
//   pq-gram  (Augsten, Bohlen, Gamper, TODS 2010): every node anchors one or
//            more small windows made of p ancestors (the stem) and q
//            consecutive children (the base). Their distance approximates the
//            tree edit distance and is a lower bound of the fanout-weighted one.
//   paths    ("bag of paths", Krishnapuram & Kummamuru): the set of root-to-node
//            label paths. Cruder, but cheap and good for page templates.
//
// Labels are tag names; text is a constant unless `content` is set, so the
// default is structure only. Both are O(n) in the size of the subtree.

#include <algorithm>
#include <cstdint>
#include <vector>


namespace pygixml_embed {

using pygixml_tree::Tree;
using pygixml_tree::combine;
using pygixml_tree::hash_str;

enum Method { PQGRAM = 0, PATHS = 1 };

struct Params {
    int method = PQGRAM;
    int p = 2, q = 3;
    bool content = false;     // include text/comment content in the labels
};

// 0 is reserved for the dummy ("*") node of a pq-gram.
static inline uint64_t label_hash(const Tree& t, int n, bool content) {
    uint64_t h;
    switch (t.kind[n]) {
        case pygixml_tree::ELEM: h = hash_str(t.label[n], 0xe1); break;
        case pygixml_tree::TEXT: h = content ? hash_str(t.label[n], 0x7e) : 0x7e57; break;
        case pygixml_tree::COMMENT: h = content ? hash_str(t.label[n], 0xc0) : 0xc011; break;
        default: h = 0xd0c; break;
    }
    return h ? h : 1;
}

// Sorted bag of the subtree rooted at `root`, taken in isolation (ancestors
// above `root` do not exist: they are dummies).
static inline std::vector<uint64_t> profile(const Tree& t, int root, const Params& pr) {
    std::vector<uint64_t> bag;
    std::vector<int> stack{root};
    std::vector<uint64_t> stem(pr.p), base(pr.q);
    while (!stack.empty()) {
        int a = stack.back(); stack.pop_back();
        const auto& ch = t.children[a];
        if (pr.method == PATHS) {
            uint64_t h = 0x5a70;
            for (int u = a;; u = t.parent[u]) {          // walk up to the subtree root
                h = combine(h, label_hash(t, u, pr.content));
                if (u == root) break;
            }
            bag.push_back(h);
        } else {
            int u = a;
            for (int i = pr.p - 1; i >= 0; --i) {          // stem: anchor + p-1 ancestors
                stem[i] = u < 0 ? 0 : label_hash(t, u, pr.content);
                u = (u < 0 || u == root) ? -1 : t.parent[u];
            }
            uint64_t sh = 0x95;
            for (uint64_t s : stem) sh = combine(sh, s);
            const int k = static_cast<int>(ch.size());
            const int windows = k == 0 ? 1 : k + pr.q - 1;
            for (int w = 0; w < windows; ++w) {
                uint64_t gh = sh;
                for (int j = 0; j < pr.q; ++j) {
                    int c = w - (pr.q - 1) + j;            // children padded with q-1 dummies each side
                    gh = combine(gh, (k == 0 || c < 0 || c >= k) ? 0 : label_hash(t, ch[c], pr.content));
                }
                bag.push_back(gh);
            }
        }
        for (size_t i = ch.size(); i-- > 0;) stack.push_back(ch[i]);
    }
    std::sort(bag.begin(), bag.end());
    return bag;
}

// Dice coefficient of two sorted bags: 2|A n B| / (|A| + |B|), multiset
// intersection. 1 = identical profiles, 0 = nothing in common.
static inline double dice(const std::vector<uint64_t>& a, const std::vector<uint64_t>& b) {
    if (a.empty() && b.empty()) return 1.0;
    size_t i = 0, j = 0, inter = 0;
    while (i < a.size() && j < b.size()) {
        if (a[i] == b[j]) { ++inter; ++i; ++j; }
        else if (a[i] < b[j]) ++i;
        else ++j;
    }
    return 2.0 * static_cast<double>(inter) / static_cast<double>(a.size() + b.size());
}

// Whole-tree entry points (what Cython calls): normalise, profile, done.
static inline std::vector<std::pair<uint64_t, uint32_t>> signature(const pugi::xml_node& first, bool siblings,
                                                                    const pygixml_tree::Options& o, const Params& pr) {
    Tree t = pygixml_tree::build(first, siblings, o);
    std::vector<uint64_t> bag = profile(t, 0, pr);
    std::vector<std::pair<uint64_t, uint32_t>> out;           // (gram hash, how many times)
    for (uint64_t g : bag) {
        if (!out.empty() && out.back().first == g) ++out.back().second;
        else out.emplace_back(g, 1u);
    }
    return out;
}

static inline double similarity(const pugi::xml_node& a, bool a_sib, const pugi::xml_node& b, bool b_sib,
                                const pygixml_tree::Options& o, const Params& pr) {
    Tree ta = pygixml_tree::build(a, a_sib, o), tb = pygixml_tree::build(b, b_sib, o);
    return dice(profile(ta, 0, pr), profile(tb, 0, pr));
}

}  // namespace pygixml_embed
    """
    cdef cppclass TreeOptions "pygixml_tree::Options":
        bint ignore_whitespace
        bint ignore_comments
        bint class_as_set
        vector[string] ignore_attrs
        vector[string] keys
    cdef cppclass EmbedParams "pygixml_embed::Params":
        int method
        int p
        int q
        bint content
    vector[pair[uint64_t, uint32_t]] signature_cpp "pygixml_embed::signature"(
        const xml_node& first, bint siblings, const TreeOptions& o, const EmbedParams& pr) except +
    double similarity_cpp "pygixml_embed::similarity"(
        const xml_node& a, bint a_sib, const xml_node& b, bint b_sib,
        const TreeOptions& o, const EmbedParams& pr) except +


class PygiXMLDiffError(PygiXMLError):
    """Raised by :func:`diff`, :func:`is_equal`, :func:`signature` and
    :func:`similarity`: something that isn't a node or document, a null node,
    an invalid option, or (a bug if it ever happens) an edit script that does
    not reproduce the target tree.  Subclass of :class:`PygiXMLError`.
    """
    pass


cdef int _unpack_tree(obj, xml_node* first, bint* siblings) except -1:
    """A document or a node -> (first top-level node, do its siblings count too)."""
    cdef XMLNode n
    cdef XMLDocument d
    if isinstance(obj, XMLDocument):
        d = <XMLDocument>obj
        first[0] = d._doc.first_child()
        siblings[0] = True
    elif isinstance(obj, XMLNode):
        n = <XMLNode>obj
        if n._node.type() == node_null:
            raise PygiXMLDiffError("can't compare a null node")
        if n._node.type() == node_document:
            first[0] = n._node.first_child()
            siblings[0] = True
        else:
            first[0] = n._node
            siblings[0] = False
    else:
        raise PygiXMLDiffError(
            f"expected XMLNode or XMLDocument, not {type(obj).__name__}"
        )
    return 0


cdef list _names(value):
    return [value] if isinstance(value, str) else list(value)


cdef TreeOptions _tree_options(bint ignore_whitespace, bint ignore_comments, bint class_as_set,
                               ignore_attrs, keys) except *:
    cdef TreeOptions o
    o.ignore_whitespace = ignore_whitespace
    o.ignore_comments = ignore_comments
    o.class_as_set = class_as_set
    for name in _names(ignore_attrs):
        o.ignore_attrs.push_back((<str>name).encode("utf-8"))
    for name in _names(keys):
        o.keys.push_back((<str>name).encode("utf-8"))
    return o


cdef EmbedParams _embed_params(str method, int p, int q, bint content) except *:
    cdef EmbedParams pr
    if method == "pqgram":
        pr.method = 0
    elif method == "paths":
        pr.method = 1
    else:
        raise PygiXMLDiffError(f"method must be 'pqgram' or 'paths', not {method!r}")
    if p < 1 or q < 1:
        raise PygiXMLDiffError("p and q must be at least 1")
    pr.p = p
    pr.q = q
    pr.content = content
    return pr


def signature(node, str method="pqgram", int p=2, int q=3, bint content=False, *,
              bint ignore_whitespace=True, bint ignore_comments=True,
              ignore_attrs=(), bint class_as_set=True):
    """Embed the *structure* of a tree as a sparse vector: ``{hash: count}``.

    Two methods, both linear in the size of the tree:

    * ``"pqgram"`` (default): pq-grams (Augsten, Bohlen, Gamper, TODS 2010).
      Each node anchors windows made of ``p`` ancestors and ``q`` consecutive
      children; their distance approximates the tree edit distance and
      lower-bounds the fanout-weighted one.
    * ``"paths"``: the bag of root-to-node tag paths. Cruder and cheaper;
      good for telling page templates apart.

    Labels are tag names; text counts as one constant label, so the default is
    structure only. Pass ``content=True`` to include text and comment content.

    The vector is hash-keyed, so it compares with
    :func:`similarity` (or your own dot product), not by key meaning.

    Args:
        node: an :class:`XMLNode` or :class:`XMLDocument`.
        method: ``"pqgram"`` or ``"paths"``.
        p, q: pq-gram shape (stem length, base width).
        content: include text/comment content in the labels.
        ignore_whitespace, ignore_comments, ignore_attrs, class_as_set:
            normalisation, same meaning as in :func:`diff`.

    Raises:
        PygiXMLDiffError: not a node/document, null node, or invalid option.
    """
    cdef xml_node first
    cdef bint sib
    _unpack_tree(node, &first, &sib)
    cdef TreeOptions o = _tree_options(ignore_whitespace, ignore_comments, class_as_set, ignore_attrs, ())
    cdef EmbedParams pr = _embed_params(method, p, q, content)
    cdef vector[pair[uint64_t, uint32_t]] bag = signature_cpp(first, sib, o, pr)
    return {<object>item.first: <object>item.second for item in bag}


def similarity(a, b, str method="pqgram", int p=2, int q=3, bint content=False, *,
               bint ignore_whitespace=True, bint ignore_comments=True,
               ignore_attrs=(), bint class_as_set=True):
    """Structural similarity of two trees in ``[0, 1]``: the Dice coefficient
    of their :func:`signature` bags (1 = same structure, 0 = nothing shared).

    Computed in a single C++ call, without building the two dicts. Runs in
    time linear in the size of the trees, so it is a cheap pre-filter before
    an expensive :func:`diff`.

    Raises:
        PygiXMLDiffError: see :func:`signature`.
    """
    cdef xml_node fa, fb
    cdef bint sa, sb
    _unpack_tree(a, &fa, &sa)
    _unpack_tree(b, &fb, &sb)
    cdef TreeOptions o = _tree_options(ignore_whitespace, ignore_comments, class_as_set, ignore_attrs, ())
    cdef EmbedParams pr = _embed_params(method, p, q, content)
    return similarity_cpp(fa, sa, fb, sb, o, pr)
