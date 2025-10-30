"""
pygixml - Python wrapper for pugixml using Cython

A fast and efficient XML parser and manipulator for Python.
"""

import importlib

__version__ = importlib.metadata.version("pygixml")

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
    parse_file
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
    "parse_string",
    "parse_file"
]
