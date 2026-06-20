# dictify.pxi
# -------------
# Provides xmltodict-compatible parse/unparse for pygixml.
# All C types are already in scope from pygixml_cy.pyx.
#
# Usage:
#   from pygixml import dictify
#   d = dictify.parse(xml_string)
#   s = dictify.unparse(d)

# ---------------------------------------------------------------------------
# Internal: convert a single xml_node to a Python object (recursive)
# ---------------------------------------------------------------------------


cdef extern from *:
    """
    #include <string>
    #include <stdexcept>

    // ---------------------------------------------------------------------------
    // XML attribute value escaping
    // ---------------------------------------------------------------------------
    static void xml_escape_attr(const char* s, std::string& out) {
        for (; *s; ++s) {
            switch (*s) {
                case '"':    out += "&quot;"; break;
                case '\\'': out += "&apos;"; break;
                case '<':    out += "&lt;";   break;
                case '>':    out += "&gt;";   break;
                case '&':    out += "&amp;";  break;
                default:     out += *s;
            }
        }
    }

    // XML text content escaping
    static void xml_escape_text(const char* s, std::string& out) {
        for (; *s; ++s) {
            switch (*s) {
                case '<':  out += "&lt;";   break;
                case '>':  out += "&gt;";   break;
                case '&':  out += "&amp;";  break;
                default:   out += *s;
            }
        }
    }

    // ---------------------------------------------------------------------------
    // Core recursive dict→XML serializer
    // ---------------------------------------------------------------------------
    // Forward declaration
    static void dict_to_xml(
        PyObject*          tag_obj,
        PyObject*          value,
        std::string&       buf,
        const std::string& attr_prefix,
        const std::string& cdata_key,
        const std::string& indent,
        int                level,
        bool               pretty
    );

    static void append_indent(std::string& buf,
                               const std::string& indent, int level) {
        for (int i = 0; i < level; ++i) buf += indent;
    }

    static void emit_scalar(PyObject* tag_obj, PyObject* value,
                             std::string& buf,
                             const std::string& indent,
                             int level, bool pretty) {
        const char* tag = PyUnicode_AsUTF8(tag_obj);
        if (pretty) append_indent(buf, indent, level);
        buf += '<';
        buf += tag;
        buf += '>';
        if (value == Py_None) {
            // nothing
        } else {
            PyObject* s = PyObject_Str(value);
            xml_escape_text(PyUnicode_AsUTF8(s), buf);
            Py_DECREF(s);
        }
        buf += "</";
        buf += tag;
        buf += '>';
        if (pretty) buf += '\\n';
    }

    static void dict_to_xml(
        PyObject*          tag_obj,
        PyObject*          value,
        std::string&       buf,
        const std::string& attr_prefix,
        const std::string& cdata_key,
        const std::string& indent,
        int                level,
        bool               pretty
    ) {
        const char* tag = PyUnicode_AsUTF8(tag_obj);

        // --- None → self-closing ---
        if (value == Py_None) {
            if (pretty) append_indent(buf, indent, level);
            buf += '<'; buf += tag; buf += "/>";
            if (pretty) buf += '\\n';
            return;
        }

        // --- list → repeated siblings ---
        if (PyList_Check(value)) {
            Py_ssize_t n = PyList_GET_SIZE(value);
            for (Py_ssize_t i = 0; i < n; ++i)
                dict_to_xml(tag_obj, PyList_GET_ITEM(value, i),
                            buf, attr_prefix, cdata_key, indent, level, pretty);
            return;
        }

        // --- dict → element with attrs / children ---
        if (PyDict_Check(value)) {
            std::string attrs_str;
            const char* text_val = nullptr;
            std::string text_storage;

            // collect attrs and text
            PyObject *k, *v;
            Py_ssize_t pos = 0;
            while (PyDict_Next(value, &pos, &k, &v)) {
                const char* ks = PyUnicode_AsUTF8(k);
                // attribute key
                if (!attr_prefix.empty() &&
                    strncmp(ks, attr_prefix.c_str(), attr_prefix.size()) == 0) {
                    const char* attr_name = ks + attr_prefix.size();
                    attrs_str += ' ';
                    attrs_str += attr_name;
                    attrs_str += "=\\"";
                    PyObject* vs = PyObject_Str(v);
                    xml_escape_attr(PyUnicode_AsUTF8(vs), attrs_str);
                    Py_DECREF(vs);
                    attrs_str += '"';
                } else if (cdata_key == ks) {
                    PyObject* vs = PyObject_Str(v);
                    text_storage = PyUnicode_AsUTF8(vs);
                    Py_DECREF(vs);
                    text_val = text_storage.c_str();
                }
            }

            // check if any non-attr, non-cdata children exist
            bool has_children = false;
            pos = 0;
            while (PyDict_Next(value, &pos, &k, &v)) {
                const char* ks = PyUnicode_AsUTF8(k);
                if ((attr_prefix.empty() ||
                     strncmp(ks, attr_prefix.c_str(), attr_prefix.size()) != 0)
                    && cdata_key != ks) {
                    has_children = true;
                    break;
                }
            }

            if (pretty) append_indent(buf, indent, level);
            buf += '<'; buf += tag; buf += attrs_str;

            if (!has_children && text_val == nullptr) {
                buf += "/>";
                if (pretty) buf += '\\n';
                return;
            }

            buf += '>';

            if (!has_children) {
                // text only
                xml_escape_text(text_val, buf);
                buf += "</"; buf += tag; buf += '>';
                if (pretty) buf += '\\n';
                return;
            }

            if (pretty) buf += '\\n';

            // text before children
            if (text_val) {
                if (pretty) append_indent(buf, indent, level + 1);
                xml_escape_text(text_val, buf);
                if (pretty) buf += '\\n';
            }

            // child elements
            pos = 0;
            while (PyDict_Next(value, &pos, &k, &v)) {
                const char* ks = PyUnicode_AsUTF8(k);
                if ((attr_prefix.empty() ||
                     strncmp(ks, attr_prefix.c_str(), attr_prefix.size()) != 0)
                    && cdata_key != ks) {
                    dict_to_xml(k, v, buf, attr_prefix, cdata_key,
                                indent, level + 1, pretty);
                }
            }

            if (pretty) append_indent(buf, indent, level);
            buf += "</"; buf += tag; buf += '>';
            if (pretty) buf += '\\n';
            return;
        }

        // --- scalar (str, int, float, bool) ---
        emit_scalar(tag_obj, value, buf, indent, level, pretty);
    }

    static std::string dict_unparse_cpp(
        PyObject*   input_dict,
        const char* encoding,
        bool        full_document,
        const char* indent,
        const char* attr_prefix,
        const char* cdata_key,
        bool        pretty
    ) {
        if (!PyDict_Check(input_dict) || PyDict_Size(input_dict) != 1)
            throw std::invalid_argument(
                "unparse expects a dict with exactly one root key");

        std::string buf;
        buf.reserve(4096);

        if (full_document) {
            buf += "<?xml version=\\"1.0\\" encoding=\\"";
            buf += encoding;
            buf += "\\"?>";
            if (pretty) buf += '\\n';
        }

        std::string ap(attr_prefix);
        std::string ck(cdata_key);
        std::string ind(indent);

        PyObject *root_tag, *root_val;
        Py_ssize_t pos = 0;
        PyDict_Next(input_dict, &pos, &root_tag, &root_val);

        dict_to_xml(root_tag, root_val, buf, ap, ck, ind, 0, pretty);

        return buf;
    }
    """
    string dict_unparse_cpp(
        object   input_dict,
        const char* encoding,
        bint        full_document,
        const char* indent,
        const char* attr_prefix,
        const char* cdata_key,
        bint        pretty
    ) except +

cdef object _node_to_obj(xml_node node,
                          str attr_prefix,
                          str cdata_key,
                          object force_list):
    """Recursively convert *node* to a dict / string / None.

    Rules (matching xmltodict behaviour):
      - Empty node (no attrs, no children, no text)  → None
      - Text-only node, no attrs                      → str (the text)
      - Whitespace-only text, no attrs, no children   → None
      - Mixed (attrs and/or children)                 → dict
        - Attributes stored as  attr_prefix + name
        - Repeated sibling tags collapsed into list
        - Text content stored under cdata_key
    """
    cdef xml_attribute attr_c
    cdef xml_node      child
    cdef string        s
    cdef bint          has_attrs    = False
    cdef bint          has_children = False
    cdef str           text         = None

    # --- collect attributes ---
    cdef dict result = {}
    attr_c = node.first_attribute()
    while not _attr_is_null(attr_c):
        has_attrs = True
        s = attr_c.name()
        k = attr_prefix + s.decode("utf-8")
        s = attr_c.value()
        result[k] = s.decode("utf-8")
        attr_c = attr_c.next_attribute()

    # --- collect text / CDATA ---
    s = node.child_value()
    if not s.empty():
        raw = s.decode("utf-8")
        stripped = raw.strip()
        if stripped:
            text = raw   # preserve original (xmltodict does not strip)

    # --- collect child elements ---
    child = node.first_child()
    while not _node_is_null(child):
        if child.type() == node_element:
            has_children = True
            s = child.name()
            tag = s.decode("utf-8")
            val = _node_to_obj(child, attr_prefix, cdata_key, force_list)

            if tag in result:
                # already seen — ensure it's a list
                if not isinstance(result[tag], list):
                    result[tag] = [result[tag]]
                result[tag].append(val)
            else:
                result[tag] = val
        child = child.next_sibling()

    # --- force_list: wrap scalar values into list ---
    if force_list:
        for tag in list(result.keys()):
            if not tag.startswith(attr_prefix) and tag != cdata_key:
                if force_list is True or tag in force_list:
                    if not isinstance(result[tag], list):
                        result[tag] = [result[tag]]

    # --- decide final shape ---
    if not has_attrs and not has_children:
        # leaf node
        if text is None:
            return None
        return text

    # mixed: attrs and/or children present
    if text is not None:
        result[cdata_key] = text

    return result if result else None


# ---------------------------------------------------------------------------
# parse
# ---------------------------------------------------------------------------

def dictify_parse(str xml,
                    str attr_prefix=u"@",
                    str cdata_key=u"#text",
                    object force_list=None,
                    object encoding=None):
    """Parse an XML string into an OrderedDict-compatible dict.

    Matches the behaviour of the ``xmltodict`` library:

    * Attributes are stored with *attr_prefix* prepended (default ``"@"``).
    * Text content of mixed nodes is stored under *cdata_key*
      (default ``"#text"``).
    * Repeated sibling elements are automatically collapsed into a list.
    * Empty elements become ``None``.
    * Whitespace-only text nodes become ``None``.

    Args:
        xml (str): XML source text.
        attr_prefix (str): Prefix for attribute keys. Default ``"@"``.
        cdata_key (str): Key for text content in mixed nodes.
            Default ``"#text"``.
        force_list (set | True | None): Tag names that should always be
            wrapped in a list even when only one element is present.
            Pass ``True`` to force all tags into lists.
        encoding: Accepted for API compatibility; pygixml auto-detects
            encoding and this parameter is ignored.

    Returns:
        dict: Parsed document as a nested dict.

    Raises:
        PygiXMLError: If the XML is malformed.

    Example::

        from pygixml import dictify
        d = dictify.parse('<root id="1"><item>a</item><item>b</item></root>')
        # {'root': {'@id': '1', 'item': ['a', 'b']}}
    """
    cdef XMLDocument doc = XMLDocument()
    if not doc.load_string(xml):
        raise PygiXMLError("Failed to parse XML string")
    cdef xml_node root_raw = doc._doc.first_child()
    if _node_is_null(root_raw):
        raise PygiXMLError("Parsed document has no root element")

    cdef string root_name = root_raw.name()
    tag = root_name.decode("utf-8")
    val = _node_to_obj(root_raw, attr_prefix, cdata_key, force_list)
    return {tag: val}


def dictify_parse_file(str path,
                         str attr_prefix=u"@",
                         str cdata_key=u"#text",
                         object force_list=None):
    """Parse an XML file into a dict. Same semantics as :func:`dictify_parse`.

    Args:
        path (str): Path to the XML file.
        attr_prefix (str): Prefix for attribute keys. Default ``"@"``.
        cdata_key (str): Key for text content in mixed nodes.
        force_list (set | True | None): Tags to always wrap in a list.

    Returns:
        dict: Parsed document as a nested dict.

    Raises:
        PygiXMLError: If the file cannot be read or XML is malformed.
    """
    cdef XMLDocument doc = XMLDocument()
    if not doc.load_file(path):
        raise PygiXMLError(f"Failed to parse XML file: {path}")
    cdef xml_node root_raw = doc._doc.first_child()
    if _node_is_null(root_raw):
        raise PygiXMLError(f"File {path!r} has no root element")

    cdef string root_name = root_raw.name()
    tag = root_name.decode("utf-8")
    val = _node_to_obj(root_raw, attr_prefix, cdata_key, force_list)
    return {tag: val}


# ---------------------------------------------------------------------------
# unparse
# ---------------------------------------------------------------------------


def dictify_unparse(object input_dict,
                    str output=None,
                    str encoding=u"utf-8",
                    str full_document=u"true",
                    str indent=u"\t",
                    str attr_prefix=u"@",
                    str cdata_key=u"#text",
                    bint pretty=False):
    """Emit an XML string from a dict produced by :func:`dictify_parse`.

    Implemented entirely in C++ — no Python list, string concatenation, or
    f-string formatting during serialization.  Only one Python ``str`` is
    created at the very end.

    Matches the ``xmltodict.unparse`` signature.

    Args:
        input_dict (dict): A ``{root_tag: value}`` dict.
        output: Ignored (accepted for API compatibility).
        encoding (str): Encoding declared in the XML header. Default ``"utf-8"``.
        full_document (str): ``"true"`` to include the XML declaration.
        indent (str): Indentation string when *pretty* is ``True``.
            Default ``"\\t"``.
        attr_prefix (str): Prefix that identifies attribute keys. Default ``"@"``.
        cdata_key (str): Key for text content in mixed nodes. Default ``"#text"``.
        pretty (bool): Whether to indent output. Default ``False``.

    Returns:
        str: XML string.

    Raises:
        ValueError: If *input_dict* does not have exactly one root key.

    Example::

        from pygixml import dictify
        d = {'root': {'@id': '1', 'item': ['a', 'b']}}
        print(dictify.unparse(d, pretty=True))
    """
    if not isinstance(input_dict, dict) or len(input_dict) != 1:
        raise ValueError("unparse expects a dict with exactly one root key")

    cdef bytes enc_b = encoding.encode("utf-8")
    cdef bytes ind_b = indent.encode("utf-8") if pretty else b""
    cdef bytes ap_b  = attr_prefix.encode("utf-8")
    cdef bytes ck_b  = cdata_key.encode("utf-8")
    cdef bint  full  = (full_document == "true")

    cdef string result = dict_unparse_cpp(
        input_dict,
        enc_b,
        full,
        ind_b,
        ap_b,
        ck_b,
        pretty,
    )
    return result.decode("utf-8")


def dictify_iterdict(source, str tag, str attr_prefix="@", str cdata_key="#text",
             object force_list=None, size_t stack_size=4096,
             Py_ssize_t chunk_size=65536):
    """Stream-parse XML and yield each matching element as a plain
    ``dict``, one at a time.

    Identical to :func:`iterjsonl` except it yields
    :meth:`StreamElement.to_dict` results instead of JSON strings --
    useful when you want to keep working with the data in Python rather
    than as text.

    Example::

        for record in dictify.iterdict("big.xml", "record"):
            print(record["name"], record["@id"])
    """
    for elem in iterfind(source, tag, stack_size=stack_size, chunk_size=chunk_size):
        yield (<StreamElement>elem).to_dict(attr_prefix, cdata_key, force_list)
        elem.clear()
