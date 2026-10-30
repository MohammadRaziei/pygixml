"""Regression tests for the streaming fast paths (C text buffers in PullParser,
no-escape fast path in to_json, stream_dump's append-without-seek writer)."""
import json

import pygixml
from pygixml import jsonify


def test_to_json_escapes_every_special_character():
    e = pygixml.StreamElement("a")
    e.text = 'x\x01y\x1f"\\\t\n\r\u00e9\u4e2d'
    assert json.loads(e.to_json()) == e.text


def test_to_json_plain_string_untouched():
    e = pygixml.StreamElement("a")
    e.text = "plain text"
    assert e.to_json() == '"plain text"'


def test_iterparse_chunk_boundaries_inside_multibyte_text():
    xml = '<r a="caf\u00e9\U0001F600"><x>\u4e2d\u6587 &amp; <![CDATA[<raw>]]> t</x></r>'.encode()
    want = [(el.tag, dict(el.attrib), el.text) for _, el in pygixml.iterparse(xml)]
    for size in (1, 2, 3, 5):
        got = [(el.tag, dict(el.attrib), el.text) for _, el in pygixml.iterparse(xml, chunk_size=size)]
        assert got == want


def test_iterparse_skipped_subtrees_build_nothing_but_still_validate():
    xml = b"<r><skip><deep>text</deep></skip><item>1</item><skip>t</skip><item>2</item></r>"
    assert [e.text for e in pygixml.iterfind(xml, "item")] == ["1", "2"]


def test_stream_dump_interleaved_matches_dumps(tmp_path):
    xml = "<r>" + "".join(f'<a x="{i}">{i}</a><b>t{i}<c>{i}</c></b>' for i in range(300)) + "<a>last</a></r>"
    src, out = tmp_path / "in.xml", tmp_path / "out.json"
    src.write_text(xml)
    jsonify.stream_dump(str(src), str(out))
    assert json.loads(out.read_text()) == json.loads(jsonify.dumps(xml))


def test_stream_dump_indent_is_valid_json(tmp_path):
    src, out = tmp_path / "in.xml", tmp_path / "out.json"
    src.write_text("<r><a>1</a><b>2</b><a>3</a><a>4</a></r>")
    jsonify.stream_dump(str(src), str(out), indent=2)
    assert json.loads(out.read_text()) == {"r": {"a": ["1", "3", "4"], "b": "2"}}
