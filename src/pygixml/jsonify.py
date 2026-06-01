"""
pygixml.jsonify — direct XML → JSON serialization.

All heavy lifting is done in C++ (jsonify.pxi compiled into pygixml_cy.so).
No Python dict/list is allocated during traversal — only one str at the end.

Usage::

    from pygixml import jsonify

    # From XML string
    json_str = jsonify.dumps(xml)
    json_str = jsonify.dumps(xml, pretty=True, indent="  ")
    json_str = jsonify.dumps(xml, force_list={"item"})

    # From XML file
    json_str = jsonify.dumps_file("data.xml")

    # From an already-parsed ObjectifiedElement (subtree)
    root = objectify.from_string(xml)
    json_str = jsonify.dumps_node(root.user_profile)
"""

from .pygixml_cy import (
    jsonify_dumps       as dumps,
    jsonify_dumps_file  as dumps_file,
    jsonify_dumps_node  as dumps_node,
)

__all__ = ["dumps", "dumps_file", "dumps_node"]
