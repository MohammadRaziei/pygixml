"""
pygixml - Python wrapper for pugixml using Cython

A fast and efficient XML parser and manipulator for Python.
"""

from .pygixml import (
    XMLDocument,
    XMLNode,
    XMLAttribute,
    XPathQuery,
    XPathNode,
    XPathNodeSet,
    PygiXMLError,
    PygiXMLNullNodeError,
    parse_string,
    parse_file,
    node_null,
    node_document,
    node_element,
    node_pcdata,
    node_cdata,
    node_comment,
    node_pi,
    node_declaration,
    node_doctype
)

__version__ = "0.4.0"
__all__ = [
    "XMLDocument",
    "XMLNode",
    "XMLAttribute",
    "XPathQuery",
    "XPathNode",
    "XPathNodeSet",
    "PygiXMLError",
    "PygiXMLNullNodeError",
    "parse_string",
    "parse_file",
    "node_null",
    "node_document",
    "node_element",
    "node_pcdata",
    "node_cdata",
    "node_comment",
    "node_pi",
    "node_declaration",
    "node_doctype"
]
