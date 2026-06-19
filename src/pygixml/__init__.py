"""
pygixml - Python wrapper for pugixml using Cython

A fast and efficient XML parser and manipulator for Python.
"""

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
    StreamElement,
    PullParser,
    iterparse,
    iterfind,
    iterjson,
    iterdict,
)

from . import objectify
from . import dictify
from . import jsonify

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
    "StreamElement",
    "PullParser",
    "iterparse",
    "iterfind",
    "iterjson",
    "iterdict",
    "objectify",
    "dictify",
    "jsonify",
]
