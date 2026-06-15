"""
Tests for pygixml.jsonify.xml_to_json_file — streaming XML → JSON conversion.

Run with:
    pytest tests/test_jsonify_stream.py -v
"""
import io
import json
import os
import tempfile

import pytest

from pygixml import jsonify


SAMPLE = b"""<?xml version="1.0"?>
<database version="1.0" owner="admin">
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
        <tags><tag>c++</tag></tags>
        <score>77</score>
    </record>
</database>"""


@pytest.fixture
def tmp_json(tmp_path):
    return str(tmp_path / "out.json")


def load(path):
    return json.loads(open(path).read())


# ---------------------------------------------------------------------------
# Mode A: record_tag
# ---------------------------------------------------------------------------

class TestModeA:
    def test_returns_record_count(self, tmp_json):
        n = jsonify.xml_to_json_file(SAMPLE, tmp_json, record_tag="record")
        assert n == 3

    def test_output_is_valid_json_array(self, tmp_json):
        jsonify.xml_to_json_file(SAMPLE, tmp_json, record_tag="record")
        data = load(tmp_json)
        assert isinstance(data, list)
        assert len(data) == 3

    def test_attributes_use_prefix(self, tmp_json):
        jsonify.xml_to_json_file(SAMPLE, tmp_json, record_tag="record")
        data = load(tmp_json)
        assert data[0]["@id"] == "1"
        assert data[0]["@active"] == "true"
        assert "@id" in data[1]

    def test_text_children_as_scalar(self, tmp_json):
        jsonify.xml_to_json_file(SAMPLE, tmp_json, record_tag="record")
        data = load(tmp_json)
        assert data[0]["name"] == "Ali Karimi"
        assert data[0]["city"] == "Tehran"
        assert data[0]["score"] == "42"

    def test_force_list_makes_single_child_a_list(self, tmp_json):
        jsonify.xml_to_json_file(SAMPLE, tmp_json, record_tag="record",
                                  force_list={"tag"})
        data = load(tmp_json)
        # record[2] has only one <tag> — force_list ensures it's still a list
        assert isinstance(data[2]["tags"]["tag"], list)
        assert data[2]["tags"]["tag"] == ["c++"]

    def test_multiple_siblings_auto_list(self, tmp_json):
        jsonify.xml_to_json_file(SAMPLE, tmp_json, record_tag="record")
        data = load(tmp_json)
        # record[0] has two <tag> siblings — must be a list without force_list
        assert isinstance(data[0]["tags"]["tag"], list)
        assert data[0]["tags"]["tag"] == ["python", "xml"]

    def test_order_preserved(self, tmp_json):
        jsonify.xml_to_json_file(SAMPLE, tmp_json, record_tag="record")
        data = load(tmp_json)
        assert [r["@id"] for r in data] == ["1", "2", "3"]

    def test_custom_attr_prefix(self, tmp_json):
        jsonify.xml_to_json_file(SAMPLE, tmp_json, record_tag="record",
                                  attr_prefix="_")
        data = load(tmp_json)
        assert "_id" in data[0]
        assert "@id" not in data[0]

    def test_no_attr_prefix(self, tmp_json):
        jsonify.xml_to_json_file(SAMPLE, tmp_json, record_tag="record",
                                  attr_prefix="")
        data = load(tmp_json)
        assert "id" in data[0]

    def test_pretty_produces_indented_json(self, tmp_json):
        jsonify.xml_to_json_file(SAMPLE, tmp_json, record_tag="record",
                                  pretty=True, indent="  ")
        raw = open(tmp_json).read()
        assert "\n" in raw
        assert "  " in raw
        # still valid
        data = json.loads(raw)
        assert len(data) == 3

    def test_no_record_tag_match_writes_empty_array(self, tmp_json):
        n = jsonify.xml_to_json_file(SAMPLE, tmp_json, record_tag="nonexistent")
        assert n == 0
        data = load(tmp_json)
        assert data == []


# ---------------------------------------------------------------------------
# Mode B: no record_tag (root element wraps children)
# ---------------------------------------------------------------------------

class TestModeB:
    def test_returns_child_count(self, tmp_json):
        n = jsonify.xml_to_json_file(SAMPLE, tmp_json)
        assert n == 3

    def test_output_is_valid_json_object(self, tmp_json):
        jsonify.xml_to_json_file(SAMPLE, tmp_json)
        data = load(tmp_json)
        assert isinstance(data, dict)

    def test_root_tag_is_top_level_key(self, tmp_json):
        jsonify.xml_to_json_file(SAMPLE, tmp_json)
        data = load(tmp_json)
        assert "database" in data

    def test_root_attributes_preserved(self, tmp_json):
        jsonify.xml_to_json_file(SAMPLE, tmp_json)
        data = load(tmp_json)
        assert data["@version"] == "1.0"
        assert data["@owner"] == "admin"

    def test_children_are_array_under_root_key(self, tmp_json):
        jsonify.xml_to_json_file(SAMPLE, tmp_json)
        data = load(tmp_json)
        assert isinstance(data["database"], list)
        assert len(data["database"]) == 3

    def test_children_content(self, tmp_json):
        jsonify.xml_to_json_file(SAMPLE, tmp_json)
        data = load(tmp_json)
        r = data["database"][0]
        assert r["@id"] == "1"
        assert r["name"] == "Ali Karimi"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_root_element(self, tmp_json):
        n = jsonify.xml_to_json_file(b"<root/>", tmp_json)
        assert n == 0
        data = load(tmp_json)
        assert data == {"root": []}

    def test_root_with_no_children_text_only(self, tmp_json):
        # text-only root direct children
        jsonify.xml_to_json_file(b"<root><item>hello</item></root>", tmp_json)
        data = load(tmp_json)
        assert data["root"] == ["hello"]

    def test_element_with_attributes_and_text(self, tmp_json):
        xml = b'<root><a x="1">text</a></root>'
        jsonify.xml_to_json_file(xml, tmp_json, pretty=True)
        data = load(tmp_json)
        a = data["root"][0]
        assert a["@x"] == "1"
        assert a["#text"] == "text"

    def test_custom_cdata_key(self, tmp_json):
        xml = b'<root><a x="1">text</a></root>'
        jsonify.xml_to_json_file(xml, tmp_json, cdata_key="_value")
        data = load(tmp_json)
        a = data["root"][0]
        assert a["_value"] == "text"

    def test_nested_hierarchy(self, tmp_json):
        xml = b"""<root>
            <a><b><c>deep</c></b></a>
        </root>"""
        jsonify.xml_to_json_file(xml, tmp_json)
        data = load(tmp_json)
        assert data["root"][0]["b"]["c"] == "deep"

    def test_entities_decoded(self, tmp_json):
        xml = b"<root><item>Tom &amp; Jerry &lt;3&gt;</item></root>"
        jsonify.xml_to_json_file(xml, tmp_json)
        data = load(tmp_json)
        assert data["root"][0] == "Tom & Jerry <3>"

    def test_unicode_content(self, tmp_json):
        xml = "<root><item>سلام دنیا</item></root>".encode("utf-8")
        jsonify.xml_to_json_file(xml, tmp_json, encoding="utf-8")
        data = load(tmp_json)
        assert data["root"][0] == "سلام دنیا"

    def test_pretty_output_is_valid_json(self, tmp_json):
        jsonify.xml_to_json_file(SAMPLE, tmp_json, pretty=True)
        data = json.loads(open(tmp_json).read())
        assert "database" in data


# ---------------------------------------------------------------------------
# Source types
# ---------------------------------------------------------------------------

class TestSourceTypes:
    def test_bytes_source(self, tmp_json):
        n = jsonify.xml_to_json_file(SAMPLE, tmp_json, record_tag="record")
        assert n == 3

    def test_bytearray_source(self, tmp_json):
        n = jsonify.xml_to_json_file(bytearray(SAMPLE), tmp_json, record_tag="record")
        assert n == 3

    def test_bytesio_source(self, tmp_json):
        n = jsonify.xml_to_json_file(io.BytesIO(SAMPLE), tmp_json, record_tag="record")
        assert n == 3

    def test_file_path_string(self, tmp_path, tmp_json):
        xml_file = str(tmp_path / "in.xml")
        open(xml_file, "wb").write(SAMPLE)
        n = jsonify.xml_to_json_file(xml_file, tmp_json, record_tag="record")
        assert n == 3

    def test_pathlib_path(self, tmp_path, tmp_json):
        xml_file = tmp_path / "in.xml"
        xml_file.write_bytes(SAMPLE)
        n = jsonify.xml_to_json_file(xml_file, tmp_json, record_tag="record")
        assert n == 3


# ---------------------------------------------------------------------------
# Large document / performance smoke test
# ---------------------------------------------------------------------------

class TestLargeDocument:
    def test_100k_records(self, tmp_json):
        N = 100_000
        parts = [b"<root>"]
        for i in range(N):
            parts.append(
                f'<record id="{i}"><name>User{i}</name>'
                f'<tags><tag>a</tag><tag>b</tag></tags></record>'.encode()
            )
        parts.append(b"</root>")
        xml = b"".join(parts)

        n = jsonify.xml_to_json_file(xml, tmp_json, record_tag="record",
                                      force_list={"tag"})
        assert n == N

        data = json.loads(open(tmp_json).read())
        assert len(data) == N
        assert data[0]["@id"] == "0"
        assert data[-1]["@id"] == str(N - 1)
        assert data[5]["tags"]["tag"] == ["a", "b"]

    def test_output_file_overwritten_on_second_call(self, tmp_json):
        jsonify.xml_to_json_file(b"<root><a>1</a></root>", tmp_json)
        jsonify.xml_to_json_file(b"<root><b>2</b></root>", tmp_json)
        data = load(tmp_json)
        assert "root" in data
        # only second run's content
        assert data["root"] == ["2"]
