# dictify.pxi
# -------------
# Include at the END of pygixml_cy.pyx (after objectify.pxi include):
#     include "objectify.pxi"
#     include "dictify.pxi"
#
# Provides xmltodict-compatible parse/unparse for pygixml.
# All C types are already in scope from pygixml_cy.pyx.
#
# Usage:
#   from pygixml import dictify
#   d = xmltodict.parse(xml_string)
#   s = xmltodict.unparse(d)

# ---------------------------------------------------------------------------
# Internal: convert a single xml_node to a Python object (recursive)
# ---------------------------------------------------------------------------

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
        d = xmltodict.parse('<root id="1"><item>a</item><item>b</item></root>')
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

def _dict_to_xml(str tag, object value, list lines,
                 str attr_prefix, str cdata_key,
                 str indent, int level):
    """Recursive helper that appends XML lines for one tag/value pair."""
    cdef str pad = indent * level

    if value is None:
        lines.append(f"{pad}<{tag}/>")
        return

    if isinstance(value, list):
        for item in value:
            _dict_to_xml(tag, item, lines, attr_prefix, cdata_key,
                         indent, level)
        return

    if isinstance(value, dict):
        # split keys into attrs, text, children
        attrs     = {}
        text      = None
        children  = {}
        for k, v in value.items():
            if k.startswith(attr_prefix) and attr_prefix:
                attrs[k[len(attr_prefix):]] = v
            elif k == cdata_key:
                text = v
            else:
                children[k] = v

        attr_str = "".join(f' {k}="{v}"' for k, v in attrs.items())
        open_tag = f"{pad}<{tag}{attr_str}>"

        if not children and text is None:
            lines.append(f"{pad}<{tag}{attr_str}/>")
            return

        if not children:
            lines.append(f"{open_tag}{text}</{tag}>")
            return

        lines.append(open_tag)
        if text is not None:
            lines.append(f"{indent * (level + 1)}{text}")
        for child_tag, child_val in children.items():
            _dict_to_xml(child_tag, child_val, lines,
                         attr_prefix, cdata_key, indent, level + 1)
        lines.append(f"{pad}</{tag}>")
        return

    # scalar (str, int, float, bool, …)
    lines.append(f"{pad}<{tag}>{value}</{tag}>")


def dictify_unparse(object input_dict,
                      str output=None,
                      str encoding=u"utf-8",
                      str full_document=u"true",
                      str indent=u"\t",
                      str attr_prefix=u"@",
                      str cdata_key=u"#text",
                      bint pretty=False):
    """Emit an XML string from a dict produced by :func:`dictify_parse`.

    Matches the ``xmltodict.unparse`` signature.

    Args:
        input_dict (dict): A ``{root_tag: value}`` dict.
        output: Ignored (accepted for API compatibility).
        encoding (str): Encoding declared in the XML header. Default ``"utf-8"``.
        full_document (str): ``"true"`` to include the XML declaration.
        indent (str): Indentation string used when *pretty* is ``True``.
            Default ``"\\t"``.
        attr_prefix (str): Prefix that identifies attribute keys. Default ``"@"``.
        cdata_key (str): Key holding text content. Default ``"#text"``.
        pretty (bool): Whether to indent output. Default ``False``.

    Returns:
        str: XML string.

    Raises:
        ValueError: If *input_dict* does not have exactly one root key.

    Example::

        from pygixml import dictify
        d = {'root': {'@id': '1', 'item': ['a', 'b']}}
        print(xmltodict.unparse(d, pretty=True))
    """
    if not isinstance(input_dict, dict) or len(input_dict) != 1:
        raise ValueError("unparse expects a dict with exactly one root key")

    root_tag = next(iter(input_dict))
    root_val = input_dict[root_tag]

    lines = []
    if full_document == "true":
        lines.append(f'<?xml version="1.0" encoding="{encoding}"?>')

    _indent = indent if pretty else ""
    _dict_to_xml(root_tag, root_val, lines, attr_prefix, cdata_key, _indent, 0)

    sep = "\n" if pretty else ""
    return sep.join(lines)
