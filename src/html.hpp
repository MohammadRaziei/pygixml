// html.hpp -- HTML <-> XML for pygixml, entirely in C++ so each Python call
// crosses the Python/C++ boundary exactly once.
//
//   to_xml(html, root)     messy HTML  -> well-formed XML text
//   to_html(node, ...)     XML tree    -> HTML text
//
// to_xml is a small HTML5-style tokenizer (tags, attributes, comments, raw
// text, entities) feeding a tree fixer (void tags, implied end tags, stray
// end tags, root wrapping). It is NOT the full HTML5 tree-construction
// algorithm: no implied <html>/<head>/<body>, no table foster-parenting.
// Both directions are iterative, so deep documents cannot overflow the stack.
#pragma once

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include "pugixml.hpp"
#include "html_entities.hpp"

namespace pygixml_html {

// ------------------------------------------------------------------ utf-8

static inline void put_utf8(std::string& out, uint32_t cp) {
    if (cp < 0x80) {
        out += static_cast<char>(cp);
    } else if (cp < 0x800) {
        out += static_cast<char>(0xC0 | (cp >> 6));
        out += static_cast<char>(0x80 | (cp & 0x3F));
    } else if (cp < 0x10000) {
        out += static_cast<char>(0xE0 | (cp >> 12));
        out += static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
        out += static_cast<char>(0x80 | (cp & 0x3F));
    } else {
        out += static_cast<char>(0xF0 | (cp >> 18));
        out += static_cast<char>(0x80 | ((cp >> 12) & 0x3F));
        out += static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
        out += static_cast<char>(0x80 | (cp & 0x3F));
    }
}

// Decode one code point (input is valid UTF-8: it came from a Python str or pugixml).
static inline uint32_t get_utf8(const std::string& s, size_t& i) {
    unsigned char c = static_cast<unsigned char>(s[i]);
    size_t n = c < 0x80 ? 1 : c < 0xE0 ? 2 : c < 0xF0 ? 3 : 4;
    if (i + n > s.size()) { ++i; return 0xFFFD; }
    uint32_t cp = n == 1 ? c : n == 2 ? (c & 0x1F) : n == 3 ? (c & 0x0F) : (c & 0x07);
    for (size_t k = 1; k < n; ++k) cp = (cp << 6) | (static_cast<unsigned char>(s[i + k]) & 0x3F);
    i += n;
    return cp;
}

// --------------------------------------------------------------- small utils

static inline bool is_ws(char c) { return c == ' ' || c == '\t' || c == '\n' || c == '\f' || c == '\r'; }
static inline bool is_alpha(char c) { return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z'); }
static inline bool is_digit(char c) { return c >= '0' && c <= '9'; }
static inline bool is_alnum(char c) { return is_alpha(c) || is_digit(c); }
static inline bool is_hex(char c) { return is_digit(c) || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F'); }

static inline std::string lower_ascii(const char* s, size_t n) {
    std::string r(s, n);
    for (auto& c : r) if (c >= 'A' && c <= 'Z') c = static_cast<char>(c + 32);
    return r;
}

static inline bool starts_ci(const char* s, size_t n, const char* lit) {
    size_t l = std::strlen(lit);
    if (n < l) return false;
    for (size_t i = 0; i < l; ++i) {
        char a = s[i];
        if (a >= 'A' && a <= 'Z') a = static_cast<char>(a + 32);
        if (a != lit[i]) return false;
    }
    return true;
}

// XML-illegal characters (control chars except \t \n \r, U+FFFE, U+FFFF) are dropped.
static inline void append_clean(std::string& out, const char* s, size_t n) {
    for (size_t i = 0; i < n; ++i) {
        unsigned char c = static_cast<unsigned char>(s[i]);
        if (c < 0x20 && c != '\t' && c != '\n' && c != '\r') continue;
        if (c == 0xEF && i + 2 < n && static_cast<unsigned char>(s[i + 1]) == 0xBF &&
            (static_cast<unsigned char>(s[i + 2]) == 0xBE || static_cast<unsigned char>(s[i + 2]) == 0xBF)) {
            i += 2;
            continue;
        }
        out += static_cast<char>(c);
    }
}

// ws_literal: keep raw \n \r \t in attribute values (HTML output) instead of
// char references (XML output: parsers would otherwise normalise them to spaces).
static inline void escape(std::string& out, const char* s, size_t n, bool attr, bool ws_literal = false) {
    for (size_t i = 0; i < n; ++i) {
        unsigned char c = static_cast<unsigned char>(s[i]);
        switch (c) {
            case '&': out += "&amp;"; continue;
            case '<': out += "&lt;"; continue;
            case '>': out += "&gt;"; continue;
            case '"': if (attr) { out += "&quot;"; continue; } break;
            case '\n': if (attr && !ws_literal) { out += "&#10;"; continue; } break;
            case '\r': if (attr && !ws_literal) { out += "&#13;"; continue; } break;
            case '\t': if (attr && !ws_literal) { out += "&#9;"; continue; } break;
            default: break;
        }
        if (c < 0x20 && c != '\t' && c != '\n' && c != '\r') continue;
        if (c == 0xEF && i + 2 < n && static_cast<unsigned char>(s[i + 1]) == 0xBF &&
            (static_cast<unsigned char>(s[i + 2]) == 0xBE || static_cast<unsigned char>(s[i + 2]) == 0xBF)) {
            i += 2;
            continue;
        }
        out += static_cast<char>(c);
    }
}

// XML comments can't contain "--" or end with "-".
static inline void append_comment(std::string& out, const char* s, size_t n) {
    std::string clean;
    append_clean(clean, s, n);
    out += "<!--";
    for (size_t i = 0; i < clean.size(); ++i) {
        out += clean[i];
        if (clean[i] == '-' && i + 1 < clean.size() && clean[i + 1] == '-') out += ' ';
    }
    if (!clean.empty() && clean.back() == '-') out += ' ';
    out += "-->";
}

// ------------------------------------------------------- reversible names
//
// XML rejects some names HTML allows (o:p, @click, [prop], 1bad). They are
// encoded, not dropped, so to_html can restore them:
//   ':' -> _colon_   '@' -> _at_   '[' -> _lbracket_   anything else -> _x<hex>_

static inline bool name_start(uint32_t c) {
    return (c >= 'A' && c <= 'Z') || c == '_' || (c >= 'a' && c <= 'z') ||
           (c >= 0xC0 && c <= 0xD6) || (c >= 0xD8 && c <= 0xF6) || (c >= 0xF8 && c <= 0x2FF) ||
           (c >= 0x370 && c <= 0x37D) || (c >= 0x37F && c <= 0x1FFF) || (c >= 0x200C && c <= 0x200D) ||
           (c >= 0x2070 && c <= 0x218F) || (c >= 0x2C00 && c <= 0x2FEF) || (c >= 0x3001 && c <= 0xD7FF) ||
           (c >= 0xF900 && c <= 0xFDCF) || (c >= 0xFDF0 && c <= 0xFFFD) || (c >= 0x10000 && c <= 0xEFFFF);
}
static inline bool name_char(uint32_t c) {
    return name_start(c) || c == '-' || c == '.' || (c >= '0' && c <= '9') || c == 0xB7 ||
           (c >= 0x300 && c <= 0x36F) || (c >= 0x203F && c <= 0x2040);
}

static const char* const kWords[][2] = {
    {":", "colon"}, {"@", "at"}, {"#", "hash"}, {"[", "lbracket"}, {"]", "rbracket"},
    {"(", "lparen"}, {")", "rparen"}, {"*", "star"}, {"+", "plus"}, {"/", "slash"},
};

static inline std::string enc_name(const std::string& raw) {
    bool ok = !raw.empty();                         // fast path: already a valid XML name
    for (size_t i = 0; ok && i < raw.size();) {
        uint32_t cp = get_utf8(raw, i);
        ok = name_char(cp);                         // (start char re-checked below)
    }
    if (ok) {
        size_t i = 0;
        if (name_start(get_utf8(raw, i))) return raw;
    }
    std::string out;
    size_t i = 0;
    bool first = true;
    while (i < raw.size()) {
        size_t begin = i;
        uint32_t cp = get_utf8(raw, i);
        if (first ? name_start(cp) : name_char(cp)) {
            out.append(raw, begin, i - begin);
        } else {
            const char* word = nullptr;
            if (cp < 0x80)
                for (auto& w : kWords) if (w[0][0] == static_cast<char>(cp)) { word = w[1]; break; }
            if (word) { out += '_'; out += word; out += '_'; }
            else { char buf[16]; std::snprintf(buf, sizeof buf, "_x%x_", cp); out += buf; }
        }
        first = false;
    }
    return out;
}

static inline std::string dec_name(const char* s) {
    std::string out;
    size_t n = std::strlen(s);
    for (size_t i = 0; i < n; ++i) {
        if (s[i] == '_') {
            size_t j = i + 1;
            if (j < n && s[j] == 'x') {                      // _x<hex>_
                size_t k = j + 1;
                while (k < n && ((s[k] >= '0' && s[k] <= '9') || (s[k] >= 'a' && s[k] <= 'f'))) ++k;
                if (k > j + 1 && k < n && s[k] == '_') {
                    put_utf8(out, static_cast<uint32_t>(std::strtoul(std::string(s + j + 1, k - j - 1).c_str(), nullptr, 16)));
                    i = k;
                    continue;
                }
            }
            bool hit = false;
            for (auto& w : kWords) {
                size_t l = std::strlen(w[1]);
                if (n - j > l && std::memcmp(s + j, w[1], l) == 0 && s[j + l] == '_') {
                    out += w[0];
                    i = j + l;
                    hit = true;
                    break;
                }
            }
            if (hit) continue;
        }
        out += s[i];
    }
    return out;
}

// ---------------------------------------------------------------- entities

static inline uint32_t cp1252(uint32_t c) {
    static const uint16_t t[32] = {
        0x20AC, 0x81, 0x201A, 0x0192, 0x201E, 0x2026, 0x2020, 0x2021, 0x02C6, 0x2030, 0x0160,
        0x2039, 0x0152, 0x8D, 0x017D, 0x8F, 0x90, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022,
        0x2013, 0x2014, 0x02DC, 0x2122, 0x0161, 0x203A, 0x0153, 0x9D, 0x017E, 0x0178};
    return t[c - 0x80];
}

// Decode character references in s[0..n) (HTML5 rules). In attribute values a
// legacy reference without ';' followed by '=' or a letter/digit is left alone.
static inline void decode_entities(std::string& out, const char* s, size_t n, bool attr) {
    size_t i = 0;
    while (i < n) {
        const char* amp = static_cast<const char*>(std::memchr(s + i, '&', n - i));
        if (!amp) { out.append(s + i, n - i); return; }
        size_t p = static_cast<size_t>(amp - s);
        out.append(s + i, p - i);
        i = p;
        if (p + 1 >= n) { out += '&'; ++i; continue; }
        char c = s[p + 1];
        if (c == '#') {
            size_t k = p + 2;
            bool hex = k < n && (s[k] == 'x' || s[k] == 'X');
            if (hex) ++k;
            size_t d0 = k;
            uint64_t v = 0;
            while (k < n && (hex ? is_hex(s[k]) : is_digit(s[k]))) {
                v = v * (hex ? 16 : 10) + static_cast<uint64_t>(is_digit(s[k]) ? s[k] - '0' : (s[k] | 0x20) - 'a' + 10);
                if (v > 0x10FFFF) v = 0x110000;
                ++k;
            }
            if (k == d0) { out += '&'; ++i; continue; }
            if (k < n && s[k] == ';') ++k;
            uint32_t cp = static_cast<uint32_t>(v);
            if (cp == 0 || cp > 0x10FFFF || (cp >= 0xD800 && cp <= 0xDFFF)) cp = 0xFFFD;
            else if (cp >= 0x80 && cp <= 0x9F) cp = cp1252(cp);
            put_utf8(out, cp);
            i = k;
        } else if (is_alnum(c)) {
            size_t m = p + 1;
            while (m < n && is_alnum(s[m]) && m - (p + 1) < 32) ++m;
            if (m < n && s[m] == ';') {
                std::string key(s + p + 1, m - p);                  // name + ';'
                if (const char* v = entity_lookup(key.data(), key.size())) { out += v; i = m + 1; continue; }
            }
            bool done = false;
            for (size_t len = m - (p + 1); len >= 2 && !done; --len) {   // longest legacy prefix
                if (const char* v = entity_lookup(s + p + 1, len)) {
                    size_t after = p + 1 + len;
                    if (attr && after < n && (s[after] == '=' || is_alnum(s[after]))) break;
                    out += v;
                    i = after;
                    done = true;
                }
            }
            if (!done) { out += '&'; ++i; }
        } else {
            out += '&';
            ++i;
        }
    }
}

// ------------------------------------------------------------ HTML -> XML

struct RuleSet { std::unordered_set<std::string> targets, stops; };
using Rules = std::vector<RuleSet>;

static inline bool in_set(const std::unordered_set<std::string>& s, const std::string& k) { return s.count(k) != 0; }

static inline const std::unordered_map<std::string, Rules>& rule_table() {
    static const std::unordered_map<std::string, Rules> table = [] {
        std::unordered_map<std::string, Rules> t;
        auto split = [](const char* w) {
            std::unordered_set<std::string> r;
            std::string cur;
            for (const char* c = w; ; ++c) {
                if (*c == ' ' || *c == '\0') { if (!cur.empty()) r.insert(cur); cur.clear(); if (!*c) break; }
                else cur += *c;
            }
            return r;
        };
        RuleSet P{split("p"), split("applet caption html table td th marquee object template button")};
        for (const char* b : {"address", "article", "aside", "blockquote", "center", "details", "dialog", "dir",
                              "div", "dl", "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2", "h3",
                              "h4", "h5", "h6", "header", "hgroup", "hr", "main", "menu", "nav", "ol", "p",
                              "pre", "search", "section", "summary", "table", "ul"})
            t[b] = {P};
        t["li"] = {{split("li"), split("ul ol menu")}, P};
        t["dt"] = {{split("dt dd"), split("dl")}, P};
        t["dd"] = {{split("dt dd"), split("dl")}, P};
        t["tr"] = {{split("tr"), split("table")}};
        t["td"] = {{split("td th"), split("tr table")}};
        t["th"] = {{split("td th"), split("tr table")}};
        for (const char* h : {"thead", "tbody", "tfoot"}) t[h] = {{split("thead tbody tfoot"), split("table")}};
        t["option"] = {{split("option"), split("select datalist")}};
        t["optgroup"] = {{split("optgroup"), split("select datalist")}, {split("option"), split("select datalist")}};
        return t;
    }();
    return table;
}

static inline bool is_void(const std::string& t) {
    static const std::unordered_set<std::string> v = {"area", "base", "br", "col", "embed", "hr", "img",
                                                      "input", "link", "meta", "param", "source", "track", "wbr"};
    return v.count(t) != 0;
}

struct Builder {
    std::string out;
    std::vector<std::string> stack;    // open elements (lower-case HTML names)
    size_t tops = 0;                   // top-level elements seen
    bool loose = false;                // top-level non-blank text seen
    bool skip_nl = false;              // just opened <pre>/<textarea>: drop one leading "\n"

    void pop_to(size_t keep) {
        while (stack.size() > keep) {
            out += "</"; out += enc_name(stack.back()); out += '>';
            stack.pop_back();
        }
    }

    void data(std::string text) {
        if (text.empty()) return;
        if (skip_nl) {                 // the HTML spec drops it; to_html re-adds it
            skip_nl = false;
            if (text[0] == '\n') { text.erase(0, 1); if (text.empty()) return; }
        }
        if (stack.empty()) {
            std::string clean;         // text that is only XML-illegal characters is blank too
            append_clean(clean, text.data(), text.size());
            bool blank = true;
            for (char c : clean) if (!is_ws(c)) { blank = false; break; }
            if (blank) return;         // blank text between top-level nodes is dropped
            loose = true;
        }
        escape(out, text.data(), text.size(), false);
    }

    void start(const std::string& tag, const std::vector<std::pair<std::string, std::string>>& attrs, bool empty) {
        skip_nl = false;
        auto it = rule_table().find(tag);
        if (it != rule_table().end()) {
            for (const RuleSet& r : it->second) {
                for (size_t i = stack.size(); i-- > 0;) {
                    if (in_set(r.targets, stack[i])) { pop_to(i); break; }
                    if (in_set(r.stops, stack[i])) break;
                }
            }
        }
        if (stack.empty()) ++tops;
        out += '<'; out += enc_name(tag);
        std::unordered_set<std::string> seen;
        for (const auto& kv : attrs) {
            std::string k = enc_name(kv.first);
            if (!seen.insert(k).second) continue;     // HTML keeps the first duplicate
            out += ' '; out += k; out += "=\"";
            escape(out, kv.second.data(), kv.second.size(), true);
            out += '"';
        }
        bool closed = empty || is_void(tag);
        out += closed ? "/>" : ">";
        if (!closed) {
            stack.push_back(tag);
            skip_nl = (tag == "pre" || tag == "textarea" || tag == "listing");
        }
    }

    void end(const std::string& tag) {
        skip_nl = false;
        for (size_t i = stack.size(); i-- > 0;)
            if (stack[i] == tag) { pop_to(i); return; }
        // stray end tag: ignored, as browsers do
    }

    void comment(const char* s, size_t n) { skip_nl = false; append_comment(out, s, n); }
};

// Returns the XML text. `root` wraps fragments (several top-level nodes or text).
static inline std::string to_xml(const std::string& input, const std::string& root) {
    // Input stream preprocessing: CRLF and lone CR become LF.
    std::string src;
    src.reserve(input.size());
    for (size_t i = 0; i < input.size(); ++i) {
        if (input[i] == '\r') { src += '\n'; if (i + 1 < input.size() && input[i + 1] == '\n') ++i; }
        else src += input[i];
    }
    const char* s = src.data();
    const size_t n = src.size();

    Builder b;
    b.out.reserve(n + n / 8);
    size_t i = 0;
    while (i < n) {
        const char* lt = static_cast<const char*>(std::memchr(s + i, '<', n - i));
        size_t p = lt ? static_cast<size_t>(lt - s) : n;
        if (p > i) { std::string t; decode_entities(t, s + i, p - i, false); b.data(std::move(t)); }
        if (p >= n) break;
        i = p;

        char c = i + 1 < n ? s[i + 1] : '\0';
        if (is_alpha(c)) {
            // ---- start tag
            size_t j = i + 1;
            while (j < n && !is_ws(s[j]) && s[j] != '/' && s[j] != '>') ++j;
            std::string tag = lower_ascii(s + i + 1, j - (i + 1));
            std::vector<std::pair<std::string, std::string>> attrs;
            bool empty = false, closed = false;
            while (true) {
                while (j < n && (is_ws(s[j]) || (s[j] == '/' && !(j + 1 < n && s[j + 1] == '>')))) ++j;
                if (j >= n) break;                                    // EOF inside the tag
                if (s[j] == '>') { ++j; closed = true; break; }
                if (s[j] == '/') { j += 2; empty = true; closed = true; break; }
                size_t k = j + 1;                                     // attribute name (may start with '=')
                while (k < n && !is_ws(s[k]) && s[k] != '/' && s[k] != '>' && s[k] != '=') ++k;
                std::string name = lower_ascii(s + j, k - j);
                j = k;
                while (j < n && is_ws(s[j])) ++j;
                std::string value;
                if (j < n && s[j] == '=') {
                    ++j;
                    while (j < n && is_ws(s[j])) ++j;
                    if (j < n && (s[j] == '"' || s[j] == '\'')) {
                        const char* q = static_cast<const char*>(std::memchr(s + j + 1, s[j], n - j - 1));
                        if (!q) { j = n; break; }
                        size_t e = static_cast<size_t>(q - s);
                        decode_entities(value, s + j + 1, e - j - 1, true);
                        j = e + 1;
                    } else {
                        size_t e = j;
                        while (e < n && !is_ws(s[e]) && s[e] != '>') ++e;
                        decode_entities(value, s + j, e - j, true);
                        j = e;
                    }
                }
                attrs.emplace_back(std::move(name), std::move(value));
            }
            if (!closed) break;                                       // EOF inside a tag: dropped (HTML5)
            b.start(tag, attrs, empty);
            i = j;
            if (!empty && (tag == "script" || tag == "style" || tag == "textarea" || tag == "title")) {
                // raw text / RCDATA: runs to the matching end tag, no markup inside
                size_t e = i;
                while (true) {
                    const char* f = e < n ? static_cast<const char*>(std::memchr(s + e, '<', n - e)) : nullptr;
                    if (!f) { e = n; break; }
                    e = static_cast<size_t>(f - s);
                    if (e + 1 < n && s[e + 1] == '/' && starts_ci(s + e + 2, n - e - 2, tag.c_str())) {
                        size_t a = e + 2 + tag.size();
                        if (a >= n || is_ws(s[a]) || s[a] == '/' || s[a] == '>') break;
                    }
                    ++e;
                }
                if (e > i) {
                    std::string t;
                    if (tag == "script" || tag == "style") t.assign(s + i, e - i);
                    else decode_entities(t, s + i, e - i, false);
                    b.data(std::move(t));
                }
                i = e;
            }
        } else if (c == '/') {
            if (i + 2 >= n) { b.data("</"); break; }                  // input ends right after "</"
            char d = s[i + 2];
            if (is_alpha(d)) {                                        // end tag
                size_t j = i + 2;
                while (j < n && !is_ws(s[j]) && s[j] != '/' && s[j] != '>') ++j;
                std::string tag = lower_ascii(s + i + 2, j - (i + 2));
                const char* gt = static_cast<const char*>(std::memchr(s + j, '>', n - j));
                b.end(tag);
                if (!gt) break;
                i = static_cast<size_t>(gt - s) + 1;
            } else if (d == '>') {
                i += 3;                                               // "</>": ignored
            } else {                                                  // bogus comment
                const char* gt = static_cast<const char*>(std::memchr(s + i + 2, '>', n - i - 2));
                size_t e = gt ? static_cast<size_t>(gt - s) : n;
                b.comment(s + i + 2, e - (i + 2));
                i = gt ? e + 1 : n;
            }
        } else if (c == '!') {
            if (n - i >= 4 && std::memcmp(s + i, "<!--", 4) == 0) {
                size_t a = i + 4;
                if (a < n && s[a] == '>') { b.comment("", 0); i = a + 1; continue; }
                if (a + 1 < n && s[a] == '-' && s[a + 1] == '>') { b.comment("", 0); i = a + 2; continue; }
                size_t stop = n, skip = 0;
                for (size_t e = a; e + 2 < n; ++e) {
                    if (s[e] != '-' || s[e + 1] != '-') continue;
                    if (s[e + 2] == '>') { stop = e; skip = 3; break; }
                    if (s[e + 2] == '!' && e + 3 < n && s[e + 3] == '>') { stop = e; skip = 4; break; }
                }
                b.comment(s + a, stop - a);
                i = stop == n ? n : stop + skip;
            } else if (starts_ci(s + i + 2, n - i - 2, "doctype")) {
                const char* gt = static_cast<const char*>(std::memchr(s + i, '>', n - i));
                i = gt ? static_cast<size_t>(gt - s) + 1 : n;         // dropped
            } else if (n - i >= 9 && std::memcmp(s + i, "<![CDATA[", 9) == 0) {
                size_t e = i + 9;
                while (e + 2 < n && !(s[e] == ']' && s[e + 1] == ']' && s[e + 2] == '>')) ++e;
                i = e + 2 < n ? e + 3 : n;                            // dropped
            } else {                                                  // bogus comment
                const char* gt = static_cast<const char*>(std::memchr(s + i + 2, '>', n - i - 2));
                size_t e = gt ? static_cast<size_t>(gt - s) : n;
                b.comment(s + i + 2, e - (i + 2));
                i = gt ? e + 1 : n;
            }
        } else if (c == '?') {
            const char* gt = static_cast<const char*>(std::memchr(s + i, '>', n - i));
            i = gt ? static_cast<size_t>(gt - s) + 1 : n;             // <?...?>: dropped
        } else {
            b.data("<");                                              // a literal '<'
            ++i;
        }
    }
    b.pop_to(0);

    if (b.tops == 1 && !b.loose) return std::move(b.out);
    std::string r = enc_name(root);
    return "<" + r + ">" + b.out + "</" + r + ">";
}

// ------------------------------------------------------------ XML -> HTML

static inline bool in_list(const char* const* list, const std::string& k) {
    for (; *list; ++list) if (k == *list) return true;
    return false;
}
static const char* const kVerbatim[] = {"pre", "textarea", "script", "style", nullptr};
static const char* const kInline[] = {
    "a", "abbr", "b", "bdi", "bdo", "br", "button", "cite", "code", "data", "del", "dfn", "em", "i", "img",
    "input", "ins", "kbd", "label", "mark", "q", "s", "samp", "select", "small", "span", "strong", "sub",
    "sup", "textarea", "time", "u", "var", "wbr", nullptr};

struct Frame {
    pugi::xml_node next;     // next child to visit
    std::string tag;
    bool block;              // children are laid out one per line
    size_t depth;
};

static inline bool blank_text(const pugi::xml_node& n) {
    for (const char* c = n.value(); *c; ++c) if (!is_ws(*c)) return false;
    return true;
}

// Can this node sit on its own line without changing how the page renders?
// (block-level elements, comments, blank text -- not inline elements or real text)
static inline bool block_ok(const pugi::xml_node& k) {
    if (k.type() == pugi::node_element) {
        std::string t = dec_name(k.name());
        return !in_list(kInline, lower_ascii(t.data(), t.size()));
    }
    if (k.type() == pugi::node_pcdata || k.type() == pugi::node_cdata) return blank_text(k);
    return true;
}

static inline void write_raw(std::string& out, const std::string& text) {
    // "</script" / "</style" inside raw text would close the element early.
    for (size_t i = 0; i < text.size(); ++i) {
        if (text[i] == '<' && i + 1 < text.size() && text[i + 1] == '/' &&
            (starts_ci(text.data() + i + 2, text.size() - i - 2, "script") ||
             starts_ci(text.data() + i + 2, text.size() - i - 2, "style"))) {
            out += "<\\";
            continue;
        }
        out += text[i];
    }
}

static inline void write_node(std::string& out, const pugi::xml_node& node, bool pretty,
                              size_t depth, std::vector<Frame>& st) {
    switch (node.type()) {
        case pugi::node_comment: append_comment(out, node.value(), std::strlen(node.value())); return;
        case pugi::node_pcdata:
        case pugi::node_cdata: escape(out, node.value(), std::strlen(node.value()), false); return;
        case pugi::node_element: break;
        default: return;   // doctype, <?pi?>, declaration: dropped
    }
    std::string tag = dec_name(node.name());
    std::string low = lower_ascii(tag.data(), tag.size());
    out += '<'; out += tag;
    for (pugi::xml_attribute a = node.first_attribute(); a; a = a.next_attribute()) {
        out += ' '; out += dec_name(a.name()); out += "=\"";
        escape(out, a.value(), std::strlen(a.value()), true, true);
        out += '"';
    }
    out += '>';
    if (is_void(low)) return;                      // HTML forbids content and an end tag

    if (low == "script" || low == "style") {       // raw text
        std::string text;
        for (pugi::xml_node k = node.first_child(); k; k = k.next_sibling())
            if (k.type() == pugi::node_pcdata || k.type() == pugi::node_cdata) text += k.value();
        std::string clean;
        append_clean(clean, text.data(), text.size());
        write_raw(out, clean);
        out += "</" + tag + ">";
        return;
    }

    pugi::xml_node first = node.first_child();
    if (first && (low == "pre" || low == "textarea" || low == "listing") &&
        (first.type() == pugi::node_pcdata || first.type() == pugi::node_cdata) && first.value()[0] == '\n')
        out += '\n';                               // parsers drop a leading newline: keep it

    bool block = false;
    if (pretty && first && !in_list(kVerbatim, low) && !in_list(kInline, low)) {
        block = true;                              // only if every child can sit on its own line
        for (pugi::xml_node k = first; k && block; k = k.next_sibling()) block = block_ok(k);
    }
    st.push_back(Frame{first, tag, block, depth});
}

static inline void drain(std::string& out, std::vector<Frame>& st, const std::string& indent) {
    while (!st.empty()) {
        Frame& f = st.back();
        if (f.next) {
            pugi::xml_node child = f.next;
            f.next = child.next_sibling();
            bool block = f.block;
            size_t depth = f.depth;
            if (block) {
                if (child.type() == pugi::node_pcdata || child.type() == pugi::node_cdata) continue;
                if (child.type() != pugi::node_element && child.type() != pugi::node_comment) continue;
                out += '\n';
                for (size_t d = 0; d <= depth; ++d) out += indent;
            }
            write_node(out, child, block, depth + 1, st);   // may push (f invalid afterwards)
        } else {
            if (f.block) { out += '\n'; for (size_t d = 0; d < f.depth; ++d) out += indent; }
            out += "</" + f.tag + ">";
            st.pop_back();
        }
    }
}

// `first`: the first top-level node. With `siblings` every following sibling is
// a top-level node too (what a document / node's children look like); without,
// `first` alone is serialized. `unwrap`: if set and the only top-level element
// has this name, emit its children instead.
static inline std::string to_html(const pugi::xml_node& first, bool siblings, bool pretty,
                                  const std::string& indent, bool doctype, const char* unwrap) {
    std::vector<pugi::xml_node> tops;
    if (siblings) for (pugi::xml_node k = first; k; k = k.next_sibling()) tops.push_back(k);
    else tops.push_back(first);

    if (unwrap) {
        pugi::xml_node only;
        size_t elems = 0;
        for (auto& t : tops) if (t.type() == pugi::node_element) { ++elems; only = t; }
        if (elems == 1 && std::strcmp(only.name(), unwrap) == 0) {
            tops.clear();
            for (pugi::xml_node k = only.first_child(); k; k = k.next_sibling()) tops.push_back(k);
        }
    }

    // Top-level newlines are only safe when no top-level node is real text or an
    // inline element: otherwise the "\n" would itself become content when re-parsed.
    bool top_block = pretty;
    for (auto& t : tops) if (!block_ok(t)) { top_block = false; break; }

    std::string out;
    if (doctype) out += top_block ? "<!DOCTYPE html>\n" : "<!DOCTYPE html>";
    std::vector<Frame> st;
    bool is_first = true;
    for (auto& t : tops) {
        if (top_block) {
            if (t.type() == pugi::node_pcdata || t.type() == pugi::node_cdata) continue;   // blank
            if (!is_first) out += '\n';
        }
        is_first = false;
        write_node(out, t, pretty, 0, st);
        drain(out, st, indent);
    }
    return out;
}

}  // namespace pygixml_html
