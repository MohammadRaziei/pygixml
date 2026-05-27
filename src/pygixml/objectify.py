"""
pygixml.objectify
=================

An ``lxml.objectify``-style interface for pygixml that lets you navigate
the XML tree with dotted attribute access, automatic type inference,
transparent hyphen/underscore mapping, and sequence handling for
repeated sibling elements.

Entry points
------------
``from_string(xml)``   – parse an XML string and return the root element.
``from_file(path)``    – parse an XML file and return the root element.

Both return an :class:`ObjectifiedElement` wrapping the document root.

Example
-------
::

    from pygixml import objectify

    xml = '''
    <database name="users_db" version="1.2">
        <user-profile id="101" verified="true">
            <first_name>Mohammad</first_name>
            <balance>450.75</balance>
        </user-profile>
        <entry>Value A</entry>
        <entry>Value B</entry>
    </database>
    '''

    root = objectify.from_string(xml)

    # Dotted access + hyphen->underscore mapping
    print(root.user_profile.first_name)        # 'Mohammad'

    # Attribute type inference
    print(root.version)                        # 1.2  (float)
    print(root.user_profile.id)               # 101  (int)
    print(root.user_profile.verified)         # True (bool)

    # Text content via call or str()
    print(root.user_profile.balance())        # 450.75  (float)
    print(str(root.user_profile.first_name))  # 'Mohammad'

    # Sequence indexing and iteration
    print(root.entry[1])                      # 'Value B'
    print([str(e) for e in root.entry])       # ['Value A', 'Value B']
"""

from __future__ import annotations

from typing import Iterator

import pygixml


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _infer_type(raw: str):
    """Convert *raw* (a string) to the most specific Python scalar type.

    Priority order:
      1. bool  – case-insensitive "true" / "false"
      2. int   – no decimal point, no exponent
      3. float – has decimal point or exponent
      4. str   – everything else
    """
    if raw is None:
        return None
    stripped = raw.strip()
    lower = stripped.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    try:
        # Reject strings like "1.0" from the int branch by checking for
        # '.' and 'e'/'E' before attempting the conversion.
        if "." not in stripped and "e" not in lower:
            return int(stripped)
    except ValueError:
        pass
    try:
        return float(stripped)
    except ValueError:
        pass
    return raw


def _candidate_names(py_name: str):
    """Yield the XML tag/attribute names to probe for a Python identifier.

    Underscores are the only character that cannot legally appear in a
    Python identifier but are common in XML hyphenated tags, so we map
    ``foo_bar`` -> ``foo-bar`` as a secondary candidate.  The original
    name is always tried first so that a literal underscore tag wins over
    a hyphenated one when both are present.
    """
    yield py_name
    hyphen = py_name.replace("_", "-")
    if hyphen != py_name:
        yield hyphen


# ---------------------------------------------------------------------------
# NodeSequence – a lightweight list-like view of same-name siblings
# ---------------------------------------------------------------------------

class NodeSequence:
    """A sequence of :class:`ObjectifiedElement` siblings that share a tag.

    Supports integer indexing, ``len()``, and iteration.  When only one
    element is present the sequence still behaves as a sequence; calling
    it or using ``str()`` on the sequence itself delegates to the sole item.
    """

    __slots__ = ("_items",)

    def __init__(self, items: list):
        # items: list[ObjectifiedElement]
        self._items = items

    # -- Sequence protocol --------------------------------------------------

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, index: int):
        # Returns ObjectifiedElement; the caller may further drill into it.
        return self._items[index]

    def __iter__(self) -> Iterator:
        return iter(self._items)

    def __repr__(self) -> str:
        return f"NodeSequence({self._items!r})"

    def __str__(self) -> str:
        # Convenience: if there is exactly one element, act like it.
        if len(self._items) == 1:
            return str(self._items[0])
        return repr(self)

    def __call__(self):
        # Convenience: if there is exactly one element, act like it.
        if len(self._items) == 1:
            return self._items[0]()
        raise TypeError(
            "Cannot call a multi-element NodeSequence; "
            "index first, e.g. seq[0]()"
        )

    def __bool__(self) -> bool:
        return bool(self._items)


# ---------------------------------------------------------------------------
# ObjectifiedElement – the main public wrapper
# ---------------------------------------------------------------------------

# Names that must never be intercepted by __getattr__; they belong to the
# object protocol or our own private interface.
_RESERVED = frozenset({"_node", "_doc_ref"})


class ObjectifiedElement:
    """Wraps a :class:`pygixml.XMLNode` and provides attribute-style access.

    Navigation
    ----------
    * ``elem.child_tag``     – first child element named ``child_tag``
      (or ``child-tag`` via underscore->hyphen fallback).
    * ``elem.attr_name``     – attribute value (type-inferred) when no
      child element with that name exists.
    * ``elem.tag_name[n]``  – the *n*-th sibling element among all
      siblings sharing the same tag.

    When multiple siblings share a tag, ``elem.tag_name`` returns a
    :class:`NodeSequence` that supports indexing and iteration.

    Type inference
    --------------
    Attribute values and leaf-node text are automatically converted:
    ``"true"``/``"false"`` -> ``bool``, integer strings -> ``int``,
    decimal strings -> ``float``, everything else -> ``str``.

    Text access
    -----------
    * ``str(elem)``  – the node's raw text content as a ``str``.
    * ``elem()``     – type-inferred text content (numeric/bool leaf nodes
      are returned as native Python types).

    Priority
    --------
    Child elements take priority over same-named attributes.  To access an
    attribute when a same-named child element also exists, use the
    underlying node directly::

        elem._node.attribute('name').value

    Document lifetime
    -----------------
    The ``_doc_ref`` slot holds a reference to the owning
    :class:`pygixml.XMLDocument`.  pugixml nodes are memory-managed by the
    document; keeping this reference prevents premature garbage collection.
    """

    __slots__ = ("_node", "_doc_ref")

    def __init__(self, node: pygixml.XMLNode, doc_ref=None):
        object.__setattr__(self, "_node", node)
        object.__setattr__(self, "_doc_ref", doc_ref)

    # ------------------------------------------------------------------
    # Core attribute lookup
    # ------------------------------------------------------------------

    def __getattr__(self, name: str):
        if name in _RESERVED:
            raise AttributeError(name)

        node: pygixml.XMLNode = object.__getattribute__(self, "_node")
        doc_ref = object.__getattribute__(self, "_doc_ref")

        # ---- 1. Child element lookup (direct name, then hyphen form) --
        found_tag: str | None = None
        for candidate in _candidate_names(name):
            probe = node.child(candidate)
            if probe and not probe.is_null():
                found_tag = candidate
                break

        if found_tag is not None:
            # Collect *all* direct siblings with the same tag so that
            # indexing (root.entry[1]) and iteration work correctly.
            siblings = _collect_siblings(node, found_tag, doc_ref)
            if len(siblings) == 1:
                return siblings[0]
            return NodeSequence(siblings)

        # ---- 2. Attribute lookup (direct name, then hyphen form) ------
        for candidate in _candidate_names(name):
            attr = node.attribute(candidate)
            if attr and attr.name is not None:
                return _infer_type(attr.value)

        raise AttributeError(
            f"{node.name!r} has no child element or attribute {name!r}"
        )

    # ------------------------------------------------------------------
    # Text / scalar access
    # ------------------------------------------------------------------

    def __call__(self):
        """Return the type-inferred text content of this node.

        Returns the native Python type where possible (int, float, bool),
        or a plain ``str`` for everything else.  Returns ``None`` for empty
        or purely structural (non-leaf) nodes.
        """
        raw = object.__getattribute__(self, "_node").text()
        return _infer_type(raw) if raw else None

    def __str__(self) -> str:
        """Return the text content of this node as a ``str``."""
        node: pygixml.XMLNode = object.__getattribute__(self, "_node")
        return node.text() or ""

    def __repr__(self) -> str:
        node: pygixml.XMLNode = object.__getattribute__(self, "_node")
        return f"ObjectifiedElement(<{node.name}>)"

    # ------------------------------------------------------------------
    # Iteration – iterates over direct child element nodes
    # ------------------------------------------------------------------

    def __iter__(self) -> Iterator["ObjectifiedElement"]:
        """Iterate over direct child element nodes."""
        node: pygixml.XMLNode = object.__getattribute__(self, "_node")
        doc_ref = object.__getattribute__(self, "_doc_ref")
        for child in node.children():
            yield ObjectifiedElement(child, doc_ref)

    # ------------------------------------------------------------------
    # Length – number of direct child element nodes
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        node: pygixml.XMLNode = object.__getattribute__(self, "_node")
        count = 0
        for _ in node.children():
            count += 1
        return count

    # ------------------------------------------------------------------
    # Boolean – mirrors XMLNode truthiness (False when null)
    # ------------------------------------------------------------------

    def __bool__(self) -> bool:
        node: pygixml.XMLNode = object.__getattribute__(self, "_node")
        return bool(node)

    # ------------------------------------------------------------------
    # Equality – identity comparison of underlying nodes
    # ------------------------------------------------------------------

    def __eq__(self, other) -> bool:
        if isinstance(other, ObjectifiedElement):
            return (
                object.__getattribute__(self, "_node")
                == object.__getattribute__(other, "_node")
            )
        return NotImplemented

    # ------------------------------------------------------------------
    # Convenience read-only properties
    # ------------------------------------------------------------------

    @property
    def tag(self) -> str | None:
        """The XML tag name of this element."""
        return object.__getattribute__(self, "_node").name

    @property
    def text_content(self) -> str:
        """The raw text content of this element (always a ``str``)."""
        node: pygixml.XMLNode = object.__getattribute__(self, "_node")
        return node.text() or ""

    @property
    def attrib(self) -> dict:
        """All attributes as a ``{name: typed_value}`` dict.

        Attribute values are type-inferred (bool/int/float/str).
        """
        node: pygixml.XMLNode = object.__getattribute__(self, "_node")
        result: dict = {}
        attr = node.first_attribute()
        while attr and attr.name is not None:
            result[attr.name] = _infer_type(attr.value)
            attr = attr.next_attribute()
        return result

    @property
    def xml(self) -> str:
        """Serialized XML of this node and its subtree."""
        return object.__getattribute__(self, "_node").to_string()


# ---------------------------------------------------------------------------
# Internal: collect direct children matching a tag
# ---------------------------------------------------------------------------

def _collect_siblings(
    parent: pygixml.XMLNode, tag: str, doc_ref
) -> list:
    """Return one :class:`ObjectifiedElement` per direct child of *parent*
    whose tag name equals *tag*.

    Iterates over ``parent.children()`` once (O(k) in direct-child count).
    """
    result = []
    for child in parent.children():
        if child.name == tag:
            result.append(ObjectifiedElement(child, doc_ref))
    return result


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def from_string(xml: str) -> ObjectifiedElement:
    """Parse an XML *string* and return the document root as an
    :class:`ObjectifiedElement`.

    Args:
        xml (str): The XML source text.

    Returns:
        ObjectifiedElement: The document root element.

    Raises:
        pygixml.PygiXMLError: If the XML is malformed or has no root element.

    Example::

        root = objectify.from_string('<root><item id="1">hello</item></root>')
        print(root.item.id)    # 1
        print(str(root.item))  # 'hello'
    """
    doc = pygixml.parse_string(xml)
    root_node = doc.root
    if root_node is None or root_node.is_null():
        raise pygixml.PygiXMLError("Parsed document has no root element")
    return ObjectifiedElement(root_node, doc)


def from_file(path: str) -> ObjectifiedElement:
    """Parse an XML file at *path* and return the document root as an
    :class:`ObjectifiedElement`.

    Args:
        path (str): Filesystem path to the XML file.

    Returns:
        ObjectifiedElement: The document root element.

    Raises:
        pygixml.PygiXMLError: If the file cannot be read or the XML is
            malformed or empty.

    Example::

        root = objectify.from_file('config.xml')
        print(root.server.host)
    """
    doc = pygixml.parse_file(path)
    root_node = doc.root
    if root_node is None or root_node.is_null():
        raise pygixml.PygiXMLError(f"File {path!r} has no root element")
    return ObjectifiedElement(root_node, doc)