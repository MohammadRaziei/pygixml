"""
pygixml.objectify — lxml.objectify-style interface.

All logic and cdef classes live in objectify.pxi which is compiled
directly into pygixml_cy.so via ``include "objectify.pxi"`` at the
end of pygixml_cy.pyx.

This module is a pure re-export shim so users can write:

    from pygixml import objectify
    root = objectify.from_string(xml)
    root = objectify.from_file(path)
"""

from .pygixml_cy import (
    ObjectifiedElement,
    NodeSequence,
    objectify_from_string as from_string,
    objectify_from_file   as from_file,
)

__all__ = [
    "ObjectifiedElement",
    "NodeSequence",
    "from_string",
    "from_file",
]