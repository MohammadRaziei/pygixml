"""
pygixml.jsonify — direct XML → JSON serialization.

All heavy lifting is done in C++ (jsonify.pxi compiled into pygixml_cy.so).
No Python dict/list is allocated during traversal — only one str at the end
(or, for the streaming entry point below, not even that).

Usage::

    from pygixml import jsonify

    # smart dispatcher — str or ObjectifiedElement or XMLNode
    jsonify.dumps("<root/>")
    jsonify.dumps(root.user_profile)          # ObjectifiedElement
    jsonify.dumps(doc.root)                   # XMLNode

    # typed entry points
    jsonify.dumps_str("<root/>")
    jsonify.dumps_file("data.xml")
    jsonify.dumps_obj(root.user_profile)
    jsonify.dumps_node(doc.root)

    # options
    jsonify.dumps(xml, pretty=True, indent="  ", encoding="utf-8")
    jsonify.dumps(xml, attr_prefix="", cdata_key="text")
    jsonify.dumps(xml, force_list={"item"})

    # streaming, constant-memory conversion for gigantic files:
    # pure C++ (yxml + hand-written JSON writer) — no pugixml DOM, no
    # Python dict/list, no `json` module, anywhere in the call chain.

    # -> JSON Lines (one record per line; fastest, truly O(depth) memory)
    jsonify.stream_xml_to_json("huge.xml", "huge.jsonl", record_tag="record")

    # -> a single standard, valid JSON document (same shape as dumps()),
    #    using an in-place seek-and-patch trick to avoid buffering whole
    #    subtrees just to know where array brackets go
    jsonify.stream_dump("huge.xml", "huge.json", pretty=True)
"""

from .pygixml_cy import (
    jsonify_dumps      as dumps,
    jsonify_dumps_str  as dumps_str,
    jsonify_dumps_file as dumps_file,
    jsonify_dumps_obj  as dumps_obj,
    jsonify_dumps_node as dumps_node,
    stream_xml_to_json,
    jsonify_stream_dump as stream_dump,
)

__all__ = [
    "dumps", "dumps_str", "dumps_file", "dumps_obj", "dumps_node",
    "stream_xml_to_json", "stream_dump",
]
