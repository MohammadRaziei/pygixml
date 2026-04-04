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
    parse_string,
    parse_file,
    # Parse flags
    PARSE_MINIMAL,
    PARSE_PI,
    PARSE_COMMENTS,
    PARSE_CDATA,
    PARSE_WS_PCDATA,
    PARSE_ESCAPES,
    PARSE_EOL,
    PARSE_WCONV_ATTRIBUTE,
    PARSE_WNORM_ATTRIBUTE,
    PARSE_DECLARATION,
    PARSE_DOCTYPE,
    PARSE_WS_PCDATA_SINGLE,
    PARSE_TRIM_PCDATA,
    PARSE_FRAGMENT,
    PARSE_EMBED_PCDATA,
    PARSE_MERGE_PCDATA,
    PARSE_DEFAULT,
    PARSE_FULL,
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
    "parse_file",
    # Parse flags
    "PARSE_MINIMAL",
    "PARSE_PI",
    "PARSE_COMMENTS",
    "PARSE_CDATA",
    "PARSE_WS_PCDATA",
    "PARSE_ESCAPES",
    "PARSE_EOL",
    "PARSE_WCONV_ATTRIBUTE",
    "PARSE_WNORM_ATTRIBUTE",
    "PARSE_DECLARATION",
    "PARSE_DOCTYPE",
    "PARSE_WS_PCDATA_SINGLE",
    "PARSE_TRIM_PCDATA",
    "PARSE_FRAGMENT",
    "PARSE_EMBED_PCDATA",
    "PARSE_MERGE_PCDATA",
    "PARSE_DEFAULT",
    "PARSE_FULL",
]
