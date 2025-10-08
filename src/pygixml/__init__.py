"""
pygixml - Python wrapper for pugixml using Cython

A fast and efficient XML parser and manipulator for Python.
"""

from .pygixml import (
    XMLDocument,
    XMLNode,
    XMLAttribute,
    parse_string,
    parse_file
)

__version__ = "0.1.0"
__all__ = [
    "XMLDocument",
    "XMLNode", 
    "XMLAttribute",
    "parse_string",
    "parse_file"
]
