# jsonify.pxi
# -----------
# Converts an xml_node tree directly to a JSON string via a C++ string
# buffer — no Python dict/list/str is allocated during traversal.
# Only one Python str object is created at the very end.
#
# Public API:
#   jsonify_dumps(xml,  attr_prefix, cdata_key, force_list, pretty, indent, encoding)
#   jsonify_dumps_node(ObjectifiedElement, ...)
#
# objectify.py and a jsonify.py shim re-export these as:
#   from pygixml import jsonify
#   jsonify.dumps(xml)
#   jsonify.dumps_node(root)

# ---------------------------------------------------------------------------
# C++ JSON serializer (inline, no extra dependencies)
# ---------------------------------------------------------------------------

cdef extern from *:
    """
    #include <string>
    #include <unordered_set>
    #include "pugixml.hpp"

    // ---------------------------------------------------------------------------
    // Minimal JSON string escaping
    // ---------------------------------------------------------------------------
    static void json_escape(const char* s, std::string& out) {
        out += '"';
        for (; *s; ++s) {
            unsigned char c = static_cast<unsigned char>(*s);
            switch (c) {
                case '"':  out += "\\\\\\""; break;
                case '\\\\': out += "\\\\\\\\"; break;
                case '\\n': out += "\\\\n";  break;
                case '\\r': out += "\\\\r";  break;
                case '\\t': out += "\\\\t";  break;
                default:
                    if (c < 0x20) {
                        // control character — emit \\\\uXXXX
                        char buf[8];
                        snprintf(buf, sizeof(buf), "\\\\u%04x", c);
                        out += buf;
                    } else {
                        out += c;
                    }
            }
        }
        out += '"';
    }

    // ---------------------------------------------------------------------------
    // Count how many direct element children share a given tag name
    // ---------------------------------------------------------------------------
    static int count_tag(pugi::xml_node parent, const char* tag) {
        int n = 0;
        for (pugi::xml_node c = parent.first_child(); c; c = c.next_sibling())
            if (c.type() == pugi::node_element && strcmp(c.name(), tag) == 0)
                ++n;
        return n;
    }

    // ---------------------------------------------------------------------------
    // Core recursive serializer
    // ---------------------------------------------------------------------------
    static void node_to_json(
        pugi::xml_node     node,
        std::string&       buf,
        const std::string& attr_prefix,
        const std::string& cdata_key,
        const std::unordered_set<std::string>& force_list,
        bool               force_all,
        const std::string& nl,       // newline: "\\n" or ""
        const std::string& ind,      // one indent level: "\\t", "  ", or ""
        int                depth
    ) {
        // --- collect attributes -------------------------------------------
        bool has_attrs    = false;
        bool has_children = false;
        const char* text  = node.child_value();   // direct text child
        bool has_text     = (text && text[0]);

        // trim whitespace-only text
        if (has_text) {
            const char* p = text;
            while (*p == ' ' || *p == '\\t' || *p == '\\n' || *p == '\\r') ++p;
            if (!*p) has_text = false;
        }

        for (pugi::xml_attribute a = node.first_attribute(); a;
             a = a.next_attribute())
            has_attrs = true;

        for (pugi::xml_node c = node.first_child(); c; c = c.next_sibling())
            if (c.type() == pugi::node_element) { has_children = true; break; }

        // --- leaf node (no attrs, no children) ----------------------------
        if (!has_attrs && !has_children) {
            if (!has_text) { buf += "null"; return; }
            json_escape(text, buf);
            return;
        }

        // --- object node --------------------------------------------------
        std::string pad(depth * ind.size(), ind.empty() ? ' ' : ind[0]);
        // actually build pad properly
        pad.clear();
        for (int i = 0; i < depth; ++i) pad += ind;

        std::string pad1 = pad + ind;

        buf += '{';

        bool first = true;
        auto sep = [&]() {
            if (!first) buf += ',';
            buf += nl;
            buf += pad1;
            first = false;
        };

        // attributes
        for (pugi::xml_attribute a = node.first_attribute(); a;
             a = a.next_attribute()) {
            sep();
            json_escape((attr_prefix + a.name()).c_str(), buf);
            buf += ':';
            if (!nl.empty()) buf += ' ';
            json_escape(a.value(), buf);
        }

        // text content in mixed nodes
        if (has_text && (has_attrs || has_children)) {
            sep();
            json_escape(cdata_key.c_str(), buf);
            buf += ':';
            if (!nl.empty()) buf += ' ';
            json_escape(text, buf);
        }

        // child elements — track which tags have been emitted
        std::unordered_set<std::string> emitted;
        for (pugi::xml_node c = node.first_child(); c; c = c.next_sibling()) {
            if (c.type() != pugi::node_element) continue;
            std::string tag(c.name());
            if (emitted.count(tag)) continue;
            emitted.insert(tag);

            int cnt = count_tag(node, tag.c_str());
            bool as_list = (cnt > 1)
                || force_all
                || force_list.count(tag) > 0;

            sep();
            json_escape(tag.c_str(), buf);
            buf += ':';
            if (!nl.empty()) buf += ' ';

            if (as_list) {
                buf += '[';
                bool first_item = true;
                for (pugi::xml_node s = node.first_child(); s;
                     s = s.next_sibling()) {
                    if (s.type() != pugi::node_element) continue;
                    if (strcmp(s.name(), tag.c_str()) != 0) continue;
                    if (!first_item) buf += ',';
                    buf += nl;
                    buf += pad1 + ind;
                    first_item = false;
                    node_to_json(s, buf, attr_prefix, cdata_key,
                                 force_list, force_all,
                                 nl, ind, depth + 2);
                }
                buf += nl;
                buf += pad1;
                buf += ']';
            } else {
                node_to_json(c, buf, attr_prefix, cdata_key,
                             force_list, force_all,
                             nl, ind, depth + 1);
            }
        }

        buf += nl;
        buf += pad;
        buf += '}';
    }

    // ---------------------------------------------------------------------------
    // Top-level entry — wraps root in {"tag": ...}
    // ---------------------------------------------------------------------------
    static std::string xml_node_to_json(
        pugi::xml_node     root,
        const char*        attr_prefix,
        const char*        cdata_key,
        const char* const* force_list_items,   // null-terminated array
        bool               force_all,
        bool               pretty,
        const char*        indent
    ) {
        std::unordered_set<std::string> force_list;
        if (force_list_items) {
            for (int i = 0; force_list_items[i]; ++i)
                force_list.insert(force_list_items[i]);
        }

        std::string nl   = pretty ? "\\n" : "";
        std::string ind  = pretty ? indent : "";

        std::string buf;
        buf.reserve(4096);

        buf += '{';
        if (pretty) buf += "\\n  ";
        json_escape(root.name(), buf);
        buf += ':';
        if (pretty) buf += ' ';

        node_to_json(root, buf, attr_prefix, cdata_key,
                     force_list, force_all, nl, ind, 1);

        if (pretty) buf += "\\n";
        buf += '}';
        return buf;
    }

    // xml_node_to_json_with_set — accepts Python set directly via CPython API
    static std::string xml_node_to_json_with_set(
        pugi::xml_node root,
        const char*    attr_prefix,
        const char*    cdata_key,
        PyObject*      force_set,
        bool           force_all,
        bool           pretty,
        const char*    indent
    ) {
        std::unordered_set<std::string> force_list;
        if (force_set && force_set != Py_None) {
            PyObject* iter = PyObject_GetIter(force_set);
            if (iter) {
                PyObject* item;
                while ((item = PyIter_Next(iter)) != nullptr) {
                    const char* s = PyUnicode_AsUTF8(item);
                    if (s) force_list.insert(s);
                    Py_DECREF(item);
                }
                Py_DECREF(iter);
            }
        }
        std::string nl  = pretty ? "\\n" : "";
        std::string ind = pretty ? indent : "";
        std::string buf;
        buf.reserve(4096);
        buf += '{';
        if (pretty) buf += "\\n  ";
        json_escape(root.name(), buf);
        buf += ':';
        if (pretty) buf += ' ';
        node_to_json(root, buf, attr_prefix, cdata_key,
                     force_list, force_all, nl, ind, 1);
        if (pretty) buf += "\\n";
        buf += '}';
        return buf;
    }

    // =========================================================================
    // Constant-memory streaming XML -> JSON Lines converter
    // =========================================================================
    //
    // Output is JSON Lines: one self-contained JSON object per line, not a
    // single big JSON array/document. A JSON array needs to know, before
    // closing a bracket, whether more items follow -- which would force
    // buffering. JSONL sidesteps this: every line stands alone, so a record
    // can be written the instant it's fully parsed.
    //
    // Within ONE record, repeated child tags (e.g. many <tag> under one
    // <item>) still need an array-vs-scalar decision. We resolve this with a
    // two-pass scan scoped to that single record's byte range in the file
    // (not the whole document):
    //   Pass 1 (count): re-read just those bytes, counting how many times
    //                   each direct-child tag appears at each depth. Only
    //                   small integer counters are kept (bounded by the
    //                   record's distinct tag count, not its data volume).
    //   Pass 2 (emit):  re-read the same bytes again and stream JSON
    //                   directly to the output file, using Pass 1's counts
    //                   to make every comma/bracket decision in O(1) with no
    //                   buffering of any subtree.
    //
    // Net memory profile, independent of file size or record count: one
    // yxml stack, one read-chunk buffer, one write-chunk buffer, and a few
    // small tag-count maps scoped to whichever single record is currently
    // being processed. Total stays in the hundreds of KB whether the input
    // is 1 MB or 100 GB.

    #include <cstdio>
    #include <cstring>
    #include <vector>
    #include <string>
    #include <unordered_map>

    #ifndef PYGIXML_IO_CHUNK
    #define PYGIXML_IO_CHUNK (1 << 16)   /* 64 KB */
    #endif
    #ifndef PYGIXML_OUT_CHUNK
    #define PYGIXML_OUT_CHUNK (1 << 16)  /* 64 KB */
    #endif

    // ---- small buffered writer over a FILE* --------------------------------
    struct JOutBuf {
        FILE*  fp;
        char   buf[PYGIXML_OUT_CHUNK];
        size_t len = 0;
        bool   io_error = false;

        explicit JOutBuf(FILE* f) : fp(f) {}
        inline void flush() {
            if (len == 0) return;
            if (fwrite(buf, 1, len, fp) != len) io_error = true;
            len = 0;
        }
        inline void putc1(char c) {
            if (len >= PYGIXML_OUT_CHUNK) flush();
            buf[len++] = c;
        }
        inline void write(const char* s, size_t n) {
            if (n > PYGIXML_OUT_CHUNK) {
                flush();
                if (fwrite(s, 1, n, fp) != n) io_error = true;
                return;
            }
            if (len + n > PYGIXML_OUT_CHUNK) flush();
            memcpy(buf + len, s, n);
            len += n;
        }
        inline void write(const char* s) { write(s, strlen(s)); }
        inline void write(const std::string& s) { write(s.data(), s.size()); }

        inline void write_json_string(const char* s, size_t n) {
            putc1('"');
            size_t start = 0;
            char ubuf[8];
            for (size_t i = 0; i < n; ++i) {
                unsigned char c = (unsigned char)s[i];
                const char* esc = nullptr;
                switch (c) {
                    case '"':  esc = "\\\\\\""; break;
                    case '\\\\': esc = "\\\\\\\\"; break;
                    case '\\n': esc = "\\\\n";  break;
                    case '\\r': esc = "\\\\r";  break;
                    case '\\t': esc = "\\\\t";  break;
                    default:
                        if (c < 0x20) {
                            snprintf(ubuf, sizeof(ubuf), "\\\\u%04x", c);
                            esc = ubuf;
                        }
                }
                if (esc) {
                    if (i > start) write(s + start, i - start);
                    write(esc);
                    start = i + 1;
                }
            }
            if (start < n) write(s + start, n - start);
            putc1('"');
        }
        inline void write_json_string(const std::string& s) {
            write_json_string(s.data(), s.size());
        }
    };

    static inline bool pg_is_ws(char c) {
        return c==' '||c=='\\t'||c=='\\n'||c=='\\r';
    }
    static inline bool pg_all_ws(const char* s, size_t n) {
        for (size_t i=0;i<n;++i) if (!pg_is_ws(s[i])) return false;
        return true;
    }

    // Pass 1: count direct-child tag occurrences at every depth, for one
    // record's byte range [start, end) of the input file.
    struct TagCounts {
        std::vector<std::unordered_map<std::string,int>> counts;
        void ensure_depth(size_t d) {
            if (counts.size() <= d) counts.resize(d + 1);
        }
    };

    static bool pg_count_pass(
        FILE* fin, long start_off, long end_off,
        size_t stack_size, size_t io_chunk,
        TagCounts& out, char* errbuf, size_t errbuf_size
    ) {
        if (fseek(fin, start_off, SEEK_SET) != 0) {
            snprintf(errbuf, errbuf_size, "seek failed for count pass");
            return false;
        }
        std::vector<char> ystack(stack_size);
        yxml_t x;
        yxml_init(&x, ystack.data(), stack_size);

        std::vector<char> chunk(io_chunk);
        long remaining = end_off - start_off;
        int depth = -1;

        while (remaining > 0) {
            size_t want = (size_t)((remaining < (long)io_chunk) ? remaining : (long)io_chunk);
            size_t nread = fread(chunk.data(), 1, want, fin);
            if (nread == 0) break;
            remaining -= (long)nread;

            for (size_t i = 0; i < nread; ++i) {
                int ret = yxml_parse(&x, (unsigned char)chunk[i]);
                if (ret < 0) {
                    snprintf(errbuf, errbuf_size,
                             "XML parse error during count pass (code %d)", ret);
                    return false;
                }
                if (ret == YXML_ELEMSTART) {
                    depth++;
                    if (depth >= 1) {
                        size_t nlen = yxml_symlen(&x, x.elem);
                        out.ensure_depth((size_t)depth);
                        out.counts[depth][std::string(x.elem, nlen)]++;
                    }
                } else if (ret == YXML_ELEMEND) {
                    if (depth == 0) { depth--; goto done; }
                    depth--;
                }
            }
        }
        done:
        return true;
    }

    // Pass 2: re-read the same byte range, emit JSON directly using the
    // counts gathered in Pass 1 -- no buffering of any subtree.
    struct EmitLevel {
        std::string tag;
        bool        wrote_brace = false;
        bool        first_field = true;
        std::string open_list_tag;
        bool        in_open_list = false;
        bool        text_flushed = false;
        int         depth = 0;
    };

    static bool pg_emit_pass(
        FILE* fin, long start_off, long end_off,
        size_t stack_size, size_t io_chunk,
        JOutBuf& w,
        const TagCounts& counts,
        const std::string& attr_prefix,
        const std::string& cdata_key,
        const std::vector<std::string>& force_list,
        bool force_all,
        char* errbuf, size_t errbuf_size
    ) {
        auto is_forced = [&](const std::string& tag) {
            if (force_all) return true;
            for (auto& t : force_list) if (t == tag) return true;
            return false;
        };
        auto count_of = [&](int depth, const std::string& tag) -> int {
            if (depth < 0 || depth >= (int)counts.counts.size()) return 1;
            auto it = counts.counts[depth].find(tag);
            return it == counts.counts[depth].end() ? 1 : it->second;
        };

        if (fseek(fin, start_off, SEEK_SET) != 0) {
            snprintf(errbuf, errbuf_size, "seek failed for emit pass");
            return false;
        }
        std::vector<char> ystack(stack_size);
        yxml_t x;
        yxml_init(&x, ystack.data(), stack_size);

        std::vector<char> chunk(io_chunk);
        long remaining = end_off - start_off;

        std::vector<EmitLevel> levels;
        std::string cur_attr_key, cur_attr_val;
        std::string cur_text;
        bool have_pending_text = false;

        auto ensure_open = [&](EmitLevel& lv) {
            if (!lv.wrote_brace) {
                w.putc1('{');
                lv.wrote_brace = true;
                lv.first_field = true;
            }
        };
        auto field_sep = [&](EmitLevel& lv) {
            if (!lv.first_field) w.putc1(',');
            lv.first_field = false;
        };
        auto flush_text_field = [&](EmitLevel& lv) {
            if (!have_pending_text) return;
            if (lv.text_flushed) {
                // pugixml's child_value() (used by the in-memory DOM
                // serializer for parity) only ever returns the FIRST
                // text run of an element -- text appearing after later
                // child elements is not concatenated. Match that here:
                // once we've already emitted this level's "#text" field
                // once, silently drop any further text.
                cur_text.clear();
                have_pending_text = false;
                return;
            }
            bool blank = pg_all_ws(cur_text.data(), cur_text.size());
            if (!blank) {
                ensure_open(lv);
                field_sep(lv);
                w.write_json_string(cdata_key);
                w.putc1(':');
                w.write_json_string(cur_text);
            }
            lv.text_flushed = true;
            cur_text.clear();
            have_pending_text = false;
        };

        while (remaining > 0) {
            size_t want = (size_t)((remaining < (long)io_chunk) ? remaining : (long)io_chunk);
            size_t nread = fread(chunk.data(), 1, want, fin);
            if (nread == 0) break;
            remaining -= (long)nread;

            for (size_t i = 0; i < nread; ++i) {
                int ret = yxml_parse(&x, (unsigned char)chunk[i]);
                if (ret < 0) {
                    snprintf(errbuf, errbuf_size,
                             "XML parse error during emit pass (code %d)", ret);
                    return false;
                }

                switch (ret) {
                case YXML_OK: break;

                case YXML_ELEMSTART: {
                    if (!levels.empty()) flush_text_field(levels.back());

                    size_t nlen = yxml_symlen(&x, x.elem);
                    std::string tag(x.elem, nlen);
                    int depth = (int)levels.size();

                    if (!levels.empty()) {
                        EmitLevel& parent = levels.back();
                        ensure_open(parent);
                        int cnt = count_of(depth, tag);
                        bool as_list = (cnt > 1) || is_forced(tag);

                        if (as_list) {
                            if (parent.in_open_list && parent.open_list_tag == tag) {
                                w.putc1(',');
                            } else {
                                if (parent.in_open_list) {
                                    w.putc1(']');
                                    parent.in_open_list = false;
                                }
                                field_sep(parent);
                                w.write_json_string(tag);
                                w.putc1(':');
                                w.putc1('[');
                                parent.in_open_list = true;
                                parent.open_list_tag = tag;
                            }
                        } else {
                            if (parent.in_open_list) {
                                w.putc1(']');
                                parent.in_open_list = false;
                            }
                            field_sep(parent);
                            w.write_json_string(tag);
                            w.putc1(':');
                        }
                    }

                    EmitLevel lv;
                    lv.tag = tag;
                    lv.depth = depth;
                    levels.push_back(lv);
                    break;
                }

                case YXML_ATTRSTART: {
                    size_t nlen = yxml_symlen(&x, x.attr);
                    cur_attr_key.assign(x.attr, nlen);
                    cur_attr_val.clear();
                    break;
                }
                case YXML_ATTRVAL:
                    cur_attr_val += x.data;
                    break;
                case YXML_ATTREND: {
                    EmitLevel& lv = levels.back();
                    ensure_open(lv);
                    field_sep(lv);
                    w.write_json_string(attr_prefix + cur_attr_key);
                    w.putc1(':');
                    w.write_json_string(cur_attr_val);
                    break;
                }

                case YXML_CONTENT:
                    cur_text += x.data;
                    have_pending_text = true;
                    break;

                case YXML_ELEMEND: {
                    EmitLevel lv = levels.back();
                    levels.pop_back();

                    if (lv.in_open_list) {
                        w.putc1(']');
                        lv.in_open_list = false;
                    }

                    if (!lv.wrote_brace) {
                        bool blank = !have_pending_text ||
                                     pg_all_ws(cur_text.data(), cur_text.size());
                        if (blank) w.write("null", 4);
                        else w.write_json_string(cur_text);
                        cur_text.clear();
                        have_pending_text = false;
                    } else {
                        flush_text_field(lv);
                        w.putc1('}');
                    }

                    if (levels.empty()) {
                        w.putc1('\\n');
                        return true;   // one record fully emitted
                    }
                    break;
                }

                case YXML_PISTART: case YXML_PICONTENT: case YXML_PIEND:
                    break;

                default: break;
                }
            }
        }
        return true;
    }

    // Top-level driver: scans the whole file once (O(depth) memory) to find
    // each record's byte range, then runs Pass1+Pass2 on just that slice.
    //   mode A (record_tag given): a "record" is any element with that tag
    //     name, regardless of nesting depth.
    //   mode B (record_tag NULL/empty): a "record" is each direct child of
    //     the document's root element.
    static long long xml_stream_to_jsonl_file(
        const char*  xml_path,
        const char*  jsonl_path,
        const char*  record_tag,
        const char*  attr_prefix_c,
        const char*  cdata_key_c,
        PyObject*    force_set,
        bool         force_all,
        size_t       stack_size,
        size_t       io_buf_size,
        char*        errbuf,
        size_t       errbuf_size
    ) {
        std::string attr_prefix(attr_prefix_c);
        std::string cdata_key(cdata_key_c);
        bool mode_a = record_tag && record_tag[0] != '\\0';
        std::string rtag = mode_a ? std::string(record_tag) : std::string();

        std::vector<std::string> force_list;
        if (force_set && force_set != Py_None) {
            PyObject* it = PyObject_GetIter(force_set);
            if (it) {
                PyObject* item;
                while ((item = PyIter_Next(it))) {
                    const char* s = PyUnicode_AsUTF8(item);
                    if (s) force_list.push_back(s);
                    Py_DECREF(item);
                }
                Py_DECREF(it);
            }
        }

        FILE* xin = fopen(xml_path, "rb");
        if (!xin) {
            snprintf(errbuf, errbuf_size, "cannot open XML input: %s", xml_path);
            return -1;
        }
        FILE* fout = fopen(jsonl_path, "wb");
        if (!fout) {
            fclose(xin);
            snprintf(errbuf, errbuf_size, "cannot open JSON Lines output: %s", jsonl_path);
            return -1;
        }
        JOutBuf w(fout);

        yxml_t x;
        std::vector<char> ystack(stack_size);
        yxml_init(&x, ystack.data(), stack_size);

        std::vector<char> chunk(io_buf_size);
        long long count = 0;
        bool ok = true;

        int  depth = 0;
        std::vector<long> elem_start_off(64, -1);
        std::vector<std::string> elem_tag_at(64);
        long pos = 0;

        // depth-by-depth tag-name tracking (elem_tag_at) is used directly
        // to detect matching ancestors -- see ELEMEND handling below.

        while (ok) {
            size_t nread = fread(chunk.data(), 1, io_buf_size, xin);
            if (nread == 0) break;

            bool buffer_stale = false;   // set true after a record consumes
                                          // bytes via fseek -- the rest of
                                          // this chunk no longer reflects
                                          // the file's current read position

            for (size_t i = 0; i < nread && !buffer_stale; ++i) {
                long byte_pos = pos;
                pos++;

                int ret = yxml_parse(&x, (unsigned char)chunk[i]);
                if (ret < 0) {
                    snprintf(errbuf, errbuf_size,
                             "XML parse error (yxml code %d) at line %u byte %ld",
                             ret, x.line, byte_pos);
                    ok = false; break;
                }

                if (ret == YXML_ELEMSTART) {
                    if ((size_t)depth >= elem_start_off.size()) {
                        elem_start_off.resize(elem_start_off.size() * 2, -1);
                        elem_tag_at.resize(elem_tag_at.size() * 2);
                    }
                    size_t nlen = yxml_symlen(&x, x.elem);
                    // yxml's ELEMSTART fires when it consumes the
                    // terminator character *after* the tag name (the
                    // space, '>' or '/' following it) -- byte_pos at that
                    // point is the terminator's position. The leading '<'
                    // is therefore nlen+1 bytes earlier.
                    elem_start_off[depth] = byte_pos - (long)nlen - 1;
                    elem_tag_at[depth].assign(x.elem, nlen);
                    depth++;
                }
                else if (ret == YXML_ELEMEND) {
                    depth--;

                    bool is_target;
                    if (mode_a) {
                        // Only the OUTERMOST element named record_tag is a
                        // record; if any still-open ancestor (depth' <
                        // depth) also has this tag name, this is a nested
                        // occurrence and must NOT be emitted separately --
                        // it's already part of the ancestor's content.
                        bool has_matching_ancestor = false;
                        for (int d = 0; d < depth; ++d) {
                            if (d < (int)elem_tag_at.size() && elem_tag_at[d] == rtag) {
                                has_matching_ancestor = true;
                                break;
                            }
                        }
                        is_target = !has_matching_ancestor
                                    && depth < (int)elem_tag_at.size()
                                    && elem_tag_at[depth] == rtag;
                    } else {
                        is_target = (depth == 1);
                    }

                    if (is_target && depth >= 0 && (size_t)depth < elem_start_off.size()) {
                        long start_off = elem_start_off[depth];
                        long end_off   = byte_pos + 1;

                        TagCounts tc;
                        if (!pg_count_pass(xin, start_off, end_off,
                                            stack_size, io_buf_size,
                                            tc, errbuf, errbuf_size)) {
                            ok = false; break;
                        }
                        if (!pg_emit_pass(xin, start_off, end_off,
                                           stack_size, io_buf_size, w,
                                           tc, attr_prefix, cdata_key,
                                           force_list, force_all,
                                           errbuf, errbuf_size)) {
                            ok = false; break;
                        }
                        // The count/emit passes seeked `xin` around for
                        // their own purposes. Restore the file position to
                        // where the outer scan should resume (`pos`), and
                        // mark the currently-loaded `chunk` buffer stale --
                        // whatever bytes after index i it still holds were
                        // read *before* this seek and no longer correspond
                        // to what's at `pos` onward, so we must stop using
                        // them and re-fread from the new position.
                        fseek(xin, pos, SEEK_SET);
                        count++;
                        buffer_stale = true;
                    }
                }
            }
            if (!ok) break;
        }

        if (ok) {
            int eof_ret = yxml_eof(&x);
            if (eof_ret < 0) {
                snprintf(errbuf, errbuf_size,
                         "unexpected end of XML (yxml code %d)", eof_ret);
                ok = false;
            }
        }

        w.flush();
        if (w.io_error) ok = false;
        fclose(xin);
        fclose(fout);

        if (!ok) return -2;
        return count;
    }

    // =========================================================================
    // Constant-memory streaming XML -> *standard* JSON converter
    // (single pass, seek-and-patch -- output is a normal JSON document,
    //  not JSON Lines)
    // =========================================================================
    //
    // Same goals as the JSONL engine above (no pugixml DOM, no Python
    // dict/list, no `json` module -- every byte hand-emitted in C++), but
    // produces ONE valid JSON document (an object or array, with proper
    // brackets/commas) instead of one-record-per-line output.
    //
    // The core difficulty solved here: JSON needs to know, before closing
    // a `]`, whether more array items follow -- and for a *repeated child
    // tag*, whether the first occurrence will end up alone (-> plain
    // value) or accompanied by siblings (-> array). We resolve this with
    // an in-place "reserve a byte, patch it later" trick instead of a
    // separate counting pass:
    //
    //   * The first time a child tag T closes under some parent, we
    //     reserve a single placeholder byte (a space) right before its
    //     value and remember that position (`bracket_pos`). We then write
    //     T's value as a plain (non-array) value, optimistically.
    //
    //   * If a *second* T sibling appears later under the same parent:
    //       - seek back to `bracket_pos` and overwrite that one
    //         placeholder byte with '[' (a 1-byte patch, O(1));
    //       - seek to the end of the previously-written value and append
    //         ",second_value" (and eventually a closing ']' once the
    //         parent itself closes).
    //     This works directly (no shifting) as long as nothing else was
    //     written to the file between the first T value and now --
    //     i.e. T's occurrences are contiguous in the output, which is the
    //     common case when same-tag siblings are adjacent in the XML.
    //
    //   * If something else (a different child) WAS written in between --
    //     i.e. the file's current write position has moved past where T's
    //     last value ended -- we "splice": shift the bytes that were
    //     written after T's last value forward (using a small fixed-size
    //     buffer, moving the file's tail in chunks) just enough to open a
    //     gap, drop the new T value into that gap, and update bookkeeping
    //     so the *next* T occurrence is contiguous again. This costs
    //     O(bytes between the two occurrences), not O(file size) -- and
    //     for the common "siblings are adjacent" case it never triggers
    //     at all.
    //
    //   * Third and later occurrences of the same tag, once `is_list` is
    //     already true and writes are still contiguous, are a pure
    //     append: no seeking at all.
    //
    // Net memory profile: O(nesting depth x distinct child tags per open
    // level) for bookkeeping, plus one small fixed-size shift buffer used
    // only on the (uncommon) non-contiguous-sibling path. Independent of
    // file size, record size, and number of repeated children.

    #include <functional>
    #include <algorithm>
    #include <utility>

    #ifndef PYGIXML_SHIFT_BUF
    #define PYGIXML_SHIFT_BUF (1 << 16)   /* 64 KB scratch for splicing */
    #endif

    // Per-(parent-level, child-tag) bookkeeping.
    struct PJChildSlot {
        long bracket_pos    = -1;    // offset of the reserved placeholder byte
        long last_value_end = -1;    // offset right after this tag's most
                                      // recently written value
        bool is_list        = false;
        // When a non-contiguous repeat is detected at open_child() time,
        // we can't relocate the new value into the gap yet -- it hasn't
        // been written. Instead we append a ',' + the value at the true
        // tail (like any other write), and defer the actual splice/
        // relocation until close_child() learns where the value ended.
        bool pending_splice     = false;
        long pending_gap_start  = -1;  // where to relocate the value to
        long pending_value_start = -1; // where the (comma+)value append began
    };

    struct PJLevel {
        std::string tag;
        bool wrote_brace          = false;  // '{' written for this level?
        bool first_field          = true;   // comma bookkeeping for this object
        bool any_attr_or_child    = false;
        bool text_flushed         = false;  // see flush_text_field's comment
        int  depth                = 0;      // nesting depth, for indentation
        std::unordered_map<std::string, PJChildSlot> children;
        // attribute de-dup, per xmltodict convention: last value for a
        // repeated attribute name wins (XML itself forbids duplicate
        // attribute names on one element, but be lenient on malformed input)
    };

    // A small helper bound to one open FILE* that knows how to do the
    // "shift a range forward to open a gap" operation used when sibling
    // writes were not contiguous.
    struct PJFileEditor {
        FILE* fp;
        long  tail_pos;   // current logical end-of-file write position

        explicit PJFileEditor(FILE* f) : fp(f), tail_pos(0) {}

        inline long pos() {
            fflush(fp);
            return ftell(fp);
        }

        inline void seek(long off) {
            fflush(fp);
            fseek(fp, off, SEEK_SET);
        }

        inline void write_at_tail(const char* s, size_t n) {
            seek(tail_pos);
            fwrite(s, 1, n, fp);
            tail_pos += (long)n;
        }
        inline void write_at_tail(const std::string& s) {
            write_at_tail(s.data(), s.size());
        }
        inline void write_at_tail(char c) {
            write_at_tail(&c, 1);
        }

        // Overwrite exactly one byte at a previously-reserved offset.
        inline void patch_byte(long off, char c) {
            seek(off);
            fwrite(&c, 1, 1, fp);
            seek(tail_pos);   // restore logical write position
        }

        // Insert `ins` (length n) right before `gap_start`, by shifting
        // everything currently in [gap_start, tail_pos) forward by n
        // bytes, then writing `ins` into the freed space. Updates
        // tail_pos accordingly. Cost: O(tail_pos - gap_start), using a
        // small fixed-size buffer (not the whole range at once).
        bool splice_insert(long gap_start, const char* ins, size_t n) {
            long region_len = tail_pos - gap_start;
            if (region_len < 0) return false;
            if (region_len == 0) {
                write_at_tail(ins, n);
                return true;
            }

            std::vector<char> buf(PYGIXML_SHIFT_BUF);
            // Move the [gap_start, tail_pos) region forward by n bytes,
            // working from the END backwards so source and destination
            // ranges (which can overlap once n < region_len) never
            // clobber data we haven't read yet.
            long remaining = region_len;
            while (remaining > 0) {
                long chunk = (remaining < (long)buf.size()) ? remaining : (long)buf.size();
                long src_off = gap_start + remaining - chunk;
                long dst_off = src_off + (long)n;

                seek(src_off);
                size_t got = fread(buf.data(), 1, (size_t)chunk, fp);
                if ((long)got != chunk) return false;

                seek(dst_off);
                size_t put = fwrite(buf.data(), 1, (size_t)chunk, fp);
                if ((long)put != (size_t)chunk) return false;

                remaining -= chunk;
            }

            // Now [gap_start, gap_start+n) is free -- write the insertion.
            seek(gap_start);
            fwrite(ins, 1, n, fp);

            tail_pos += (long)n;
            seek(tail_pos);
            return true;
        }
        bool splice_insert(long gap_start, const std::string& s) {
            return splice_insert(gap_start, s.data(), s.size());
        }
    };

    static inline bool pgj_is_ws(char c) {
        return c==' '||c=='\\t'||c=='\\n'||c=='\\r';
    }
    static inline bool pgj_all_ws(const char* s, size_t n) {
        for (size_t i=0;i<n;++i) if (!pgj_is_ws(s[i])) return false;
        return true;
    }

    // Writes a JSON-escaped string straight to the editor's tail.
    static void pgj_write_escaped(PJFileEditor& ed, const char* s, size_t n) {
        std::string tmp;
        tmp.reserve(n + 2);
        tmp += '"';
        for (size_t i = 0; i < n; ++i) {
            unsigned char c = (unsigned char)s[i];
            switch (c) {
                case '"':  tmp += "\\\\\\""; break;
                case '\\\\': tmp += "\\\\\\\\"; break;
                case '\\n': tmp += "\\\\n";  break;
                case '\\r': tmp += "\\\\r";  break;
                case '\\t': tmp += "\\\\t";  break;
                default:
                    if (c < 0x20) {
                        char ub[8];
                        snprintf(ub, sizeof(ub), "\\\\u%04x", c);
                        tmp += ub;
                    } else tmp += (char)c;
            }
        }
        tmp += '"';
        ed.write_at_tail(tmp);
    }
    static void pgj_write_escaped(PJFileEditor& ed, const std::string& s) {
        pgj_write_escaped(ed, s.data(), s.size());
    }

    // -------------------------------------------------------------------
    // Main single-pass, seek-and-patch XML -> JSON document converter.
    // -------------------------------------------------------------------
    static long long xml_stream_to_json_file(
        const char*  xml_path,
        const char*  json_path,
        const char*  attr_prefix_c,
        const char*  cdata_key_c,
        PyObject*    force_set,
        bool         force_all,
        int          indent_width,
        size_t       stack_size,
        size_t       io_buf_size,
        char*        errbuf,
        size_t       errbuf_size
    ) {
        std::string attr_prefix(attr_prefix_c);
        std::string cdata_key(cdata_key_c);
        bool pretty = indent_width > 0;
        std::string nl  = pretty ? "\\n" : "";
        std::string ind = pretty ? std::string((size_t)indent_width, ' ') : "";

        std::vector<std::string> force_list;
        if (force_set && force_set != Py_None) {
            PyObject* it = PyObject_GetIter(force_set);
            if (it) {
                PyObject* item;
                while ((item = PyIter_Next(it))) {
                    const char* s = PyUnicode_AsUTF8(item);
                    if (s) force_list.push_back(s);
                    Py_DECREF(item);
                }
                Py_DECREF(it);
            }
        }
        auto is_forced = [&](const std::string& tag) {
            if (force_all) return true;
            for (auto& t : force_list) if (t == tag) return true;
            return false;
        };

        FILE* xin = fopen(xml_path, "rb");
        if (!xin) {
            snprintf(errbuf, errbuf_size, "cannot open XML input: %s", xml_path);
            return -1;
        }
        FILE* fout = fopen(json_path, "w+b");   // read+write: needed for seek/patch
        if (!fout) {
            fclose(xin);
            snprintf(errbuf, errbuf_size, "cannot open JSON output: %s", json_path);
            return -1;
        }

        PJFileEditor ed(fout);

        std::vector<char> ystack(stack_size);
        yxml_t x;
        yxml_init(&x, ystack.data(), stack_size);

        std::vector<char> chunk(io_buf_size);

        std::vector<PJLevel> levels;
        std::string cur_attr_key, cur_attr_val;
        std::string cur_text;
        bool have_pending_text = false;
        long long elements_seen = 0;

        auto pad_for = [&](int depth) {
            std::string p;
            for (int i = 0; i < depth; ++i) p += ind;
            return p;
        };

        auto ensure_open = [&](PJLevel& lv) {
            if (!lv.wrote_brace) {
                ed.write_at_tail('{');
                lv.wrote_brace = true;
                lv.first_field = true;
            }
        };
        auto field_sep = [&](PJLevel& lv) {
            if (!lv.first_field) ed.write_at_tail(',');
            ed.write_at_tail(nl);
            ed.write_at_tail(pad_for(lv.depth + 1));
            lv.first_field = false;
        };

        // Flush this level's accumulated direct text as a "#text" field
        // (only meaningful once we know the level is becoming an object --
        // i.e. it already has attrs/children, or is about to get one).
        auto flush_text_field = [&](PJLevel& lv) {
            if (!have_pending_text) return;
            if (lv.text_flushed) {
                // Match pugixml's child_value() semantics (used by the
                // in-memory DOM serializer): only the FIRST text run of
                // an element becomes "#text"; text appearing after later
                // child elements is dropped, not concatenated.
                cur_text.clear();
                have_pending_text = false;
                return;
            }
            bool blank = pgj_all_ws(cur_text.data(), cur_text.size());
            if (!blank) {
                ensure_open(lv);
                field_sep(lv);
                pgj_write_escaped(ed, cdata_key);
                ed.write_at_tail(':');
                if (!nl.empty()) ed.write_at_tail(' ');
                pgj_write_escaped(ed, cur_text);
            }
            lv.text_flushed = true;
            cur_text.clear();
            have_pending_text = false;
        };

        // Called when a child element with tag `tag` STARTS under `parent`
        // (i.e. at the child's ELEMSTART). This writes everything that
        // must precede the child's own content: the field separator, the
        // `"tag":` key, and -- for repeated tags -- the comma (and, if
        // this is exactly the moment we learn it's a list, the '['
        // patch). After this returns, the caller is free to write the
        // child's own value (object/array/scalar) directly at the
        // current tail, and it will land in the right place.
        //
        // This ordering (key/bracket prefix written eagerly at
        // ELEMSTART, not deferred to ELEMEND) is essential: a nested
        // object's own '{' starts getting written the moment its FIRST
        // child needs it open, which happens immediately during parsing,
        // long before the object itself closes. If the parent's key
        // prefix were written lazily at the child's ELEMEND instead, the
        // child's content would already be sitting in the file BEFORE
        // its own key -- corrupting the structure. Writing the prefix at
        // ELEMSTART guarantees correct ordering for arbitrarily deep
        // nesting.
        auto open_child = [&](PJLevel& parent, const std::string& tag) {
            ensure_open(parent);
            auto it = parent.children.find(tag);
            std::string item_pad = pad_for(parent.depth + 1) + ind;  // pad1 + ind

            if (it == parent.children.end()) {
                // ---- first occurrence ------------------------------------
                field_sep(parent);
                pgj_write_escaped(ed, tag);
                ed.write_at_tail(':');
                if (!nl.empty()) ed.write_at_tail(' ');

                PJChildSlot slot;
                if (is_forced(tag)) {
                    ed.write_at_tail('[');
                    ed.write_at_tail(nl);
                    ed.write_at_tail(item_pad);
                    slot.is_list = true;
                } else {
                    slot.bracket_pos = ed.tail_pos;
                    ed.write_at_tail(' ');   // reserved placeholder byte
                }
                parent.children[tag] = slot;
                return;
            }

            PJChildSlot& slot = it->second;
            bool contiguous = (slot.last_value_end == ed.tail_pos);

            if (contiguous) {
                if (!slot.is_list) {
                    ed.patch_byte(slot.bracket_pos, '[');
                    slot.is_list = true;
                }
                ed.write_at_tail(',');
                ed.write_at_tail(nl);
                ed.write_at_tail(item_pad);
                return;
            }

            // ---- non-contiguous: a different child was written after
            // this tag's last value. We can't relocate the new value
            // into the gap right after that last value yet, because the
            // value hasn't been written -- it may itself be a deeply
            // nested object spanning many further ELEMSTART/ELEMEND
            // events. Instead: append ',' at the true tail (a normal,
            // cheap write) and let the new value be written normally
            // wherever subsequent processing puts it; once close_child()
            // observes that the value is complete, IT performs the
            // actual relocation of the whole "," + value blob into the
            // gap in one shot.
            bool was_list_already = slot.is_list;
            if (!slot.is_list) {
                ed.patch_byte(slot.bracket_pos, '[');
                slot.is_list = true;
            }
            (void)was_list_already;
            slot.pending_splice = true;
            slot.pending_gap_start = slot.last_value_end;
            slot.pending_value_start = ed.tail_pos;
            ed.write_at_tail(',');
            ed.write_at_tail(nl);
            ed.write_at_tail(item_pad);
            // last_value_end is intentionally left stale here -- it still
            // points at the gap location close_child() needs to splice
            // into. It gets corrected (to the post-relocation position)
            // once close_child() finishes the splice.
        };

        // Called when a child element with tag `tag` under `parent` ENDS
        // (i.e. at the child's ELEMEND), AFTER its own content has been
        // fully written (via close_level). Just records where the value
        // ended, for the next sibling/closing-bracket bookkeeping.
        auto close_child = [&](PJLevel& parent, const std::string& tag) {
            PJChildSlot& slot = parent.children[tag];

            if (!slot.pending_splice) {
                slot.last_value_end = ed.tail_pos;
                return;
            }

            // The ',' + new value were appended at the true tail (from
            // pending_value_start to the current tail). Relocate that
            // whole blob into the gap right after this tag's previous
            // value (pending_gap_start), then fix up every other child
            // slot of this parent whose offsets point at or after the
            // gap -- they all just shifted forward by the blob's length.
            long blob_start = slot.pending_value_start;
            long blob_end   = ed.tail_pos;
            long blob_len   = blob_end - blob_start;
            long gap_start  = slot.pending_gap_start;

            std::vector<char> blob(blob_len);
            ed.seek(blob_start);
            size_t nrd = fread(blob.data(), 1, (size_t)blob_len, fout);
            (void)nrd;  // best-effort; overall ok/errbuf path covers I/O
                        // failures elsewhere in this function
            // Roll the tail back to before the blob -- it will be
            // re-appended (at its final, correct position) by
            // splice_insert below.
            ed.tail_pos = blob_start;

            ed.splice_insert(gap_start, blob.data(), blob.size());
            long shift = blob_len;

            for (auto& kv : parent.children) {
                PJChildSlot& other = kv.second;
                if (&other == &slot && !other.pending_splice) continue;
                if (&other == &slot) continue;  // fixed explicitly below
                if (other.bracket_pos >= gap_start) other.bracket_pos += shift;
                if (other.last_value_end >= gap_start) other.last_value_end += shift;
            }

            slot.pending_splice = false;
            slot.last_value_end = gap_start + shift;
        };

        // Closes out a level: writes any trailing text field, closes any
        // child tags that ended up as lists (']'), and writes the final
        // '}' (or, for a leaf with no attrs/children, a scalar/null).
        auto close_level = [&](PJLevel& lv, int depth) -> void {
            if (!lv.wrote_brace) {
                bool blank = !have_pending_text ||
                             pgj_all_ws(cur_text.data(), cur_text.size());
                if (blank) ed.write_at_tail("null", 4);
                else pgj_write_escaped(ed, cur_text);
                cur_text.clear();
                have_pending_text = false;
                return;
            }
            flush_text_field(lv);

            // Close every child tag that ended up as a list, in ascending
            // order of where its content ends in the file. This matters
            // because closing one (via splice_insert, which shifts bytes
            // forward) can invalidate the still-pending last_value_end of
            // ANOTHER list whose content comes later in the file -- so we
            // must process strictly left-to-right and shift the remaining
            // pending offsets by however many bytes each splice inserted.
            std::vector<std::pair<long, std::string>> pending_closes;
            for (auto& kv : lv.children) {
                if (kv.second.is_list) {
                    pending_closes.push_back({kv.second.last_value_end, kv.first});
                }
            }
            std::sort(pending_closes.begin(), pending_closes.end());

            for (auto& pc : pending_closes) {
                long close_at = pc.first;
                std::string close_seq = nl + pad_for(lv.depth + 1) + "]";
                if (close_at == ed.tail_pos) {
                    ed.write_at_tail(close_seq);
                } else {
                    ed.splice_insert(close_at, close_seq);
                    long shift = (long)close_seq.size();
                    // Every not-yet-processed pending close whose offset
                    // was recorded *after* this insertion point must shift
                    // forward by however many bytes we just inserted.
                    for (auto& other : pending_closes) {
                        if (&other != &pc && other.first > close_at)
                            other.first += shift;
                    }
                }
            }
            ed.write_at_tail(nl);
            ed.write_at_tail(pad_for(depth));
            ed.write_at_tail('}');
        };

        bool ok = true;

        while (ok) {
            size_t nread = fread(chunk.data(), 1, io_buf_size, xin);
            if (nread == 0) break;

            for (size_t i = 0; i < nread; ++i) {
                int ret = yxml_parse(&x, (unsigned char)chunk[i]);
                if (ret < 0) {
                    snprintf(errbuf, errbuf_size,
                             "XML parse error (yxml code %d) at line %u", ret, x.line);
                    ok = false; break;
                }

                switch (ret) {
                case YXML_OK: break;

                case YXML_ELEMSTART: {
                    if (!levels.empty()) flush_text_field(levels.back());

                    size_t nlen = yxml_symlen(&x, x.elem);
                    std::string tag(x.elem, nlen);

                    if (levels.empty()) {
                        // This is the document root. Match dumps_file's
                        // convention of wrapping the whole document as
                        // {"<root_tag>": <root's own object>} rather than
                        // emitting the root's content directly as the
                        // top-level JSON value.
                        ed.write_at_tail('{');
                        if (!nl.empty()) ed.write_at_tail(nl + ind);
                        pgj_write_escaped(ed, tag);
                        ed.write_at_tail(':');
                        if (!nl.empty()) ed.write_at_tail(' ');
                    } else {
                        // Write this child's key prefix (and comma/'['
                        // patch, if it's a repeat) into its PARENT
                        // *before* any of this new level's own content
                        // gets written. This ordering is what keeps
                        // nested objects correct -- see open_child's
                        // comment for why.
                        open_child(levels.back(), tag);
                    }

                    PJLevel lv;
                    lv.tag = tag;
                    if (levels.empty()) {
                        lv.depth = 1;   // matches node_to_json(root, ..., depth=1)
                    } else {
                        PJLevel& parent = levels.back();
                        bool in_array = parent.children.count(tag) &&
                                         parent.children[tag].is_list;
                        // node_to_json recurses with depth+1 for a plain
                        // (non-array) child, and depth+2 for an array
                        // item (the array itself consumes one indent
                        // level for its brackets).
                        lv.depth = parent.depth + (in_array ? 2 : 1);
                    }
                    levels.push_back(lv);
                    elements_seen++;
                    break;
                }

                case YXML_ATTRSTART: {
                    size_t nlen = yxml_symlen(&x, x.attr);
                    cur_attr_key.assign(x.attr, nlen);
                    cur_attr_val.clear();
                    break;
                }
                case YXML_ATTRVAL:
                    cur_attr_val += x.data;
                    break;
                case YXML_ATTREND: {
                    PJLevel& lv = levels.back();
                    ensure_open(lv);
                    // xmltodict convention: a repeated attribute name (not
                    // valid per the XML spec, but tolerate malformed
                    // input) -- last value wins, no array wrapping.
                    field_sep(lv);
                    pgj_write_escaped(ed, attr_prefix + cur_attr_key);
                    ed.write_at_tail(':');
                    if (!nl.empty()) ed.write_at_tail(' ');
                    pgj_write_escaped(ed, cur_attr_val);
                    break;
                }

                case YXML_CONTENT:
                    cur_text += x.data;
                    have_pending_text = true;
                    break;

                case YXML_ELEMEND: {
                    PJLevel finished = levels.back();
                    levels.pop_back();

                    int depth = (int)levels.size();

                    if (levels.empty()) {
                        // document root -- close its own object, then
                        // close the outer wrapper opened at ELEMSTART.
                        close_level(finished, 1);
                        ed.write_at_tail(nl);
                        ed.write_at_tail('}');
                    } else {
                        PJLevel& parent = levels.back();
                        close_level(finished, depth + 1);
                        close_child(parent, finished.tag);
                    }
                    break;
                }

                case YXML_PISTART: case YXML_PICONTENT: case YXML_PIEND:
                    break;

                default: break;
                }
            }
            if (!ok) break;
        }

        if (ok) {
            int eof_ret = yxml_eof(&x);
            if (eof_ret < 0) {
                snprintf(errbuf, errbuf_size,
                         "unexpected end of XML (yxml code %d)", eof_ret);
                ok = false;
            }
        }

        fclose(xin);
        fclose(fout);

        if (!ok) return -2;
        return elements_seen;
    }
    """
    string xml_node_to_json(
        xml_node   root,
        const char* attr_prefix,
        const char* cdata_key,
        const char** force_list_items,
        bint        force_all,
        bint        pretty,
        const char* indent
    ) except +

    # direct overload with pre-built set — used by _do_jsonify
    string xml_node_to_json_set "xml_node_to_json_with_set"(
        xml_node    root,
        const char* attr_prefix,
        const char* cdata_key,
        object      force_set,
        bint        force_all,
        bint        pretty,
        const char* indent
    ) except +

    long long xml_stream_to_jsonl_file(
        const char* xml_path,
        const char* jsonl_path,
        const char* record_tag,
        const char* attr_prefix,
        const char* cdata_key,
        object      force_set,
        bint        force_all,
        size_t      stack_size,
        size_t      io_buf_size,
        char*       errbuf,
        size_t      errbuf_size
    ) except +

    long long xml_stream_to_json_file(
        const char* xml_path,
        const char* json_path,
        const char* attr_prefix,
        const char* cdata_key,
        object      force_set,
        bint        force_all,
        int         indent_width,
        size_t      stack_size,
        size_t      io_buf_size,
        char*       errbuf,
        size_t      errbuf_size
    ) except +


# ---------------------------------------------------------------------------
# Python-level helpers
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Public Cython entry points
# ---------------------------------------------------------------------------

cdef object _do_jsonify(xml_node root, str attr_prefix, str cdata_key,
                         object force_list, bint pretty, str indent,
                         str encoding, object doc_ref=None):
    """Call the C++ serializer and return a Python str.

    *doc_ref* keeps the owning XMLDocument alive for the duration of the
    C++ serialization call — pass it whenever root comes from an
    ObjectifiedElement or NamespacedElement.
    """
    cdef bytes ap_b      = attr_prefix.encode(encoding)
    cdef bytes ck_b      = cdata_key.encode(encoding)
    cdef bytes ind_b     = indent.encode(encoding)
    cdef bint  force_all = (force_list is True)
    cdef object fl_set   = None
    if force_list and not force_all:
        fl_set = set(force_list)
    cdef string result = xml_node_to_json_set(
        root, ap_b, ck_b, fl_set, force_all, pretty, ind_b,
    )
    return result.decode(encoding)


def jsonify_dumps_str(str xml,
                      str    attr_prefix = u"@",
                      str    cdata_key   = u"#text",
                      object force_list  = None,
                      bint   pretty      = False,
                      str    indent      = u"\t",
                      str    encoding    = u"utf-8"):
    """Serialize an XML *string* directly to JSON.

    Args:
        xml (str): XML source text.

    Returns:
        str: JSON string.

    Raises:
        PygiXMLError: If the XML is malformed.
    """
    cdef XMLDocument doc = XMLDocument()
    if not doc.load_string(xml):
        raise PygiXMLError("Failed to parse XML string")
    cdef xml_node root_raw = doc._doc.first_child()
    if _node_is_null(root_raw):
        raise PygiXMLError("Parsed document has no root element")
    return _do_jsonify(root_raw, attr_prefix, cdata_key, force_list, pretty, indent, encoding)


def jsonify_dumps_file(str path,
                       str    attr_prefix = u"@",
                       str    cdata_key   = u"#text",
                       object force_list  = None,
                       bint   pretty      = False,
                       str    indent      = u"\t",
                      str    encoding    = u"utf-8"):
    """Serialize an XML *file* directly to JSON.

    Args:
        path (str): Filesystem path to the XML file.

    Returns:
        str: JSON string.

    Raises:
        PygiXMLError: If the file cannot be read or XML is malformed.
    """
    cdef XMLDocument doc = XMLDocument()
    if not doc.load_file(path):
        raise PygiXMLError(f"Failed to parse XML file: {path}")
    cdef xml_node root_raw = doc._doc.first_child()
    if _node_is_null(root_raw):
        raise PygiXMLError(f"File {path!r} has no root element")
    return _do_jsonify(root_raw, attr_prefix, cdata_key, force_list, pretty, indent, encoding)


def jsonify_dumps_obj(object elem,
                      str    attr_prefix = u"@",
                      str    cdata_key   = u"#text",
                      object force_list  = None,
                      bint   pretty      = False,
                      str    indent      = u"\t",
                      str    encoding    = u"utf-8"):
    """Serialize an :class:`ObjectifiedElement` subtree directly to JSON.

    Args:
        elem (ObjectifiedElement): Element to serialise.

    Returns:
        str: JSON string.

    Raises:
        TypeError: If *elem* is not an ObjectifiedElement.
    """
    if not isinstance(elem, ObjectifiedElement):
        raise TypeError(
            f"expected ObjectifiedElement, got {type(elem).__name__!r}"
        )
    cdef xml_node node   = (<ObjectifiedElement>elem)._node
    cdef object   doc_ref = (<ObjectifiedElement>elem)._doc_ref
    return _do_jsonify(node, attr_prefix, cdata_key,
                       force_list, pretty, indent, encoding, doc_ref)


def jsonify_dumps_node(object node,
                       str    attr_prefix = u"@",
                       str    cdata_key   = u"#text",
                       object force_list  = None,
                       bint   pretty      = False,
                       str    indent      = u"\t",
                      str    encoding    = u"utf-8"):
    """Serialize a low-level :class:`XMLNode` directly to JSON.

    Args:
        node (XMLNode): Node to serialise.

    Returns:
        str: JSON string.

    Raises:
        TypeError: If *node* is not an XMLNode.
    """
    if not isinstance(node, XMLNode):
        raise TypeError(
            f"expected XMLNode, got {type(node).__name__!r}"
        )
    cdef xml_node raw = (<XMLNode>node)._node
    # Note: XMLNode does not hold a doc_ref — caller must keep XMLDocument alive
    return _do_jsonify(raw, attr_prefix, cdata_key, force_list, pretty, indent, encoding)


def jsonify_dumps(object source,
                  str    attr_prefix = u"@",
                  str    cdata_key   = u"#text",
                  object force_list  = None,
                  bint   pretty      = False,
                  str    indent      = u"\t",
                  str    encoding    = u"utf-8"):
    """Serialize XML to JSON — smart dispatcher.

    Routes automatically based on *source* type:

    * :class:`str` starting with ``<``  →  :func:`jsonify_dumps_str`
    * :class:`ObjectifiedElement`        →  :func:`jsonify_dumps_obj`
    * :class:`XMLNode`                   →  :func:`jsonify_dumps_node`

    .. note::
        File input is intentionally excluded from the dispatcher —
        use :func:`jsonify_dumps_file` explicitly for files.

    Args:
        source (str | ObjectifiedElement | XMLNode): Input XML.
        attr_prefix (str): Prefix for attribute keys. Default ``"@"``.
        cdata_key (str): Key for text content. Default ``"#text"``.
        force_list (set | True | None): Tags always serialised as array.
        pretty (bool): Indent output. Default ``False``.
        indent (str): Indentation string. Default ``"\\t"``.

    Returns:
        str: JSON string.

    Raises:
        PygiXMLError: If the XML is malformed.
        TypeError: If *source* type is not recognised.
        ValueError: If *source* is a str but does not look like XML.

    Example::

        from pygixml import jsonify, objectify

        jsonify.dumps("<root id=\'1\'><item>x</item></root>")
        jsonify.dumps(root.user_profile)   # ObjectifiedElement
        jsonify.dumps(doc.root)            # XMLNode
        jsonify.dumps_file("data.xml")     # file — explicit
    """
    if isinstance(source, ObjectifiedElement):
        return jsonify_dumps_obj(source, attr_prefix, cdata_key,
                                 force_list, pretty, indent, encoding)
    if isinstance(source, XMLNode):
        return jsonify_dumps_node(source, attr_prefix, cdata_key,
                                  force_list, pretty, indent, encoding)
    if isinstance(source, str):
        if (<str>source).lstrip().startswith("<"):
            return jsonify_dumps_str(source, attr_prefix, cdata_key,
                                     force_list, pretty, indent, encoding)
        raise ValueError(
            f"jsonify.dumps() received a str that does not start with '<'. "
            f"For files use jsonify.dumps_file() explicitly."
        )
    raise TypeError(
        f"jsonify.dumps() expects str, ObjectifiedElement, or XMLNode "
        f"— got {type(source).__name__!r}. "
        f"For files use jsonify.dumps_file() explicitly."
    )


def jsonify_stream_dump_jsonl(
    str xml_path,
    str jsonl_path,
    str record_tag=None,
    str attr_prefix="@",
    str cdata_key="#text",
    object force_list=None,
    size_t stack_size=4096,
    size_t io_buf_size=65536,
):
    """Convert a (potentially gigantic) XML file directly to JSON Lines.

    Constant memory, regardless of input file size or how many children
    any single element has. This calls straight into a C++ engine
    (:func:`xml_stream_to_jsonl_file`) that reads the XML file with
    :func:`fread`, writes JSON with :func:`fwrite`, and never builds a
    pugixml DOM, a Python ``dict``/``list``, or any in-memory subtree
    representation — not even temporarily. The Python ``json`` module is
    never imported or used; every byte of output is hand-emitted in C++.

    Output is **JSON Lines** (``.jsonl``): one self-contained JSON object
    per line — not a single big JSON array/document. This is what makes
    constant-memory operation possible — a JSON array needs to know
    whether more items follow before it can place its closing bracket
    correctly, which would force buffering; JSON Lines has no such
    requirement, since every line is independent.

    Parameters
    ----------
    xml_path : str
        Path to the input XML file.
    jsonl_path : str
        Path to the output **JSON Lines** file (conventionally named
        with a ``.jsonl`` extension). **Overwritten if it exists.**
    record_tag : str | None
        Tag name of the elements to emit as JSON Lines records — matched
        anywhere in the document regardless of nesting depth. When
        *None* (default), each **direct child of the document's root
        element** becomes one JSONL record instead.
    attr_prefix : str
        Prefix for XML attribute names in JSON keys. Default ``"@"``.
    cdata_key : str
        JSON key used for an element's text content when it is mixed
        with attributes or child elements. Default ``"#text"``.
    force_list : set[str] | True | None
        Tag names that should always be serialised as a JSON array, even
        when only one sibling exists for a given parent. Pass ``True``
        to force *every* repeated-or-not child tag into an array. When
        *None* (default), a tag becomes an array only when more than one
        sibling with that name actually appears under the same parent.
    stack_size : int
        Size in bytes of yxml's internal name stack — increase for very
        deeply nested XML or very long tag/attribute names.
        Default ``4096``.
    io_buf_size : int
        Bytes read/written per I/O operation. Default ``65536`` (64 KB).

    Returns
    -------
    int
        Number of JSON Lines records written.

    Raises
    ------
    PygiXMLError
        On malformed XML, or if the input/output file cannot be opened.

    Examples
    --------
    Convert every ``<record>`` element anywhere in a multi-gigabyte file::

        from pygixml import jsonify
        n = jsonify.stream_dump_jsonl("huge.xml", "huge.jsonl",
                                       record_tag="record")
        print(f"wrote {n} lines")

    No ``record_tag`` — each direct child of the root becomes one line::

        jsonify.stream_dump_jsonl("huge.xml", "huge.jsonl")

    Read the result back, one record at a time, still in constant memory
    (``json`` is fine to use on the *read* side — only this function's
    own internals avoid it)::

        import json
        with open("huge.jsonl") as f:
            for line in f:
                record = json.loads(line)
                ...
    """
    cdef bytes xml_b   = xml_path.encode("utf-8")
    cdef bytes jsonl_b = jsonl_path.encode("utf-8")
    cdef bytes rtag_b = record_tag.encode("utf-8") if record_tag else b""
    cdef bytes ap_b   = attr_prefix.encode("utf-8")
    cdef bytes ck_b   = cdata_key.encode("utf-8")

    cdef bint force_all = False
    cdef object force_set = None
    if force_list is True:
        force_all = True
    elif force_list:
        force_set = set(force_list)

    cdef char errbuf[512]
    errbuf[0] = 0

    cdef long long result = xml_stream_to_jsonl_file(
        <const char*>xml_b,
        <const char*>jsonl_b,
        <const char*>rtag_b,
        <const char*>ap_b,
        <const char*>ck_b,
        force_set,
        force_all,
        stack_size,
        io_buf_size,
        errbuf,
        sizeof(errbuf),
    )

    if result < 0:
        msg = errbuf.decode("utf-8", "replace") if errbuf[0] else "unknown error"
        raise PygiXMLError(f"jsonify_stream_dump_jsonl failed: {msg}")

    return result


def jsonify_stream_dump(
    str xml_path,
    str json_path,
    str attr_prefix="@",
    str cdata_key="#text",
    object force_list=None,
    int indent=0,
    size_t stack_size=4096,
    size_t io_buf_size=65536,
):
    """Convert a (potentially gigantic) XML file to a single, **standard,
    valid JSON document** — in roughly constant memory.

    Unlike :func:`stream_dump_jsonl` (which writes JSON *Lines* — one
    independent object per line, by design, to sidestep the
    "do I need an array bracket" problem), this function produces exactly
    what :func:`dumps`/:func:`dumps_file` would produce: one JSON value
    (an object, mirroring the XML root) that round-trips through a
    normal ``json.load`` like any other JSON file. No pugixml DOM, no
    Python ``dict``/``list``, and no ``json`` module are used internally
    — every byte is hand-emitted in C++, the same as
    :func:`stream_dump_jsonl`.

    How it stays (mostly) constant-memory while still producing valid
    JSON syntax: a normal JSON array must know, before its closing ``]``,
    whether more items follow. Instead of buffering whole subtrees to
    find out, this engine writes optimistically and *patches the file in
    place* once it learns more:

    * The first time a child tag is seen under some parent, a single
      placeholder byte is reserved right before its value and the tag is
      written as a plain (non-array) value.
    * If a second sibling with the same tag shows up, that one
      placeholder byte is overwritten with ``[`` (an O(1) patch), and the
      new value is appended right after the first — this is the common
      case when same-tag siblings are adjacent in the XML, and it never
      needs to move any bytes around.
    * If XML interleaves a different child in between two same-tag
      siblings, the engine "splices": it shifts just the bytes written
      in between forward (using a small fixed-size buffer, in chunks) to
      open a gap for the new sibling, then continues. This costs time
      proportional to how much was interleaved, not to the file size,
      and is the only case where any data movement happens at all.

    Because of that splice fallback, worst-case time can exceed
    :func:`stream_dump_jsonl`'s for documents where repeated sibling
    tags are heavily interleaved with unrelated children — for typical
    record-oriented XML (where ``<tag>`` repeats appear consecutively)
    this never triggers and the function runs at full streaming speed.

    Parameters
    ----------
    xml_path : str
        Path to the input XML file.
    json_path : str
        Path to the output JSON file. **Overwritten if it exists.**
    attr_prefix : str
        Prefix for XML attribute names in JSON keys. Default ``"@"``.
    cdata_key : str
        JSON key used for an element's text content when mixed with
        attributes or child elements. Default ``"#text"``.
    force_list : set[str] | True | None
        Tag names that should always be serialised as a JSON array, even
        when only one sibling exists for a given parent. Pass ``True``
        to force *every* child tag into an array. Default *None*
        (a tag becomes an array only when more than one sibling with
        that name actually appears under the same parent) — matching
        :func:`dumps`'s default behaviour.
    indent : int
        Number of spaces to indent nested structures with, following
        the same convention as Python's ``json.dump(..., indent=N)``.
        ``0`` (the default) produces compact output with no extra
        whitespace. Any positive value enables multi-line, indented
        output using that many spaces per nesting level.
    stack_size : int
        Size in bytes of yxml's internal name stack.
    io_buf_size : int
        Bytes read per XML I/O operation. Default ``65536`` (64 KB).

    Returns
    -------
    int
        Number of XML elements processed (informational).

    Raises
    ------
    PygiXMLError
        On malformed XML, or if the input/output file cannot be opened.

    Examples
    --------
    ::

        from pygixml import jsonify
        jsonify.jsonify_stream_dump("huge.xml", "huge.json")            # compact
        jsonify.jsonify_stream_dump("huge.xml", "huge.json", indent=2)  # pretty

        import json
        with open("huge.json") as f:
            data = json.load(f)   # a single, ordinary, valid JSON document
    """
    cdef bytes xml_b  = xml_path.encode("utf-8")
    cdef bytes json_b = json_path.encode("utf-8")
    cdef bytes ap_b   = attr_prefix.encode("utf-8")
    cdef bytes ck_b   = cdata_key.encode("utf-8")

    if indent < 0:
        raise ValueError(f"indent must be >= 0, got {indent}")

    cdef bint force_all = False
    cdef object force_set = None
    if force_list is True:
        force_all = True
    elif force_list:
        force_set = set(force_list)

    cdef char errbuf[512]
    errbuf[0] = 0

    cdef long long result = xml_stream_to_json_file(
        <const char*>xml_b,
        <const char*>json_b,
        <const char*>ap_b,
        <const char*>ck_b,
        force_set,
        force_all,
        <int>indent,
        stack_size,
        io_buf_size,
        errbuf,
        sizeof(errbuf),
    )

    if result < 0:
        msg = errbuf.decode("utf-8", "replace") if errbuf[0] else "unknown error"
        raise PygiXMLError(f"jsonify_stream_dump failed: {msg}")

    return result
