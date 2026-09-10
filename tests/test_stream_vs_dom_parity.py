"""
TDD: jsonify.stream_dump must byte-for-byte match jsonify.dumps_file
for small XMLs, across edge cases (singular fields, arrays, nesting,
attrs, mixed content, compact + pretty).

dumps_file (DOM-based) is treated as the reference implementation: it
has no seek/patch trickery, so its formatting is trusted as "correct".
"""
import json
import os
import tempfile
import pytest

from pygixml import jsonify

CASES = {
    "single_scalar":        b"<root><a>1</a></root>",
    "two_scalars_no_list":  b"<root><a>1</a><b>2</b></root>",
    "simple_list":          b"<root><a>1</a><a>2</a></root>",
    "list_then_scalar":     b"<root><a>1</a><a>2</a><b>x</b></root>",
    "scalar_then_list":     b"<root><b>x</b><a>1</a><a>2</a></root>",
    "noncontig_list":       b"<root><a>1</a><b>x</b><a>2</a></root>",
    "three_way_interleave": b"<root><a>1</a><b>1</b><c>1</c><a>2</a><b>2</b></root>",
    "nested_object":        b"<root><a><x>1</x><y>2</y></a></root>",
    "nested_list_of_obj":   b"<root><rec><n>1</n></rec><rec><n>2</n></rec></root>",
    "attrs_only":           b'<root><a id="1">x</a></root>',
    "attrs_and_list":       b'<root><a id="1">x</a><a id="2">y</a></root>',
    "deep_nested_list":     b"<root><a><b><c>1</c><c>2</c></b></a></root>",
    "three_items":          b"<root><a>1</a><a>2</a><a>3</a></root>",
}


def _xml_path(tmp_path, name, content):
    p = tmp_path / f"{name}.xml"
    p.write_bytes(content)
    return str(p)


@pytest.mark.parametrize("name,xml", CASES.items())
@pytest.mark.parametrize("pretty,stream_indent,dom_indent", [
    (False, 0, ""),
    (True, 2, "  "),
])
def test_stream_dump_matches_dumps_file(tmp_path, name, xml, pretty, stream_indent, dom_indent):
    xml_path = _xml_path(tmp_path, name, xml)
    json_path = str(tmp_path / f"{name}.json")

    expected = jsonify.dumps_file(xml_path, pretty=pretty, indent=(dom_indent or "\t"))

    jsonify.stream_dump(xml_path, json_path, indent=stream_indent)
    with open(json_path, "r", encoding="utf-8") as f:
        got = f.read()

    # Structural equality (both must be valid, semantically identical JSON)
    assert json.loads(got) == json.loads(expected), (
        f"[{name} pretty={pretty}] parsed JSON differs\n"
        f" expected: {expected!r}\n got:      {got!r}"
    )

    # Byte-for-byte equality (formatting must match exactly, no stray
    # placeholder bytes, correct indentation on first array item, etc.)
    assert got == expected, (
        f"[{name} pretty={pretty}] formatting differs\n"
        f" expected: {expected!r}\n got:      {got!r}"
    )
