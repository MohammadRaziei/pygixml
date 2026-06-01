"""
pygixml.jsonify — direct XML → JSON serialization.

All heavy lifting is done in C++ (jsonify.pxi compiled into pygixml_cy.so).
No Python dict/list is allocated during traversal — only one str at the end.

Usage::

    from pygixml import jsonify

    # smart dispatcher — accepts str, file path, or ObjectifiedElement
    jsonify.dumps("<root/>")
    jsonify.dumps("data.xml")
    jsonify.dumps(root.user_profile)
    jsonify.dumps(root, pretty=True, indent="  ")
"""

from .pygixml_cy import (
    jsonify_dumps as dumps,
)

__all__ = ["dumps"]
