# objectify.pxi
# -------------
# objectify.py is a thin re-export shim:
#   from .pygixml_cy import (ObjectifiedElement, NodeSequence,
#       objectify_from_string as from_string,
#       objectify_from_file   as from_file)

# ---------------------------------------------------------------------------
# Null-check helpers
# ---------------------------------------------------------------------------
# xml_node      : type() == node_null  (mirrors XMLNode.__bool__)
# xml_attribute : name().empty()       (mirrors XMLAttribute.__bool__)

cdef inline bint _node_is_null(xml_node n):
    return n.type() == node_null

cdef inline bint _attr_is_null(xml_attribute a):
    cdef string name = a.name()   # const char* → std::string first
    return name.empty()

# ---------------------------------------------------------------------------
# Internal helpers (cdef — not visible from Python)
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


cdef list _obj_candidate_names(str py_name):
    """Return [py_name] or [py_name, hyphen_form] for identifier mapping."""
    cdef str h = py_name.replace("_", "-")
    if h == py_name:
        return [py_name]
    return [py_name, h]


cdef list _obj_collect_siblings(xml_node parent, bytes tag_b, object doc_ref):
    """Return ObjectifiedElements for every direct child of parent named tag_b."""
    cdef xml_node child    = parent.first_child()
    cdef list     result   = []
    cdef string   tag_s    = tag_b   # bytes → std::string for reliable comparison
    cdef string   child_name
    while not _node_is_null(child):
        if child.type() == node_element:
            child_name = child.name()
            if child_name == tag_s:
                result.append(ObjectifiedElement._from_raw(child, doc_ref))
        child = child.next_sibling()
    return result


cdef xml_node _find_first(xml_node parent, list tag_bytes, bint recursive):
    """Return the first descendant of parent whose name is in tag_bytes.

    Searches breadth-first across direct children, then recurses when
    recursive=True.  Returns a null xml_node when nothing is found.
    """
    cdef xml_node child = parent.first_child()
    cdef xml_node found
    cdef string   child_name

    # First pass: direct children
    while not _node_is_null(child):
        if child.type() == node_element:
            child_name = child.name()
            for tb in tag_bytes:
                if child_name == <string>(<bytes>tb):
                    return child
        child = child.next_sibling()

    if not recursive:
        return xml_node()   # default-constructed = null

    # Second pass: recurse into children
    child = parent.first_child()
    while not _node_is_null(child):
        if child.type() == node_element:
            found = _find_first(child, tag_bytes, True)
            if not _node_is_null(found):
                return found
        child = child.next_sibling()

    return xml_node()   # null


cdef void _find_all(xml_node parent, list tag_bytes, bint recursive,
                    list result, object doc_ref):
    """Append every descendant of parent whose name is in tag_bytes to result."""
    cdef xml_node child = parent.first_child()
    cdef string   child_name

    while not _node_is_null(child):
        if child.type() == node_element:
            child_name = child.name()
            for tb in tag_bytes:
                if child_name == <string>(<bytes>tb):
                    result.append(ObjectifiedElement._from_raw(child, doc_ref))
                    break
            if recursive:
                _find_all(child, tag_bytes, True, result, doc_ref)
        child = child.next_sibling()


_OBJ_RESERVED = frozenset({"_node", "_doc_ref"})


# ---------------------------------------------------------------------------
# NodeSequence
# ---------------------------------------------------------------------------

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
        # Avoid 'bool(...)' — conflicts with 'from libcpp cimport bool' in pyx
        return len(self._items) > 0


# ---------------------------------------------------------------------------
# ObjectifiedElement
# ---------------------------------------------------------------------------

cdef class ObjectifiedElement:
    """Wraps an XML element node with attribute-style navigation.

    Stores the pugixml ``xml_node`` struct directly as a C-level field —
    no intermediate Python wrapper is allocated per access.
    ``_doc_ref`` keeps the owning :class:`XMLDocument` alive so the
    underlying pugixml memory is never freed while a wrapper exists.

    Navigation
    ----------
    * ``elem.child_tag``              – first ``<child_tag>`` child element;
      falls back to ``<child-tag>`` via underscore→hyphen mapping.
    * ``elem.attr_name``              – XML attribute value (type-inferred)
      when no matching child element exists.
    * ``elem.tag[n]``                 – n-th sibling among direct siblings
      sharing the same tag; returns a :class:`NodeSequence` when multiple
      exist.
    * ``elem.get('attr', default)``   – safe attribute read, never raises.
    * ``elem.find('tag')``            – first matching descendant or ``None``.
    * ``elem.findall('tag')``         – all matching descendants as a list.

    Type inference: ``"true"``/``"false"`` → ``bool``, integer strings →
    ``int``, decimal/scientific strings → ``float``, everything else → ``str``.

    Priority: child elements win over same-named attributes.
    To read a shadowed attribute use ``elem.attrib['name']`` or
    ``elem.get('name')``.
    """

    cdef xml_node _node     # C struct — zero Python object overhead
    cdef object   _doc_ref  # XMLDocument ref — prevents GC of the document

    def __cinit__(self):
        pass  # _node is default-constructed (empty/null) by Cython

    @staticmethod
    cdef ObjectifiedElement _from_raw(xml_node node, object doc_ref):
        cdef ObjectifiedElement obj = ObjectifiedElement.__new__(ObjectifiedElement)
        obj._node    = node
        obj._doc_ref = doc_ref
        return obj

    # ------------------------------------------------------------------
    # Attribute-style navigation
    # ------------------------------------------------------------------

    def __getattr__(self, str name):
        if name in _OBJ_RESERVED:
            raise AttributeError(name)

        cdef list       candidates = _obj_candidate_names(name)
        cdef bytes      cb
        cdef xml_node   probe
        cdef xml_attribute attr_c
        cdef list       siblings
        cdef str        found_tag = None

        # 1. Child element lookup (exact name, then hyphen form)
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
            )
            if len(siblings) == 1:
                return siblings[0]
            return NodeSequence(siblings)

        # 2. Attribute lookup (exact name, then hyphen form)
        for candidate in candidates:
            cb = (<str>candidate).encode("utf-8")
            attr_c = self._node.attribute(cb)
            if not _attr_is_null(attr_c):
                return _infer_type(attr_c.value().decode("utf-8"))

        raise AttributeError(
            f"{self._node.name().decode('utf-8')!r} "
            f"has no child element or attribute {name!r}"
        )

    # ------------------------------------------------------------------
    # Safe attribute access
    # ------------------------------------------------------------------

    def get(self, str name, object default=None):
        """Return the value of attribute *name*, or *default* if absent.

        Unlike dotted access which raises ``AttributeError`` for missing
        names, ``get()`` never raises — it behaves like ``dict.get()``.
        Only attributes are searched; child elements are not considered.
        The underscore→hyphen fallback applies.

        Args:
            name (str): Attribute name (underscores map to hyphens).
            default: Returned when the attribute is absent. Defaults to
                ``None``.

        Returns:
            The type-inferred attribute value, or *default*.

        Example::

            root = objectify_from_string('<user id="42" active="true"/>')
            root.get('id')           # 42   (int)
            root.get('missing')      # None
            root.get('missing', -1)  # -1
        """
        cdef list      candidates = _obj_candidate_names(name)
        cdef bytes     cb
        cdef xml_attribute attr_c

        for candidate in candidates:
            cb = (<str>candidate).encode("utf-8")
            attr_c = self._node.attribute(cb)
            if not _attr_is_null(attr_c):
                return _infer_type(attr_c.value().decode("utf-8"))
        return default

    # ------------------------------------------------------------------
    # Recursive search
    # ------------------------------------------------------------------

    def find(self, str tag, bint recursive=True):
        """Return the first descendant element whose tag matches *tag*.

        Checks direct children first, then recurses deeper when
        *recursive* is ``True``.  The underscore→hyphen fallback applies.

        Args:
            tag (str): Tag name to search for.
            recursive (bool): Search all descendants (default ``True``),
                or only direct children (``False``).

        Returns:
            ObjectifiedElement | None: First match, or ``None``.

        Example::

            root = objectify_from_string(
                '<root><a><b><target>found</target></b></a></root>')
            print(str(root.find('target')))          # 'found'
            print(root.find('target', recursive=False))  # None
        """
        cdef list tag_bytes = [(<str>c).encode("utf-8")
                               for c in _obj_candidate_names(tag)]
        cdef xml_node found = _find_first(self._node, tag_bytes, recursive)
        if _node_is_null(found):
            return None
        return ObjectifiedElement._from_raw(found, self._doc_ref)

    def findall(self, str tag, bint recursive=True):
        """Return all descendant elements whose tag matches *tag*.

        Args:
            tag (str): Tag name to search for.
            recursive (bool): Search all descendants (default ``True``),
                or only direct children (``False``).

        Returns:
            list[ObjectifiedElement]: All matches (may be empty).

        Example::

            root = objectify_from_string('''
                <root>
                  <item>a</item>
                  <group><item>b</item></group>
                  <item>c</item>
                </root>''')
            root.findall('item')                    # [a, b, c]
            root.findall('item', recursive=False)   # [a, c]
        """
        cdef list tag_bytes = [(<str>c).encode("utf-8")
                               for c in _obj_candidate_names(tag)]
        cdef list result = []
        _find_all(self._node, tag_bytes, recursive, result, self._doc_ref)
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
        while not _node_is_null(child):
            if child.type() == node_element:
                yield ObjectifiedElement._from_raw(child, self._doc_ref)
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
    def text_content(self):
        """Raw text content, always a ``str``."""
        cdef string raw = self._node.child_value()
        return raw.decode("utf-8") if not raw.empty() else ""

    @property
    def attrib(self):
        """All attributes as a ``{name: typed_value}`` dict.

        Walks the C-level attribute linked list directly — no Python wrappers.
        Values are type-inferred (bool / int / float / str).
        """
        cdef xml_attribute a = self._node.first_attribute()
        cdef dict result = {}
        while not _attr_is_null(a):
            result[a.name().decode("utf-8")] = _infer_type(a.value().decode("utf-8"))
            a = a.next_attribute()
        return result

    @property
    def xml(self):
        """Serialised XML of this node and its subtree."""
        cdef XMLNode wrapper = XMLNode.create_from_cpp(self._node)
        return wrapper.to_string()


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def objectify_from_string(str xml):
    """Parse an XML string and return the root as :class:`ObjectifiedElement`.

    Args:
        xml (str): XML source text.

    Returns:
        ObjectifiedElement: The document root element.

    Raises:
        PygiXMLError: If the XML is malformed or has no root element.

    Example::

        root = objectify_from_string('<db ver="2"><item>x</item></db>')
        print(root.ver)        # 2  (int)
        print(str(root.item))  # 'x'
    """
    cdef XMLDocument doc = XMLDocument()
    if not doc.load_string(xml):
        raise PygiXMLError("Failed to parse XML string")
    cdef xml_node root_raw = doc._doc.first_child()
    if _node_is_null(root_raw):
        raise PygiXMLError("Parsed document has no root element")
    return ObjectifiedElement._from_raw(root_raw, doc)


def objectify_from_file(str path):
    """Parse an XML file and return the root as :class:`ObjectifiedElement`.

    Args:
        path (str): Filesystem path to the XML file.

    Returns:
        ObjectifiedElement: The document root element.

    Raises:
        PygiXMLError: If the file cannot be read, is malformed, or empty.

    Example::

        root = objectify_from_file("config.xml")
        print(root.server.host)
    """
    cdef XMLDocument doc = XMLDocument()
    if not doc.load_file(path):
        raise PygiXMLError(f"Failed to parse XML file: {path}")
    cdef xml_node root_raw = doc._doc.first_child()
    if _node_is_null(root_raw):
        raise PygiXMLError(f"File {path!r} has no root element")
    return ObjectifiedElement._from_raw(root_raw, doc)
