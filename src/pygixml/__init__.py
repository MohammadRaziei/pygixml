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
    PygiXMLHTMLError,
    html_to_xml,
    parse_html,
    xml_to_html,
    PygiXMLDiffError,
    diff,
    is_equal,
    signature,
    similarity,
    Insert,
    InsertText,
    Delete,
    Move,
    UpdateText,
    SetAttrib,
    DeleteAttrib,
)

from . import objectify
from . import dictify
from . import jsonify
from . import formats

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
    "PygiXMLHTMLError",
    "html_to_xml",
    "parse_html",
    "xml_to_html",
    "PygiXMLDiffError",
    "diff",
    "is_equal",
    "signature",
    "similarity",
    "Insert",
    "InsertText",
    "Delete",
    "Move",
    "UpdateText",
    "SetAttrib",
    "DeleteAttrib",
    "objectify",
    "dictify",
    "jsonify",
    "formats",
]
