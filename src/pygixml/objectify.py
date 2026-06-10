"""
pygixml.objectify — lxml.objectify-style interface.

All logic lives in objectify.pxi and namespace.pxi, compiled into
pygixml_cy.so.

Usage::

    from pygixml import objectify

    # Plain XML
    root = objectify.from_string(xml)
    root = objectify.from_file(path)

    # Namespace-aware (auto-detected from xmlns declarations)
    root = objectify.from_string(xml)
    root.find("{http://ns.com}item")   # Clark notation
    root.find("ns:item")               # prefix notation
    root.ns_item                       # dotted access

    # Explicit namespace map
    root = objectify.from_string(xml, namespaces={"dc": "http://dc.com"})
    root.dc_title
"""

from .pygixml_cy import (
    ObjectifiedElement,
    NodeSequence,
    NamespacedElement,
    AttributeValue,
    AttributeMap,
    objectify_from_string as from_string,
    objectify_from_file   as from_file,
    objectify_from_node   as from_node,
)

__all__ = [
    "ObjectifiedElement",
    "NodeSequence",
    "NamespacedElement",
    "AttributeValue",
    "AttributeMap",
    "from_string",
    "from_file",
    "from_node",
]