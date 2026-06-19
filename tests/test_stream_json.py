"""
Tests for StreamElement.to_dict()/to_json() and the pygixml.iterjson /
pygixml.iterdict generators built on top of them.

These all sit on top of the already-tested iterfind/iterparse (yxml-backed
streaming parser, see test_stream.py) -- this file focuses on the
dict/JSON conversion layer itself: convention parity with jsonify.dumps,
to_dict/to_json consistency, and generator behavior.

Run with:
    pytest tests/test_stream_json.py -v
"""
import json

import pytest

import pygixml
from pygixml import jsonify


SAMPLE = b"""<database>
    <record id="1" active="true">
        <name>Ali Karimi</name>
        <city>Tehran</city>
        <tags><tag>python</tag><tag>xml</tag></tags>
        <score>42</score>
    </record>
    <record id="2">
        <name>Sara Mohammadi</name>
        <city>Shiraz</city>
        <tags><tag>json</tag></tags>
        <score>99</score>
    </record>
    <record id="3">
        <name>Reza Ahmadi</name>
        <city>Isfahan</city>
        <tags><tag>c++</tag><tag>rust</tag></tags>
        <score>77</score>
    </record>
</database>"""


def first_record(xml=SAMPLE, **kw):
    return next(pygixml.iterfind(xml, "record", **kw))


# ---------------------------------------------------------------------------
# StreamElement.to_dict()
# ---------------------------------------------------------------------------

class TestToDict:
    def test_basic_fields(self):
        rec = first_record()
        d = rec.to_dict()
        assert d["@id"] == "1"
        assert d["@active"] == "true"
        assert d["name"] == "Ali Karimi"
        assert d["city"] == "Tehran"
        assert d["score"] == "42"

    def test_repeated_children_become_list(self):
        rec = first_record()
        d = rec.to_dict()
        assert d["tags"]["tag"] == ["python", "xml"]

    def test_single_child_is_scalar_without_force_list(self):
        records = list(pygixml.iterfind(SAMPLE, "record"))
        d = records[1].to_dict()  # only one <tag>
        assert d["tags"]["tag"] == "json"

    def test_force_list_set(self):
        records = list(pygixml.iterfind(SAMPLE, "record"))
        d = records[1].to_dict(force_list={"tag"})
        assert d["tags"]["tag"] == ["json"]

    def test_force_list_true_forces_everything(self):
        rec = first_record()
        d = rec.to_dict(force_list=True)
        assert isinstance(d["name"], list)
        assert d["name"] == ["Ali Karimi"]

    def test_custom_attr_prefix(self):
        rec = first_record()
        d = rec.to_dict(attr_prefix="_")
        assert d["_id"] == "1"
        assert "@id" not in d

    def test_custom_cdata_key(self):
        elem = next(pygixml.iterfind(b"<root><a id='1'>hi</a></root>", "a"))
        d = elem.to_dict(cdata_key="_value")
        assert d == {"@id": "1", "_value": "hi"}

    def test_scalar_shortcut_no_attrs_no_children(self):
        elem = next(pygixml.iterfind(b"<root><a>solo</a></root>", "a"))
        assert elem.to_dict() == "solo"

    def test_empty_element_is_none(self):
        elem = next(pygixml.iterfind(b"<root><a/></root>", "a"))
        assert elem.to_dict() == {}.get("missing")  # i.e. None
        assert elem.to_dict() is None

    def test_nested_objects(self):
        elem = next(pygixml.iterfind(b"<root><a><b><c>deep</c></b></a></root>", "a"))
        assert elem.to_dict() == {"b": {"c": "deep"}}

    def test_does_not_self_wrap_with_own_tag(self):
        # unlike jsonify.dumps_node, to_dict() on <record> does NOT wrap
        # the result as {"record": {...}} -- it returns the content directly
        rec = first_record()
        d = rec.to_dict()
        assert "record" not in d


# ---------------------------------------------------------------------------
# StreamElement.to_json()
# ---------------------------------------------------------------------------

class TestToJson:
    def test_returns_str(self):
        rec = first_record()
        assert isinstance(rec.to_json(), str)

    def test_valid_json(self):
        rec = first_record()
        json.loads(rec.to_json())  # must not raise

    def test_matches_to_dict(self):
        rec = first_record()
        assert json.loads(rec.to_json()) == rec.to_dict()

    def test_matches_to_dict_with_force_list(self):
        records = list(pygixml.iterfind(SAMPLE, "record"))
        rec = records[1]
        assert json.loads(rec.to_json(force_list={"tag"})) == rec.to_dict(force_list={"tag"})

    def test_matches_to_dict_with_custom_prefix_and_key(self):
        elem = next(pygixml.iterfind(b"<root><a id='1'>hi</a></root>", "a"))
        j = elem.to_json(attr_prefix="_", cdata_key="_v")
        d = elem.to_dict(attr_prefix="_", cdata_key="_v")
        assert json.loads(j) == d

    def test_special_characters_escaped(self):
        xml = '<root><a>Tom &amp; Jerry "quoted" back\\slash \u0633\u0644\u0627\u0645</a></root>'
        elem = next(pygixml.iterfind(xml.encode("utf-8"), "a"))
        j = elem.to_json()
        assert json.loads(j) == elem.to_dict()
        assert json.loads(j) == 'Tom & Jerry "quoted" back\\slash \u0633\u0644\u0627\u0645'

    def test_no_self_wrap(self):
        rec = first_record()
        data = json.loads(rec.to_json())
        assert "record" not in data

    def test_matches_jsonify_dumps_node_unwrapped(self):
        # Convention parity check against the pugixml-DOM-based serializer:
        # to_json() on an element should equal dumps_node()'s output for
        # that same element, once you strip dumps_node's self-wrapper.
        xml_str = SAMPLE.decode("utf-8")
        doc = pygixml.parse_string(xml_str)
        first_dom_record = doc.root.child("record")
        dom_json = jsonify.dumps_node(first_dom_record)
        dom_parsed = json.loads(dom_json)["record"]

        stream_rec = first_record()
        stream_parsed = json.loads(stream_rec.to_json())

        assert stream_parsed == dom_parsed


# ---------------------------------------------------------------------------
# pygixml.iterjson
# ---------------------------------------------------------------------------

class TestIterjson:
    def test_is_generator(self):
        gen = pygixml.iterjson(SAMPLE, "record")
        assert hasattr(gen, "__next__")
        assert hasattr(gen, "__iter__")

    def test_yields_strings(self):
        for line in pygixml.iterjson(SAMPLE, "record"):
            assert isinstance(line, str)

    def test_yields_valid_json_per_record(self):
        count = 0
        for line in pygixml.iterjson(SAMPLE, "record"):
            json.loads(line)
            count += 1
        assert count == 3

    def test_does_not_write_any_file(self, tmp_path, monkeypatch):
        # sanity: consuming the generator must not touch the filesystem
        # for output -- only reads the input file/bytes.
        before = set(tmp_path.iterdir())
        list(pygixml.iterjson(SAMPLE, "record"))
        after = set(tmp_path.iterdir())
        assert before == after

    def test_content_matches_to_json(self):
        lines = list(pygixml.iterjson(SAMPLE, "record"))
        direct = [rec.to_json() for rec in pygixml.iterfind(SAMPLE, "record")]
        assert lines == direct

    def test_force_list(self):
        lines = list(pygixml.iterjson(SAMPLE, "record", force_list={"tag"}))
        parsed = [json.loads(l) for l in lines]
        # record 2 has only one <tag> -- force_list keeps it a list
        assert parsed[1]["tags"]["tag"] == ["json"]

    def test_custom_attr_prefix_and_cdata_key(self):
        xml = b"<root><a id='1'>hi</a><a id='2'>bye</a></root>"
        lines = list(pygixml.iterjson(xml, "a", attr_prefix="_", cdata_key="_v"))
        parsed = [json.loads(l) for l in lines]
        assert parsed[0] == {"_id": "1", "_v": "hi"}
        assert parsed[1] == {"_id": "2", "_v": "bye"}

    def test_empty_when_no_match(self):
        assert list(pygixml.iterjson(SAMPLE, "nonexistent")) == []

    def test_file_path_source(self, tmp_path):
        p = tmp_path / "data.xml"
        p.write_bytes(SAMPLE)
        lines = list(pygixml.iterjson(str(p), "record"))
        assert len(lines) == 3
        for line in lines:
            json.loads(line)


# ---------------------------------------------------------------------------
# pygixml.iterdict
# ---------------------------------------------------------------------------

class TestIterdict:
    def test_yields_dicts(self):
        for d in pygixml.iterdict(SAMPLE, "record"):
            assert isinstance(d, dict)

    def test_count_and_content(self):
        records = list(pygixml.iterdict(SAMPLE, "record"))
        assert len(records) == 3
        assert records[0]["@id"] == "1"
        assert records[0]["name"] == "Ali Karimi"
        assert records[2]["tags"]["tag"] == ["c++", "rust"]

    def test_matches_to_dict(self):
        dicts = list(pygixml.iterdict(SAMPLE, "record"))
        direct = [rec.to_dict() for rec in pygixml.iterfind(SAMPLE, "record")]
        assert dicts == direct

    def test_force_list(self):
        records = list(pygixml.iterdict(SAMPLE, "record", force_list={"tag"}))
        assert records[1]["tags"]["tag"] == ["json"]

    def test_iterjson_and_iterdict_agree(self):
        jsons = [json.loads(s) for s in pygixml.iterjson(SAMPLE, "record")]
        dicts = list(pygixml.iterdict(SAMPLE, "record"))
        assert jsons == dicts


# ---------------------------------------------------------------------------
# Large-ish document smoke test (constant-memory-ish per-record model)
# ---------------------------------------------------------------------------

class TestLargeDocument:
    def test_many_records_iterjson(self):
        n = 5000
        parts = [b"<root>"]
        for i in range(n):
            parts.append(f'<item id="{i}"><name>Item {i}</name></item>'.encode())
        parts.append(b"</root>")
        data = b"".join(parts)

        count = 0
        total = 0
        for line in pygixml.iterjson(data, "item"):
            d = json.loads(line)
            count += 1
            total += int(d["@id"])

        assert count == n
        assert total == sum(range(n))

    def test_many_records_iterdict(self):
        n = 5000
        parts = [b"<root>"]
        for i in range(n):
            parts.append(f'<item id="{i}"/>'.encode())
        parts.append(b"</root>")
        data = b"".join(parts)

        ids = [int(d["@id"]) for d in pygixml.iterdict(data, "item")]
        assert ids == list(range(n))
