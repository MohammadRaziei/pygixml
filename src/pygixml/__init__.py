"""
pygixml - Python wrapper for pugixml using Cython

A fast and efficient XML parser and manipulator for Python.
"""

import importlib.metadata


from .pygixml_cy import (
    __version__,
    XMLDocument,
    XMLNode,
    XMLAttribute,
    XPathQuery,
    XPathNode,
    XPathNodeSet,
    PygiXMLError,
    PygiXMLNullNodeError,
    ParseFlags,
    parse_string,
    parse_file,
)



__all__ = [
    "XMLDocument",
    "XMLNode",
    "XMLAttribute",
    "XPathQuery",
    "XPathNode",
    "XPathNodeSet",
    "PygiXMLError",
    "PygiXMLNullNodeError",
    "ParseFlags",
    "parse_string",
    "parse_file",
]
