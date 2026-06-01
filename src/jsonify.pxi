# jsonify.pxi
# -----------
# Include after objectify.pxi and namespace.pxi in pygixml_cy.pyx:
#     include "objectify.pxi"
#     include "namespace.pxi"
#     include "jsonify.pxi"
#
# Converts an xml_node tree directly to a JSON string via a C++ string
# buffer — no Python dict/list/str is allocated during traversal.
# Only one Python str object is created at the very end.
#
# Public API:
#   jsonify_dumps(xml,  attr_prefix, cdata_key, force_list, pretty, indent)
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


# ---------------------------------------------------------------------------
# Public Cython entry points
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Internal typed helpers (cdef — not callable from Python directly)
# ---------------------------------------------------------------------------

cdef object _dumps_from_str(str xml, str attr_prefix, str cdata_key,
                              object force_list, bint pretty, str indent, str encoding):
    cdef XMLDocument doc = XMLDocument()
    if not doc.load_string(xml):
        raise PygiXMLError("Failed to parse XML string")
    cdef xml_node root_raw = doc._doc.first_child()
    if _node_is_null(root_raw):
        raise PygiXMLError("Parsed document has no root element")
    return _do_jsonify(root_raw, attr_prefix, cdata_key, force_list, pretty, indent, encoding)


cdef object _dumps_from_file(str path, str attr_prefix, str cdata_key,
                               object force_list, bint pretty, str indent, str encoding):
    cdef XMLDocument doc = XMLDocument()
    if not doc.load_file(path):
        raise PygiXMLError(f"Failed to parse XML file: {path}")
    cdef xml_node root_raw = doc._doc.first_child()
    if _node_is_null(root_raw):
        raise PygiXMLError(f"File {path!r} has no root element")
    return _do_jsonify(root_raw, attr_prefix, cdata_key, force_list, pretty, indent, encoding)


cdef object _dumps_from_node(object elem, str attr_prefix, str cdata_key,
                               object force_list, bint pretty, str indent, str encoding):
    if not isinstance(elem, ObjectifiedElement):
        raise TypeError(
            f"expected ObjectifiedElement, got {type(elem).__name__!r}"
        )
    cdef xml_node node = (<ObjectifiedElement>elem)._node
    return _do_jsonify(node, attr_prefix, cdata_key, force_list, pretty, indent, encoding)


# ---------------------------------------------------------------------------
# Public entry point — smart dispatcher
# ---------------------------------------------------------------------------

def jsonify_dumps(object source,
                  str    attr_prefix = u"@",
                  str    cdata_key   = u"#text",
                  object force_list  = None,
                  bint   pretty      = False,
                  str    indent      = u"\t", 
                  str    encoding    = u"utf-8"):
    """Serialize XML to a JSON string — directly in C++, no intermediate dict.

    Accepts three input types and routes automatically:

    * **str** — XML source text (parsed on the fly).
    * **ObjectifiedElement** — already-parsed node or subtree.
    * **os.PathLike / path string ending in** ``".xml"`` — read from file.

    Follows the same conventions as :func:`pygixml.dictify.parse`:

    * Attributes prefixed with *attr_prefix* (default ``"@"``).
    * Text content in mixed nodes stored under *cdata_key* (``"#text"``).
    * Repeated siblings collapsed into a JSON array automatically.
    * Empty / whitespace-only elements become JSON ``null``.

    Args:
        source (str | ObjectifiedElement | PathLike): Input XML.
        attr_prefix (str): Prefix for attribute keys. Default ``"@"``.
        cdata_key (str): Key for text content. Default ``"#text"``.
        force_list (set | True | None): Tags always serialised as a JSON
            array. Pass ``True`` to force all tags.
        pretty (bool): Indent output. Default ``False``.
        indent (str): Indentation string. Default ``"\\t"``.

    Returns:
        str: JSON string.

    Raises:
        PygiXMLError: If the XML is malformed or unreadable.
        TypeError: If *source* is not a recognised input type.

    Example::

        from pygixml import jsonify

        # from XML string
        jsonify.dumps("<root id=\'1\'><item>x</item></root>")

        # from file
        jsonify.dumps("data.xml")

        # from ObjectifiedElement (subtree)
        root = objectify.from_string(xml)
        jsonify.dumps(root.user_profile)
        jsonify.dumps(root.user_profile, pretty=True, indent="  ")
    """
    # --- ObjectifiedElement (or NamespacedElement) ---
    if isinstance(source, ObjectifiedElement):
        return _dumps_from_node(source, attr_prefix, cdata_key,
                                force_list, pretty, indent, encoding)

    # --- str: could be XML content or a file path ---
    if isinstance(source, str):
        s = <str>source
        # heuristic: if it starts with '<' it's XML content
        stripped = s.lstrip()
        if stripped.startswith("<"):
            return _dumps_from_str(s, attr_prefix, cdata_key,
                                   force_list, pretty, indent, encoding)
        # otherwise treat as file path
        return _dumps_from_file(s, attr_prefix, cdata_key,
                                force_list, pretty, indent, encoding)

    # --- PathLike (pathlib.Path, os.fspath, etc.) ---
    import os as _os
    if isinstance(source, _os.PathLike):
        return _dumps_from_file(str(source), attr_prefix, cdata_key,
                                force_list, pretty, indent, encoding)

    raise TypeError(
        f"jsonify.dumps() expects an XML string, a file path, or an "
        f"ObjectifiedElement — got {type(source).__name__!r}"
    )


# ---------------------------------------------------------------------------
# Internal dispatcher
# ---------------------------------------------------------------------------

cdef object _do_jsonify(xml_node root, str attr_prefix, str cdata_key,
                         object force_list, bint pretty, str indent, str encoding):
    """Call the C++ serializer and return a Python str.

    force_list is handled entirely in C++ — no Python json.loads/dumps
    fallback. The Python set is passed directly to C++ which iterates
    it via the CPython API.
    """
    cdef bytes ap_b      = attr_prefix.encode(encoding)
    cdef bytes ck_b      = cdata_key.encode(encoding)
    cdef bytes ind_b     = indent.encode(encoding)
    cdef bint  force_all = (force_list is True)

    # Normalise force_list to a Python set of str (or None)
    cdef object fl_set = None
    if force_list and not force_all:
        fl_set = set(force_list)   # ensure it's a set

    cdef string result = xml_node_to_json_set(
        root,
        ap_b,
        ck_b,
        fl_set,      # Python set passed directly — C++ reads via PySet_*
        force_all,
        pretty,
        ind_b,
    )

    return result.decode(encoding)