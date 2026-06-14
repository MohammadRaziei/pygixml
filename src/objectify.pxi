# objectify.pxi
# -------------
# Include at the END of pygixml_cy.pyx:
#     include "objectify.pxi"
#
# All C types are already in scope from pygixml_cy.pyx.
# Namespace support (NamespacedElement) is included in this file.
#
# objectify.py re-exports:
#   from .pygixml_cy import (ObjectifiedElement, NodeSequence,
#       NamespacedElement, objectify_from_string, objectify_from_file)

#       objectify_from_file   as from_file)

# ---------------------------------------------------------------------------
# Encoding support — maps Python strings to pugixml xml_encoding enum
# ---------------------------------------------------------------------------

cdef extern from "pugixml.hpp" namespace "pugi":
    cdef enum xml_encoding:
        encoding_auto
        encoding_utf8
        encoding_utf16_le
        encoding_utf16_be
        encoding_utf16
        encoding_utf32_le
        encoding_utf32_be
        encoding_utf32
        encoding_wchar
        encoding_latin1

    cdef cppclass xml_parse_result:
        pass

cdef extern from *:
    """
    static bool pygixml_parse_ok(const pugi::xml_parse_result& r) {
        return static_cast<bool>(r);
    }
    static bool pygixml_load_buffer(pugi::xml_document* doc,
                                     const void* data, size_t size,
                                     unsigned int opts,
                                     pugi::xml_encoding enc) {
        return static_cast<bool>(doc->load_buffer(data, size, opts, enc));
    }
    static bool pygixml_load_file(pugi::xml_document* doc,
                                   const char* path,
                                   unsigned int opts,
                                   pugi::xml_encoding enc) {
        return static_cast<bool>(doc->load_file(path, opts, enc));
    }
    """
    bint pygixml_parse_ok(xml_parse_result r)
    bint pygixml_load_buffer "pygixml_load_buffer"(
        xml_document* doc,
        const void*   data,
        size_t        size,
        unsigned int  opts,
        xml_encoding  enc)
    bint pygixml_load_file "pygixml_load_file"(
        xml_document* doc,
        const char*   path,
        unsigned int  opts,
        xml_encoding  enc)


cdef xml_encoding _str_to_encoding(str enc):
    """Map a Python encoding string to pugixml xml_encoding enum value."""
    cdef str e = enc.lower().replace("-", "").replace("_", "")
    if e in ("utf8", "utf"):
        return encoding_utf8
    if e == "utf16le":
        return encoding_utf16_le
    if e == "utf16be":
        return encoding_utf16_be
    if e == "utf16":
        return encoding_utf16
    if e == "utf32le":
        return encoding_utf32_le
    if e == "utf32be":
        return encoding_utf32_be
    if e == "utf32":
        return encoding_utf32
    if e in ("latin1", "latin", "iso88591", "iso8859"):
        return encoding_latin1
    if e == "wchar":
        return encoding_wchar
    # default — auto-detect from BOM / XML declaration
    return encoding_auto


# ---------------------------------------------------------------------------
# Null-check helpers
# ---------------------------------------------------------------------------

cdef inline bint _node_is_null(xml_node n):
    return n.type() == node_null

cdef inline bint _attr_is_null(xml_attribute a):
    cdef string name = a.name()   # const char* → std::string first
    return name.empty()

cdef inline bint _is_xmlns_attr(xml_attribute a):
    """True for ``xmlns`` / ``xmlns:*`` namespace declaration attributes."""
    cdef string name = a.name()
    return name == <string>b"xmlns" or name.substr(0, 6) == <string>b"xmlns:"

# ---------------------------------------------------------------------------
# Namespace map builder
# ---------------------------------------------------------------------------

cdef dict _build_nsmap(xml_node node):
    """Collect all xmlns:prefix="uri" attributes on *node* into a dict.

    Returns a dict mapping prefix → uri  (e.g. {"ns": "http://ns.com"}).
    The default namespace (xmlns="...") is stored under the empty string key.
    Also builds the reverse map uri → prefix for {uri}local lookup.
    Both maps are merged into one dict:
        "ns"               → "http://ns.com"   (prefix → uri)
        "http://ns.com"    → "ns"              (uri    → prefix)
    """
    cdef xml_attribute a = node.first_attribute()
    cdef string        aname
    cdef dict          nsmap = {}

    while not _attr_is_null(a):
        aname = a.name()
        py_name = aname.decode("utf-8")
        py_val  = a.value().decode("utf-8")
        if py_name == "xmlns":
            nsmap[""]       = py_val   # default namespace
            nsmap[py_val]   = ""
        elif py_name.startswith("xmlns:"):
            prefix = py_name[6:]
            nsmap[prefix]   = py_val   # prefix → uri
            nsmap[py_val]   = prefix   # uri    → prefix
        a = a.next_attribute()

    return nsmap


cdef dict _inherit_nsmap(dict parent_nsmap, xml_node node):
    """Return an nsmap for *node* that inherits from *parent_nsmap*."""
    cdef dict local = _build_nsmap(node)
    if not local:
        return parent_nsmap
    if not parent_nsmap:
        return local
    cdef dict merged = dict(parent_nsmap)
    merged.update(local)
    return merged

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

cdef object _infer_type(str raw):
    """Convert a string to the most specific Python scalar.

    Priority: bool > int > float > str
    """
    if raw is None:
        return None
    cdef str s  = raw.strip()
    cdef str lo = s.lower()
    if lo == "true":
        return True
    if lo == "false":
        return False
    if "." not in s and "e" not in lo:
        try:
            return int(s)
        except ValueError:
            pass
    try:
        return float(s)
    except ValueError:
        pass
    return raw


cdef list _obj_candidate_names(str py_name, dict nsmap):
    """Return all XML tag/attribute name candidates for a Python identifier.

    Handles three mappings in order:
      1. Exact name              "foo_bar"  → "foo_bar"
      2. Underscore → hyphen     "foo_bar"  → "foo-bar"
      3. Underscore → colon      "ns_tag"   → "ns:tag"   (if "ns" in nsmap)
      4. {uri}local via nsmap    "ns_tag"   → "{http://...}tag" resolved back
                                              to "ns:tag" for pugixml lookup
    """
    cdef list candidates = []
    cdef str  hyphen     = py_name.replace("_", "-")
    cdef str  colon      = py_name.replace("_", ":", 1)  # only first underscore

    # 1. exact
    candidates.append(py_name)

    # 2. hyphen fallback
    if hyphen != py_name:
        candidates.append(hyphen)

    # 3. colon / namespace fallback
    if nsmap and "_" in py_name:
        colon = py_name.replace("_", ":", 1)
        parts = colon.split(":", 1)
        if len(parts) == 2 and parts[0] in nsmap:
            # e.g. "ns_item" → "ns:item"  (pugixml stores it literally)
            if colon not in candidates:
                candidates.append(colon)

    return candidates


cdef list _resolve_tag(str tag, dict nsmap):
    """Resolve a user-supplied tag to a list of pugixml-level name candidates.

    Accepted formats:
      "item"               → ["item"]
      "ns:item"            → ["ns:item"]
      "{http://ns.com}item"→ ["ns:item"]   (looked up via uri→prefix map)
      "ns_item"            → ["ns_item", "ns-item", "ns:item"]
    """
    if tag.startswith("{"):
        # Clark notation: {uri}local
        end = tag.index("}")
        uri   = tag[1:end]
        local = tag[end + 1:]
        if nsmap and uri in nsmap:
            prefix = nsmap[uri]
            if prefix:
                return [f"{prefix}:{local}"]
            else:
                return [local]          # default namespace — no prefix in pugixml
        return [local]                  # uri not in map — fall back to local name
    # Not Clark notation — use normal candidate expansion
    return _obj_candidate_names(tag, nsmap)


cdef list _obj_collect_siblings(xml_node parent, bytes tag_b, object doc_ref,
                                 dict nsmap):
    """Return ObjectifiedElements for every direct child of parent named tag_b."""
    cdef xml_node child     = parent.first_child()
    cdef list     result    = []
    cdef string   tag_s     = tag_b
    cdef string   child_name
    while not _node_is_null(child):
        if child.type() == node_element:
            child_name = child.name()
            if child_name == tag_s:
                child_nsmap = _inherit_nsmap(nsmap, child)
                result.append(ObjectifiedElement._from_raw(child, doc_ref,
                                                           child_nsmap))
        child = child.next_sibling()
    return result


cdef xml_node _find_first(xml_node parent, list tag_bytes, bint recursive):
    """Return the first descendant of parent whose name is in tag_bytes."""
    cdef xml_node child = parent.first_child()
    cdef xml_node found
    cdef string   child_name

    while not _node_is_null(child):
        if child.type() == node_element:
            child_name = child.name()
            for tb in tag_bytes:
                if child_name == <string>(<bytes>tb):
                    return child
        child = child.next_sibling()

    if not recursive:
        return xml_node()

    child = parent.first_child()
    while not _node_is_null(child):
        if child.type() == node_element:
            found = _find_first(child, tag_bytes, True)
            if not _node_is_null(found):
                return found
        child = child.next_sibling()

    return xml_node()


cdef void _find_all(xml_node parent, list tag_bytes, bint recursive,
                    list result, object doc_ref, dict nsmap):
    """Append every descendant of parent whose name is in tag_bytes to result."""
    cdef xml_node child = parent.first_child()
    cdef string   child_name

    while not _node_is_null(child):
        if child.type() == node_element:
            child_name = child.name()
            for tb in tag_bytes:
                if child_name == <string>(<bytes>tb):
                    child_nsmap = _inherit_nsmap(nsmap, child)
                    result.append(ObjectifiedElement._from_raw(child, doc_ref,
                                                               child_nsmap))
                    break
            if recursive:
                _find_all(child, tag_bytes, True, result, doc_ref, nsmap)
        child = child.next_sibling()


_OBJ_RESERVED = frozenset({"_node", "_doc_ref", "_nsmap"})


# ---------------------------------------------------------------------------
# NodeSequence
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# AttributeValue — lazy wrapper around a single xml_attribute
# ---------------------------------------------------------------------------

cdef class AttributeValue:
    """Lazy wrapper around a single XML attribute.

    Holds the C-level ``xml_attribute`` struct directly — no string copy
    or type conversion is performed until explicitly requested.

    Access patterns
    ---------------
    * ``str(av)``      — raw value as ``str`` (cheap: one UTF-8 decode)
    * ``av()``         — type-inferred value (bool > int > float > str)
    * ``av.str()``     — explicit ``str``
    * ``av.int()``     — explicit ``int``
    * ``av.float()``   — explicit ``float``
    * ``av.bool()``    — explicit ``bool``
    * ``av.name``      — attribute name as ``str``
    * ``av.raw``       — raw bytes (no decode — zero-cost)

    All conversion methods accept an optional *encoding* parameter
    (default ``"utf-8"``).
    """

    cdef xml_attribute _attr
    cdef object        _doc_ref   # keeps XMLDocument alive

    @staticmethod
    cdef AttributeValue _from_raw(xml_attribute attr, object doc_ref):
        cdef AttributeValue obj = AttributeValue.__new__(AttributeValue)
        obj._attr    = attr
        obj._doc_ref = doc_ref
        return obj

    # ------------------------------------------------------------------
    # Core value access
    # ------------------------------------------------------------------

    def __str__(self):
        """Raw attribute value as a plain ``str``."""
        cdef string v = self._attr.value()
        return v.decode("utf-8")

    def __repr__(self):
        cdef string n = self._attr.name()
        cdef string v = self._attr.value()
        return f"AttributeValue({n.decode('utf-8')!r}={v.decode('utf-8')!r})"

    def __call__(self):
        """Type-inferred value: bool > int > float > str."""
        cdef string v = self._attr.value()
        return _infer_type(v.decode("utf-8"))

    def __bool__(self):
        cdef string n = self._attr.name()
        return not n.empty()

    def __eq__(self, other):
        cdef string v1, v2
        if isinstance(other, AttributeValue):
            v1 = self._attr.value()
            v2 = (<AttributeValue>other)._attr.value()
            return v1 == v2
        return self() == other

    def str(self):
        """Return the attribute value as a ``str``.

        Equivalent to ``str(av)``.  Provided for explicit, readable code.
        """
        cdef string v = self._attr.value()
        return v.decode("utf-8")

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def name(self):
        """Attribute name as a ``str``."""
        cdef string n = self._attr.name()
        return n.decode("utf-8")

    @property
    def raw(self):
        """Raw attribute value as ``bytes`` — zero-cost, no decode."""
        cdef string v = self._attr.value()
        return bytes(v)


# ---------------------------------------------------------------------------
# AttributeMap — dict-like view of all attributes on a node
# ---------------------------------------------------------------------------

cdef class AttributeMap:
    """Dict-like view of all XML attributes on a node.

    Provides attribute access via dotted notation, indexing, iteration,
    and safe ``get()``.  Each access returns a lazy :class:`AttributeValue`
    — no string conversion until you ask for it.

    Access patterns
    ---------------
    * ``am.id``              — ``AttributeValue`` for attribute ``id``
    * ``am["id"]``           — same via ``__getitem__``
    * ``am.get("id")``       — ``AttributeValue`` or *default*
    * ``str(am.id)``         — raw string value
    * ``am.id()``            — type-inferred value
    * ``for av in am``       — iterate all attributes as ``AttributeValue``
    * ``len(am)``            — number of attributes
    * ``"id" in am``         — membership test
    * ``am.keys()``          — list of attribute names
    * ``am.values()``        — list of ``AttributeValue`` objects
    * ``am.items()``         — list of ``(name, AttributeValue)`` tuples
    * ``dict(am)``           — ``{name: str_value}`` plain dict
    """

    cdef xml_node  _node
    cdef object    _doc_ref

    @staticmethod
    cdef AttributeMap _from_raw(xml_node node, object doc_ref):
        cdef AttributeMap obj = AttributeMap.__new__(AttributeMap)
        obj._node    = node
        obj._doc_ref = doc_ref
        return obj

    # ------------------------------------------------------------------
    # Core lookup
    # ------------------------------------------------------------------

    cdef AttributeValue _get_attr(self, str name):
        """Return AttributeValue for *name* (with hyphen fallback) or NULL."""
        cdef bytes     cb
        cdef xml_attribute attr
        for candidate in _obj_candidate_names(name, {}):
            cb   = (<str>candidate).encode("utf-8")
            attr = self._node.attribute(cb)
            if not _attr_is_null(attr):
                return AttributeValue._from_raw(attr, self._doc_ref)
        return None

    def __getattr__(self, str name):
        result = self._get_attr(name)
        if result is None:
            raise AttributeError(
                f"No attribute {name!r} on <{self._node.name().decode('utf-8')}>"
            )
        return result

    def __getitem__(self, str name):
        result = self._get_attr(name)
        if result is None:
            raise KeyError(name)
        return result

    def get(self, str name, object default=None):
        """Return :class:`AttributeValue` for *name*, or *default* if absent."""
        result = self._get_attr(name)
        return result if result is not None else default

    def __contains__(self, str name):
        return self._get_attr(name) is not None

    # ------------------------------------------------------------------
    # Iteration
    # ------------------------------------------------------------------

    def __iter__(self):
        """Iterate all attributes as :class:`AttributeValue` objects.

        ``xmlns`` / ``xmlns:*`` namespace declarations are excluded —
        use :attr:`ObjectifiedElement.nsmap` for those.
        """
        cdef xml_attribute a = self._node.first_attribute()
        while not _attr_is_null(a):
            if not _is_xmlns_attr(a):
                yield AttributeValue._from_raw(a, self._doc_ref)
            a = a.next_attribute()

    def __len__(self):
        cdef xml_attribute a = self._node.first_attribute()
        cdef int count = 0
        while not _attr_is_null(a):
            if not _is_xmlns_attr(a):
                count += 1
            a = a.next_attribute()
        return count

    def __bool__(self):
        cdef xml_attribute a = self._node.first_attribute()
        while not _attr_is_null(a):
            if not _is_xmlns_attr(a):
                return True
            a = a.next_attribute()
        return False

    def __repr__(self):
        items = {av.name: av.str() for av in self}
        return f"AttributeMap({items!r})"

    # ------------------------------------------------------------------
    # Dict-like helpers
    # ------------------------------------------------------------------

    def keys(self):
        """List of attribute names."""
        return [av.name for av in self]

    def values(self):
        """List of :class:`AttributeValue` objects."""
        return list(self)

    def items(self):
        """List of ``(name, AttributeValue)`` tuples."""
        return [(av.name, av) for av in self]

    def to_dict(self, bint type_infer=False):
        """Return a plain ``{name: value}`` dict.

        Args:
            type_infer: If ``True``, values are type-inferred
                (bool/int/float/str). If ``False`` (default), all values
                are plain ``str``.
        """
        if type_infer:
            return {av.name: av() for av in self}
        return {av.name: str(av) for av in self}

cdef class NodeSequence:
    """A sequence of :class:`ObjectifiedElement` siblings sharing a tag.

    Supports integer indexing (including negative), ``len()``, and iteration.
    When exactly one element is present, calling or ``str()``-ing the sequence
    delegates to that sole item.
    """

    cdef list _items

    def __cinit__(self, list items):
        self._items = items

    def __len__(self):
        return len(self._items)

    def __getitem__(self, int index):
        return self._items[index]

    def __iter__(self):
        return iter(self._items)

    def __repr__(self):
        return f"NodeSequence({self._items!r})"

    def __str__(self):
        if len(self._items) == 1:
            return str(self._items[0])
        return repr(self)

    def __call__(self):
        if len(self._items) == 1:
            return self._items[0]()
        raise TypeError(
            "Cannot call a multi-element NodeSequence; "
            "index first, e.g. seq[0]()"
        )

    def __bool__(self):
        return len(self._items) > 0


# ---------------------------------------------------------------------------
# ObjectifiedElement
# ---------------------------------------------------------------------------

cdef class ObjectifiedElement:
    """Wraps an XML element node with attribute-style navigation.

    Stores the pugixml ``xml_node`` struct directly as a C-level field.
    ``_doc_ref`` keeps the owning :class:`XMLDocument` alive.
    ``_nsmap`` holds the inherited namespace map for this node
    (prefix→uri and uri→prefix entries merged together).

    Navigation
    ----------
    * ``elem.child_tag``   – finds ``<child_tag>``, ``<child-tag>``, or
      ``<prefix:tag>`` via namespace map.
    * ``elem.attr_name``   – type-inferred attribute value when no child
      element matches.
    * ``elem.tag[n]``      – n-th sibling among same-tag direct siblings.
    * ``elem.get(name)``   – safe attribute read, never raises.
    * ``elem.find(tag)``   – first matching descendant; accepts
      ``"prefix:local"`` and ``"{uri}local"`` notation.
    * ``elem.findall(tag)``– all matching descendants.

    Namespace support
    -----------------
    ``xmlns`` declarations are collected automatically during parsing and
    propagated to child wrappers.  Three tag formats are accepted:

    .. code-block:: python

       root.ns_item                    # underscore → colon mapping
       root.find("ns:item")            # explicit prefix
       root.find("{http://ns.com}item")# Clark notation

    Write support
    -------------
    Assignment updates child text or attributes; deletion removes them.
    """

    cdef xml_node _node
    cdef object   _doc_ref
    cdef dict     _nsmap      # {prefix: uri, uri: prefix} — may be empty dict

    def __cinit__(self):
        self._nsmap = {}

    @staticmethod
    cdef ObjectifiedElement _from_raw(xml_node node, object doc_ref,
                                      dict nsmap=None):
        cdef ObjectifiedElement obj = ObjectifiedElement.__new__(ObjectifiedElement)
        obj._node    = node
        obj._doc_ref = doc_ref
        obj._nsmap   = nsmap if nsmap is not None else {}
        return obj

    # ------------------------------------------------------------------
    # Attribute-style navigation
    # ------------------------------------------------------------------

    def __getattr__(self, str name):
        if name in _OBJ_RESERVED:
            raise AttributeError(name)

        cdef list       candidates = _obj_candidate_names(name, self._nsmap)
        cdef bytes      cb
        cdef xml_node   probe
        cdef xml_attribute attr_c
        cdef list       siblings
        cdef str        found_tag = None
        cdef dict       child_nsmap

        # 1. Child element lookup
        for candidate in candidates:
            cb = (<str>candidate).encode("utf-8")
            probe = self._node.child(cb)
            if not _node_is_null(probe):
                found_tag = candidate
                break

        if found_tag is not None:
            siblings = _obj_collect_siblings(
                self._node,
                (<str>found_tag).encode("utf-8"),
                self._doc_ref,
                self._nsmap,
            )
            if len(siblings) == 1:
                return siblings[0]
            return NodeSequence(siblings)

        raise AttributeError(
            f"{self._node.name().decode('utf-8')!r} "
            f"has no child element {name!r}. "
            f"Use .attrib.{name} to access attributes."
        )

    # ------------------------------------------------------------------
    # Write support
    # ------------------------------------------------------------------

    def __setattr__(self, str name, object value):
        if name in _OBJ_RESERVED:
            object.__setattr__(self, name, value)
            return

        cdef bytes         cb
        cdef xml_node      probe
        cdef xml_node      text_node
        cdef xml_attribute attr_c
        cdef bytes         val_b     = str(value).encode("utf-8")
        cdef str           found_tag = None

        for candidate in _obj_candidate_names(name, self._nsmap):
            cb = (<str>candidate).encode("utf-8")
            probe = self._node.child(cb)
            if not _node_is_null(probe):
                found_tag = candidate
                break

        if found_tag is not None:
            # pugixml's xml_node.set_value() only works on pcdata/cdata/
            # comment/pi/doctype nodes — it is a no-op on node_element.
            # Replicate XMLNode.value's setter behaviour here: replace the
            # existing text child if there is one, otherwise create one.
            text_node = probe.first_child()
            if text_node.type() == node_pcdata or text_node.type() == node_cdata:
                text_node.set_value(val_b)
            else:
                probe.prepend_child(node_pcdata).set_value(val_b)
            return

        for candidate in _obj_candidate_names(name, self._nsmap):
            cb = (<str>candidate).encode("utf-8")
            attr_c = self._node.attribute(cb)
            if not _attr_is_null(attr_c):
                attr_c.set_value(val_b)
                return

        cb = name.encode("utf-8")
        cdef xml_node new_elem = self._node.append_child(cb)
        new_elem.append_child(node_pcdata).set_value(val_b)

    def __delattr__(self, str name):
        cdef bytes         cb
        cdef xml_node      probe
        cdef xml_attribute attr_c
        cdef str           found_tag = None

        for candidate in _obj_candidate_names(name, self._nsmap):
            cb = (<str>candidate).encode("utf-8")
            probe = self._node.child(cb)
            if not _node_is_null(probe):
                found_tag = candidate
                break

        if found_tag is not None:
            self._node.remove_child(probe)
            return

        for candidate in _obj_candidate_names(name, self._nsmap):
            cb = (<str>candidate).encode("utf-8")
            attr_c = self._node.attribute(cb)
            if not _attr_is_null(attr_c):
                self._node.remove_attribute(attr_c)
                return

        raise AttributeError(
            f"{self._node.name().decode('utf-8')!r} "
            f"has no child element or attribute {name!r}"
        )

    # ------------------------------------------------------------------
    # Safe attribute access
    # ------------------------------------------------------------------

    def get(self, str name, object default=None):
        """Return the value of attribute *name*, or *default* if absent.

        Never raises.  Underscore→hyphen fallback applies.
        Namespace prefix mapping applies when a namespace map is present.

        Args:
            name (str): Attribute name.
            default: Returned when absent. Defaults to ``None``.
        """
        cdef list      candidates = _obj_candidate_names(name, self._nsmap)
        cdef bytes     cb
        cdef xml_attribute attr_c

        for candidate in candidates:
            cb = (<str>candidate).encode("utf-8")
            attr_c = self._node.attribute(cb)
            if not _attr_is_null(attr_c):
                return _infer_type(attr_c.value().decode("utf-8"))
        return default

    # ------------------------------------------------------------------
    # Namespace map access
    # ------------------------------------------------------------------

    @property
    def nsmap(self):
        """Namespace map for this element: ``{prefix: uri}``.

        Only prefix→uri entries are returned (not the reverse uri→prefix
        entries that are stored internally for lookup purposes).

        Example::

            root = objectify_from_string(
                '<root xmlns:ns="http://ns.com"><ns:item/></root>')
            root.nsmap   # {'ns': 'http://ns.com', '': 'http://default.com'}
        """
        # _nsmap contains both prefix→uri and uri→prefix entries
        # Return only prefix→uri (keys that don't start with 'http')
        # More robust: keep only entries where key doesn't contain '://'
        return {k: v for k, v in self._nsmap.items()
                if "://" not in k}

    # ------------------------------------------------------------------
    # Recursive search (namespace-aware)
    # ------------------------------------------------------------------

    def find(self, str tag, bint recursive=True):
        """Return the first descendant matching *tag*, or ``None``.

        Accepts three tag formats:

        * ``"item"``               — plain tag name
        * ``"ns:item"``            — prefixed tag name
        * ``"{http://ns.com}item"``— Clark notation (resolved via nsmap)

        Args:
            tag (str): Tag to search for.
            recursive (bool): Search all descendants (default ``True``).

        Returns:
            ObjectifiedElement | None
        """
        cdef list resolved  = _resolve_tag(tag, self._nsmap)
        cdef list tag_bytes = [(<str>c).encode("utf-8") for c in resolved]
        cdef xml_node found = _find_first(self._node, tag_bytes, recursive)
        if _node_is_null(found):
            return None
        child_nsmap = _inherit_nsmap(self._nsmap, found)
        return ObjectifiedElement._from_raw(found, self._doc_ref, child_nsmap)

    def findall(self, str tag, bint recursive=True):
        """Return all descendants matching *tag* in document order.

        Accepts the same tag formats as :meth:`find`.

        Args:
            tag (str): Tag to search for.
            recursive (bool): Search all descendants (default ``True``).

        Returns:
            list[ObjectifiedElement]
        """
        cdef list resolved  = _resolve_tag(tag, self._nsmap)
        cdef list tag_bytes = [(<str>c).encode("utf-8") for c in resolved]
        cdef list result    = []
        _find_all(self._node, tag_bytes, recursive, result,
                  self._doc_ref, self._nsmap)
        return result

    # ------------------------------------------------------------------
    # Text access
    # ------------------------------------------------------------------

    def __call__(self):
        """Type-inferred text content; ``None`` for empty/structural nodes."""
        cdef string raw = self._node.child_value()
        if raw.empty():
            return None
        return _infer_type(raw.decode("utf-8"))

    def __str__(self):
        """Raw text content, always a plain ``str``."""
        cdef string raw = self._node.child_value()
        if raw.empty():
            return ""
        return raw.decode("utf-8")

    def __repr__(self):
        return f"ObjectifiedElement(<{self._node.name().decode('utf-8')}>)"

    # ------------------------------------------------------------------
    # Iteration / sizing
    # ------------------------------------------------------------------

    def __iter__(self):
        """Iterate over direct child element nodes."""
        cdef xml_node child = self._node.first_child()
        cdef dict     child_nsmap
        while not _node_is_null(child):
            if child.type() == node_element:
                child_nsmap = _inherit_nsmap(self._nsmap, child)
                yield ObjectifiedElement._from_raw(child, self._doc_ref,
                                                   child_nsmap)
            child = child.next_sibling()

    def __len__(self):
        cdef xml_node child = self._node.first_child()
        cdef int count = 0
        while not _node_is_null(child):
            if child.type() == node_element:
                count += 1
            child = child.next_sibling()
        return count

    def __bool__(self):
        return not _node_is_null(self._node)

    def __eq__(self, other):
        if isinstance(other, ObjectifiedElement):
            return self._node == (<ObjectifiedElement>other)._node
        return NotImplemented

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def tag(self):
        """The XML tag name of this element (``str``)."""
        return self._node.name().decode("utf-8")

    @property
    def local_name(self):
        """Tag name without namespace prefix (``str``).

        Example::

            # For <ns:item>, tag = "ns:item", local_name = "item"
        """
        cdef str full = self._node.name().decode("utf-8")
        if ":" in full:
            return full.split(":", 1)[1]
        return full

    @property
    def prefix(self):
        """Namespace prefix of this element, or ``None`` if unprefixed.

        Example::

            # For <ns:item>, prefix = "ns"
        """
        cdef str full = self._node.name().decode("utf-8")
        if ":" in full:
            return full.split(":", 1)[0]
        return None

    @property
    def namespace(self):
        """Namespace URI of this element, or ``None`` if not in any namespace.

        Resolved via the inherited namespace map.

        Example::

            root = objectify_from_string(
                '<root xmlns:ns="http://ns.com"><ns:item/></root>')
            root.ns_item.namespace   # 'http://ns.com'
        """
        cdef str pfx = self.prefix
        if pfx is None:
            # check default namespace — stored under "" key
            default = self._nsmap.get("", None)
            return default if default and "://" in default else None
        val = self._nsmap.get(pfx, None)
        # make sure we got a URI not another prefix
        return val if val and "://" in val else None

    @property
    def text_content(self):
        """Raw text content, always a ``str``."""
        cdef string raw = self._node.child_value()
        return raw.decode("utf-8") if not raw.empty() else ""

    @property
    def attrib(self):
        """All attributes as an :class:`AttributeMap`.

        xmlns declarations are excluded — use :attr:`nsmap` for those.

        Example::

            root.attrib["id"]          # type-inferred value
            root.attrib.id             # same via dotted access
            str(root.attrib["id"])     # as string
            for k, v in root.attrib.items(): ...
        """
        return AttributeMap._from_raw(self._node, self._doc_ref)

    @property
    def xml(self):
        """Serialised XML of this node and its subtree."""
        cdef XMLNode wrapper = XMLNode.create_from_cpp(self._node)
        return wrapper.to_string()


# ---------------------------------------------------------------------------
# Namespace support
# ---------------------------------------------------------------------------

cdef dict _extract_ns_map(xml_node node):
    """Walk the node's attributes and collect xmlns declarations.

    Returns a dict mapping prefix → URI:
      {"": "http://default.com", "ns": "http://ns.com"}

    Only inspects the given node — callers should pass the root element
    so the most common case (all xmlns on root) is handled in one call.
    For documents that scatter xmlns across multiple elements, use
    _extract_ns_map_recursive.
    """
    cdef xml_attribute a = node.first_attribute()
    cdef dict result = {}
    cdef string name_s
    cdef str   name_py
    while not _attr_is_null(a):
        name_s  = a.name()
        name_py = name_s.decode("utf-8")
        if name_py == "xmlns":
            result[""] = a.value().decode("utf-8")
        elif name_py.startswith("xmlns:"):
            prefix = name_py[6:]   # strip "xmlns:"
            result[prefix] = a.value().decode("utf-8")
        a = a.next_attribute()
    return result


cdef dict _extract_ns_map_recursive(xml_node parent):
    """Recursively collect all xmlns declarations in the subtree."""
    cdef xml_node child = parent.first_child()
    cdef dict result = _extract_ns_map(parent)
    while not _node_is_null(child):
        if child.type() == node_element:
            result.update(_extract_ns_map_recursive(child))
        child = child.next_sibling()
    return result


# ---------------------------------------------------------------------------
# Namespace-aware name resolution
# ---------------------------------------------------------------------------

cdef list _ns_candidate_names(str py_name, dict ns_map):
    """Expand a Python identifier into candidate XML tag/attribute names.

    Handles three forms:
      1. Clark notation  "{http://ns.com}local"  → "prefix:local" for each
         prefix that maps to that URI
      2. Prefix notation "ns_local" or "ns:local" → kept as-is (after
         underscore→colon mapping) plus the hyphen fallback
      3. Plain name                               → normal _obj_candidate_names
    """
    cdef list result = []

    # Clark notation: {uri}local
    if py_name.startswith("{"):
        end = py_name.find("}")
        if end != -1:
            uri   = py_name[1:end]
            local = py_name[end + 1:]
            # find all prefixes that map to this URI
            for prefix, mapped_uri in ns_map.items():
                if mapped_uri == uri:
                    if prefix:
                        result.append(f"{prefix}:{local}")
                    else:
                        result.append(local)
            # always include bare local name as last resort
            if local not in result:
                result.append(local)
            return result if result else [py_name]

    # Prefix notation: if ns_map has a key that matches the leading segment,
    # try both "prefix:local" (colon) and "prefix-local" (hyphen) forms.
    # e.g. py_name="ns_item", ns_map={"ns": "..."} → try "ns:item"
    if ns_map:
        for prefix in ns_map:
            if prefix and py_name.startswith(prefix + "_"):
                local = py_name[len(prefix) + 1:]
                result.append(f"{prefix}:{local}")
                # also hyphen forms of the local part
                result.append(f"{prefix}:{local.replace('_', '-')}")

    # Always fall back to standard underscore→hyphen candidates
    for c in _obj_candidate_names(py_name, {}):
        if c not in result:
            result.append(c)

    return result


# ---------------------------------------------------------------------------
# NamespacedElement — ObjectifiedElement with namespace awareness
# ---------------------------------------------------------------------------

cdef class NamespacedElement(ObjectifiedElement):
    """An :class:`ObjectifiedElement` with namespace-aware lookup.

    Created automatically by :func:`objectify_from_string` /
    :func:`objectify_from_file` when a *namespaces* dict is supplied, or
    when the document contains ``xmlns`` declarations and
    ``auto_ns=True`` (default).

    Supports all three lookup styles:

    .. code-block:: python

       # Clark notation
       root.find("{http://ns.com}item")

       # Prefix notation (colon via find/findall)
       root.find("ns:item")

       # Dotted access with registered prefix
       root.ns_item          # expands to <ns:item>

    The *ns_map* is inherited by every child element automatically —
    you never need to pass it manually.
    """

    cdef dict _ns_map   # {prefix: uri}  — shared across the tree

    @staticmethod
    cdef NamespacedElement _from_raw_ns(xml_node node, object doc_ref,
                                        dict ns_map):
        cdef NamespacedElement obj = NamespacedElement.__new__(NamespacedElement)
        obj._node    = node
        obj._doc_ref = doc_ref
        obj._ns_map  = ns_map
        # Keep the inherited ObjectifiedElement._nsmap in sync so that
        # inherited properties (namespace, nsmap) — which read _nsmap —
        # resolve prefixes/URIs correctly for namespaced elements too.
        obj._nsmap   = ns_map
        return obj

    # ------------------------------------------------------------------
    # Override __getattr__ to use namespace-aware candidate names
    # ------------------------------------------------------------------

    def __getattr__(self, str name):
        if name in _OBJ_RESERVED or name == "_ns_map":
            raise AttributeError(name)

        cdef list       candidates = _ns_candidate_names(name, self._ns_map)
        cdef bytes      cb
        cdef xml_node   probe
        cdef xml_attribute attr_c
        cdef list       siblings
        cdef str        found_tag = None
        cdef string     tag_s
        cdef string     child_name

        # 1. Child element lookup
        for candidate in candidates:
            cb = (<str>candidate).encode("utf-8")
            probe = self._node.child(cb)
            if not _node_is_null(probe):
                found_tag = candidate
                break

        if found_tag is not None:
            siblings = _ns_collect_siblings(
                self._node,
                (<str>found_tag).encode("utf-8"),
                self._doc_ref,
                self._ns_map,
            )
            if len(siblings) == 1:
                return siblings[0]
            return NodeSequence(siblings)

        raise AttributeError(
            f"{self._node.name().decode('utf-8')!r} "
            f"has no child element {name!r}. "
            f"Use .attrib.{name} to access attributes."
        )

    # ------------------------------------------------------------------
    # Override find / findall to use namespace-aware candidates
    # ------------------------------------------------------------------

    def find(self, str tag, bint recursive=True):
        """Namespace-aware find.  Accepts Clark notation, prefix notation,
        or plain names.  See :meth:`ObjectifiedElement.find`."""
        cdef list tag_bytes = [(<str>c).encode("utf-8")
                               for c in _ns_candidate_names(tag, self._ns_map)]
        cdef xml_node found = _find_first(self._node, tag_bytes, recursive)
        if _node_is_null(found):
            return None
        return NamespacedElement._from_raw_ns(found, self._doc_ref, self._ns_map)

    def findall(self, str tag, bint recursive=True):
        """Namespace-aware findall.  Accepts Clark notation, prefix notation,
        or plain names.  See :meth:`ObjectifiedElement.findall`."""
        cdef list tag_bytes = [(<str>c).encode("utf-8")
                               for c in _ns_candidate_names(tag, self._ns_map)]
        cdef list result = []
        _ns_find_all(self._node, tag_bytes, recursive, result,
                     self._doc_ref, self._ns_map)
        return result

    # ------------------------------------------------------------------
    # ns_map property — expose for inspection / debugging
    # ------------------------------------------------------------------

    @property
    def ns_map(self):
        """The namespace map ``{prefix: uri}`` active for this element."""
        return dict(self._ns_map)


# ---------------------------------------------------------------------------
# Namespace-aware sibling collection and search helpers
# ---------------------------------------------------------------------------

cdef list _ns_collect_siblings(xml_node parent, bytes tag_b,
                                object doc_ref, dict ns_map):
    cdef xml_node child    = parent.first_child()
    cdef list     result   = []
    cdef string   tag_s    = tag_b
    cdef string   child_name
    while not _node_is_null(child):
        if child.type() == node_element:
            child_name = child.name()
            if child_name == tag_s:
                result.append(
                    NamespacedElement._from_raw_ns(child, doc_ref, ns_map)
                )
        child = child.next_sibling()
    return result


cdef void _ns_find_all(xml_node parent, list tag_bytes, bint recursive,
                       list result, object doc_ref, dict ns_map):
    cdef xml_node child = parent.first_child()
    cdef string   child_name
    while not _node_is_null(child):
        if child.type() == node_element:
            child_name = child.name()
            for tb in tag_bytes:
                if child_name == <string>(<bytes>tb):
                    result.append(
                        NamespacedElement._from_raw_ns(child, doc_ref, ns_map)
                    )
                    break
            if recursive:
                _ns_find_all(child, tag_bytes, recursive,
                             result, doc_ref, ns_map)
        child = child.next_sibling()


# ---------------------------------------------------------------------------
# Updated entry points — replace objectify_from_string / objectify_from_file
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Public entry points (namespace-aware)
# ---------------------------------------------------------------------------

def objectify_from_node(object node,
                         dict namespaces=None,
                         bint auto_ns=True):
    """Wrap an existing :class:`XMLNode` as an :class:`ObjectifiedElement`.

    No re-parsing is done — the node's owning document stays alive via
    the node's own reference.  Useful when you already have a parsed tree
    and want to switch to the objectify navigation API for a subtree.

    Args:
        node (XMLNode): A node from a parsed :class:`XMLDocument`.
        namespaces (dict | None): Optional ``{prefix: uri}`` map.
        auto_ns (bool): Automatically extract ``xmlns`` declarations
            (default ``True``).

    Returns:
        NamespacedElement | ObjectifiedElement: Wrapped node.

    Raises:
        TypeError: If *node* is not an :class:`XMLNode`.
        PygiXMLError: If *node* is null.

    Example::

        doc  = pygixml.parse_string(xml)
        root = objectify.from_node(doc.root)
        print(root.user_profile.first_name)

        # wrap a specific child
        child = doc.root.child("user-profile")
        elem  = objectify.from_node(child)
        print(elem.first_name)
    """
    if not isinstance(node, XMLNode):
        raise TypeError(
            f"expected XMLNode, got {type(node).__name__!r}"
        )
    cdef xml_node raw = (<XMLNode>node)._node
    if _node_is_null(raw):
        raise PygiXMLError("Cannot wrap a null XMLNode")

    # Use the XMLNode's parent document as doc_ref to keep it alive.
    # We don't have direct access to the XMLDocument here, so we keep
    # the XMLNode itself as the ref — it holds its own document reference.
    cdef object doc_ref = node

    cdef dict ns_map = {}
    if auto_ns:
        ns_map = _extract_ns_map_recursive(raw)
    if namespaces:
        ns_map.update(namespaces)

    if ns_map:
        return NamespacedElement._from_raw_ns(raw, doc_ref, ns_map)
    return ObjectifiedElement._from_raw(raw, doc_ref)


def objectify_from_string(str xml,
                           dict namespaces=None,
                           bint auto_ns=True,
                           str encoding=u"auto"):
    """Parse an XML string and return the root as :class:`ObjectifiedElement`
    or :class:`NamespacedElement`.

    Args:
        xml (str): XML source text.
        namespaces (dict | None): Optional ``{prefix: uri}`` map supplied by
            the caller.  Merged with any ``xmlns`` declarations found in the
            document when *auto_ns* is ``True``.
        auto_ns (bool): When ``True`` (default), automatically extract
            ``xmlns`` declarations from the root element and use
            :class:`NamespacedElement`.  Set to ``False`` to get a plain
            :class:`ObjectifiedElement`` regardless of namespace declarations.
        encoding (str): Input encoding hint. Default ``"auto"`` (detect from
            BOM or XML declaration). Other values: ``"utf-8"``, ``"utf-16"``,
            ``"latin-1"``, etc.

    Returns:
        NamespacedElement | ObjectifiedElement: Document root.

    Raises:
        PygiXMLError: If the XML is malformed or has no root element.

    Example::

        root = objectify_from_string(xml)
        root = objectify_from_string(xml, encoding="latin-1")
        root = objectify_from_string(xml, namespaces={"dc": "http://dc.com"})
    """
    cdef XMLDocument   doc   = XMLDocument()
    cdef bytes         xml_b = xml.encode("utf-8")
    cdef xml_encoding  enc   = _str_to_encoding(encoding)
    if not pygixml_load_buffer(doc._doc,
                                <const void*>(<char*>xml_b),
                                len(xml_b), parse_full, enc):
        raise PygiXMLError("Failed to parse XML string")
    cdef xml_node root_raw = doc._doc.first_child()
    if _node_is_null(root_raw):
        raise PygiXMLError("Parsed document has no root element")

    cdef dict ns_map = {}
    if auto_ns:
        ns_map = _extract_ns_map_recursive(root_raw)
    if namespaces:
        ns_map.update(namespaces)

    if ns_map:
        return NamespacedElement._from_raw_ns(root_raw, doc, ns_map)
    return ObjectifiedElement._from_raw(root_raw, doc)


def objectify_from_file(str path,
                         dict namespaces=None,
                         bint auto_ns=True,
                         str encoding=u"auto"):
    """Parse an XML file and return the root as :class:`ObjectifiedElement`
    or :class:`NamespacedElement`.

    Args:
        path (str): Filesystem path to the XML file.
        namespaces (dict | None): Optional ``{prefix: uri}`` map.
        auto_ns (bool): Automatically extract ``xmlns`` declarations
            (default ``True``).
        encoding (str): Input encoding hint. Default ``"auto"`` (detect from
            BOM or XML declaration). Other values: ``"utf-8"``, ``"utf-16"``,
            ``"latin-1"``, etc.

    Returns:
        NamespacedElement | ObjectifiedElement: Document root.

    Raises:
        PygiXMLError: If the file cannot be read, is malformed, or empty.

    Example::

        root = objectify_from_file("data.xml")
        root = objectify_from_file("legacy.xml", encoding="latin-1")
    """
    cdef XMLDocument  doc   = XMLDocument()
    cdef bytes        path_b = path.encode("utf-8")
    cdef xml_encoding enc    = _str_to_encoding(encoding)
    if not pygixml_load_file(doc._doc,
                              <const char*>path_b,
                              parse_full, enc):
        raise PygiXMLError(f"Failed to parse XML file: {path}")
    cdef xml_node root_raw = doc._doc.first_child()
    if _node_is_null(root_raw):
        raise PygiXMLError(f"File {path!r} has no root element")

    cdef dict ns_map = {}
    if auto_ns:
        ns_map = _extract_ns_map_recursive(root_raw)
    if namespaces:
        ns_map.update(namespaces)

    if ns_map:
        return NamespacedElement._from_raw_ns(root_raw, doc, ns_map)
    return ObjectifiedElement._from_raw(root_raw, doc)
    