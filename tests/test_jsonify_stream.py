"""
Tests for pygixml.jsonify.stream_xml_to_json — constant-memory streaming
XML -> JSON Lines conversion, implemented entirely in C++ (jsonify.pxi).

No Python dict/list is ever built for document content, and the `json`
module is never imported on the write path — every byte of output JSON
is hand-emitted in C++. Output is JSON Lines (one record per line),
which is what makes constant-memory operation possible at all.

Run with:
    pytest tests/test_jsonify_stream.py -v
"""
import json
import os

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
def xml_path(tmp_path):
    p = tmp_path / "in.xml"
    p.write_bytes(SAMPLE)
    return str(p)


@pytest.fixture
def jsonl_path(tmp_path):
    return str(tmp_path / "out.jsonl")


def write_xml(tmp_path, content, name="in.xml"):
    p = tmp_path / name
    if isinstance(content, str):
        content = content.encode("utf-8")
    p.write_bytes(content)
    return str(p)


def read_lines(path):
    """Read a JSONL file, returning a list of parsed JSON objects
    (skipping blank trailing lines)."""
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


# ---------------------------------------------------------------------------
# Mode A: record_tag given
# ---------------------------------------------------------------------------

class TestModeARecordTag:
    def test_returns_record_count(self, xml_path, jsonl_path):
        n = jsonify.stream_xml_to_json(xml_path, jsonl_path, record_tag="record")
        assert n == 3

    def test_output_is_valid_jsonl(self, xml_path, jsonl_path):
        jsonify.stream_xml_to_json(xml_path, jsonl_path, record_tag="record")
        records = read_lines(jsonl_path)
        assert len(records) == 3

    def test_attributes_use_prefix(self, xml_path, jsonl_path):
        jsonify.stream_xml_to_json(xml_path, jsonl_path, record_tag="record")
        records = read_lines(jsonl_path)
        assert records[0]["@id"] == "1"
        assert records[0]["@active"] == "true"
        assert "@id" in records[1]

    def test_text_children_as_scalar(self, xml_path, jsonl_path):
        jsonify.stream_xml_to_json(xml_path, jsonl_path, record_tag="record")
        records = read_lines(jsonl_path)
        assert records[0]["name"] == "Ali Karimi"
        assert records[0]["city"] == "Tehran"
        assert records[0]["score"] == "42"

    def test_force_list_set_forces_array(self, xml_path, jsonl_path):
        jsonify.stream_xml_to_json(xml_path, jsonl_path, record_tag="record",
                                    force_list={"tag"})
        records = read_lines(jsonl_path)
        # record[2] has only one <tag> sibling -- force_list keeps it a list
        assert records[2]["tags"]["tag"] == ["c++"]

    def test_multiple_siblings_auto_array_without_force_list(self, xml_path, jsonl_path):
        jsonify.stream_xml_to_json(xml_path, jsonl_path, record_tag="record")
        records = read_lines(jsonl_path)
        assert records[0]["tags"]["tag"] == ["python", "xml"]

    def test_single_sibling_without_force_list_is_scalar(self, xml_path, jsonl_path):
        jsonify.stream_xml_to_json(xml_path, jsonl_path, record_tag="record")
        records = read_lines(jsonl_path)
        # record[2] has exactly one <tag> -- without force_list it's a
        # plain (non-array) value
        assert records[2]["tags"]["tag"] == "c++"

    def test_force_list_true_forces_every_tag(self, tmp_path):
        xf = write_xml(tmp_path, b"<root><record id='1'><tag>a</tag></record></root>")
        jf = str(tmp_path / "out.jsonl")
        jsonify.stream_xml_to_json(xf, jf, record_tag="record", force_list=True)
        records = read_lines(jf)
        assert records[0]["tag"] == ["a"]

    def test_order_preserved(self, xml_path, jsonl_path):
        jsonify.stream_xml_to_json(xml_path, jsonl_path, record_tag="record")
        records = read_lines(jsonl_path)
        assert [r["@id"] for r in records] == ["1", "2", "3"]

    def test_custom_attr_prefix(self, xml_path, jsonl_path):
        jsonify.stream_xml_to_json(xml_path, jsonl_path, record_tag="record",
                                    attr_prefix="_")
        records = read_lines(jsonl_path)
        assert "_id" in records[0]
        assert "@id" not in records[0]

    def test_no_attr_prefix(self, xml_path, jsonl_path):
        jsonify.stream_xml_to_json(xml_path, jsonl_path, record_tag="record",
                                    attr_prefix="")
        records = read_lines(jsonl_path)
        assert "id" in records[0]

    def test_custom_cdata_key(self, tmp_path):
        xf = write_xml(tmp_path, b'<root><record id="1">hello</record></root>')
        jf = str(tmp_path / "out.jsonl")
        jsonify.stream_xml_to_json(xf, jf, record_tag="record", cdata_key="_value")
        records = read_lines(jf)
        assert records[0]["_value"] == "hello"

    def test_no_matching_record_tag_writes_nothing(self, xml_path, jsonl_path):
        n = jsonify.stream_xml_to_json(xml_path, jsonl_path, record_tag="nonexistent")
        assert n == 0
        assert read_lines(jsonl_path) == []

    def test_returns_int(self, xml_path, jsonl_path):
        n = jsonify.stream_xml_to_json(xml_path, jsonl_path, record_tag="record")
        assert isinstance(n, int)


# ---------------------------------------------------------------------------
# Mode B: no record_tag (direct children of root)
# ---------------------------------------------------------------------------

class TestModeBNoRecordTag:
    def test_returns_child_count(self, xml_path, jsonl_path):
        n = jsonify.stream_xml_to_json(xml_path, jsonl_path)
        assert n == 3

    def test_each_child_is_one_line(self, xml_path, jsonl_path):
        jsonify.stream_xml_to_json(xml_path, jsonl_path)
        records = read_lines(jsonl_path)
        assert len(records) == 3
        assert records[0]["@id"] == "1"
        assert records[0]["name"] == "Ali Karimi"


# ---------------------------------------------------------------------------
# Nested record_tag occurrences
# ---------------------------------------------------------------------------

class TestNestedRecordTag:
    def test_nested_same_tag_not_double_counted(self, tmp_path):
        xf = write_xml(
            tmp_path,
            b'<root><record id="1">'
            b'<record id="2"><name>nested</name></record>'
            b'</record></root>',
        )
        jf = str(tmp_path / "out.jsonl")
        n = jsonify.stream_xml_to_json(xf, jf, record_tag="record")
        assert n == 1  # only the OUTER record is a top-level entry
        records = read_lines(jf)
        outer = records[0]
        assert outer["@id"] == "1"
        assert outer["record"]["@id"] == "2"
        assert outer["record"]["name"] == "nested"

    def test_sibling_records_after_nested_one(self, tmp_path):
        xf = write_xml(
            tmp_path,
            b'<root>'
            b'<record id="1"><record id="2"><x>a</x></record></record>'
            b'<record id="3"><x>b</x></record>'
            b'</root>',
        )
        jf = str(tmp_path / "out.jsonl")
        n = jsonify.stream_xml_to_json(xf, jf, record_tag="record")
        assert n == 2
        records = read_lines(jf)
        assert records[0]["@id"] == "1"
        assert records[1]["@id"] == "3"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_record_self_closing(self, tmp_path):
        xf = write_xml(tmp_path, b'<root><record id="1"/></root>')
        jf = str(tmp_path / "out.jsonl")
        n = jsonify.stream_xml_to_json(xf, jf, record_tag="record")
        assert n == 1
        records = read_lines(jf)
        assert records[0] == {"@id": "1"}

    def test_empty_record_open_close(self, tmp_path):
        xf = write_xml(tmp_path, b'<root><record id="1"></record></root>')
        jf = str(tmp_path / "out.jsonl")
        jsonify.stream_xml_to_json(xf, jf, record_tag="record")
        records = read_lines(jf)
        assert records[0] == {"@id": "1"}

    def test_no_attributes_no_children_pure_text(self, tmp_path):
        xf = write_xml(tmp_path, b"<root><record>just text</record></root>")
        jf = str(tmp_path / "out.jsonl")
        jsonify.stream_xml_to_json(xf, jf, record_tag="record")
        records = read_lines(jf)
        assert records[0] == "just text"

    def test_mixed_text_and_attributes(self, tmp_path):
        xf = write_xml(tmp_path, b'<root><record id="1">hello world</record></root>')
        jf = str(tmp_path / "out.jsonl")
        jsonify.stream_xml_to_json(xf, jf, record_tag="record")
        records = read_lines(jf)
        assert records[0] == {"@id": "1", "#text": "hello world"}

    def test_nested_object_hierarchy(self, tmp_path):
        xf = write_xml(
            tmp_path,
            b"<root><record><a><b><c>deep</c></b></a></record></root>",
        )
        jf = str(tmp_path / "out.jsonl")
        jsonify.stream_xml_to_json(xf, jf, record_tag="record")
        records = read_lines(jf)
        assert records[0]["a"]["b"]["c"] == "deep"

    def test_entities_decoded(self, tmp_path):
        xf = write_xml(
            tmp_path,
            b"<root><record><note>Tom &amp; Jerry &lt;3&gt;</note></record></root>",
        )
        jf = str(tmp_path / "out.jsonl")
        jsonify.stream_xml_to_json(xf, jf, record_tag="record")
        records = read_lines(jf)
        assert records[0]["note"] == "Tom & Jerry <3>"

    def test_unicode_content(self, tmp_path):
        xf = write_xml(tmp_path, "<root><record><note>سلام دنیا</note></record></root>")
        jf = str(tmp_path / "out.jsonl")
        jsonify.stream_xml_to_json(xf, jf, record_tag="record")
        records = read_lines(jf)
        assert records[0]["note"] == "سلام دنیا"

    def test_special_chars_in_attribute_values(self, tmp_path):
        xf = write_xml(tmp_path, b'<root><record x="a &quot;quoted&quot; b"/></root>')
        jf = str(tmp_path / "out.jsonl")
        jsonify.stream_xml_to_json(xf, jf, record_tag="record")
        records = read_lines(jf)
        assert records[0]["@x"] == 'a "quoted" b'

    def test_backslash_in_text(self, tmp_path):
        xf = write_xml(tmp_path, b"<root><record><note>back\\slash</note></record></root>")
        jf = str(tmp_path / "out.jsonl")
        jsonify.stream_xml_to_json(xf, jf, record_tag="record")
        records = read_lines(jf)
        assert records[0]["note"] == "back\\slash"

    def test_newline_in_attribute_decoded(self, tmp_path):
        xf = write_xml(tmp_path, b'<root><record x="line1&#10;line2"/></root>')
        jf = str(tmp_path / "out.jsonl")
        jsonify.stream_xml_to_json(xf, jf, record_tag="record")
        records = read_lines(jf)
        assert records[0]["@x"] == "line1\nline2"

    def test_overwrites_existing_output_file(self, tmp_path):
        xf1 = write_xml(tmp_path, b"<root><record><a>1</a></record></root>", "a.xml")
        xf2 = write_xml(tmp_path, b"<root><record><b>2</b></record></root>", "b.xml")
        jf = str(tmp_path / "out.jsonl")
        jsonify.stream_xml_to_json(xf1, jf, record_tag="record")
        jsonify.stream_xml_to_json(xf2, jf, record_tag="record")
        records = read_lines(jf)
        assert len(records) == 1
        assert records[0] == {"b": "2"}


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrors:
    def test_missing_input_file_raises(self, tmp_path):
        jf = str(tmp_path / "out.jsonl")
        with pytest.raises(Exception):
            jsonify.stream_xml_to_json(str(tmp_path / "nope.xml"), jf)

    def test_malformed_xml_raises(self, tmp_path):
        xf = write_xml(tmp_path, b"<root><record><a></record></root>")  # mismatched
        jf = str(tmp_path / "out.jsonl")
        with pytest.raises(Exception):
            jsonify.stream_xml_to_json(xf, jf, record_tag="record")

    def test_unclosed_tag_raises(self, tmp_path):
        xf = write_xml(tmp_path, b"<root><record><a>text</record></root>")
        jf = str(tmp_path / "out.jsonl")
        with pytest.raises(Exception):
            jsonify.stream_xml_to_json(xf, jf, record_tag="record")


# ---------------------------------------------------------------------------
# Large document / constant-memory smoke tests
# ---------------------------------------------------------------------------

class TestLargeDocument:
    def test_many_records(self, tmp_path):
        n_records = 50_000
        xf = tmp_path / "big.xml"
        with open(xf, "w") as f:
            f.write("<root>\n")
            for i in range(n_records):
                f.write(
                    f'<record id="{i}"><name>User{i}</name>'
                    f'<tags><tag>a</tag><tag>b</tag></tags></record>\n'
                )
            f.write("</root>\n")

        jf = str(tmp_path / "out.jsonl")
        n = jsonify.stream_xml_to_json(str(xf), jf, record_tag="record",
                                        force_list={"tag"})
        assert n == n_records

        records = read_lines(jf)
        assert len(records) == n_records
        assert records[0]["@id"] == "0"
        assert records[-1]["@id"] == str(n_records - 1)
        assert records[5]["tags"]["tag"] == ["a", "b"]

    def test_single_record_with_many_children(self, tmp_path):
        # A single record with a large number of repeated child elements --
        # this exercises the two-pass count+emit path within ONE record,
        # which must not buffer the whole subtree.
        n_items = 50_000
        xf = tmp_path / "one_big_record.xml"
        with open(xf, "w") as f:
            f.write('<root><record id="1">')
            for i in range(n_items):
                f.write(f"<item>{i}</item>")
            f.write("</record></root>")

        jf = str(tmp_path / "out.jsonl")
        n = jsonify.stream_xml_to_json(str(xf), jf, record_tag="record",
                                        force_list={"item"})
        assert n == 1

        records = read_lines(jf)
        items = records[0]["item"]
        assert len(items) == n_items
        assert items[0] == "0"
        assert items[-1] == str(n_items - 1)

    def test_memory_stays_roughly_constant_across_sizes(self, tmp_path):
        import resource

        def make(n):
            p = tmp_path / f"f{n}.xml"
            with open(p, "w") as f:
                f.write("<root>\n")
                for i in range(n):
                    f.write(f'<record id="{i}"><name>U{i}</name></record>\n')
                f.write("</root>\n")
            return str(p)

        jf = str(tmp_path / "out.jsonl")
        deltas = []
        for n in (5_000, 50_000):
            xf = make(n)
            before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            jsonify.stream_xml_to_json(xf, jf, record_tag="record")
            after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            deltas.append(after - before)

        # The increase in resident memory for a 10x larger file should be
        # small (a loose bound -- this isn't a precise memory profiler,
        # just a guard against an obviously-quadratic regression).
        assert deltas[-1] < 20_000  # KB


# ---------------------------------------------------------------------------
# No `json` module usage on the write path (sanity check via monkeypatch)
# ---------------------------------------------------------------------------

class TestNoJsonModuleDependency:
    def test_works_even_if_json_module_unavailable(self, tmp_path, monkeypatch):
        """stream_xml_to_json must not import the `json` module internally --
        verify by making `json.dumps`/`json.loads` explode and confirming
        the conversion still succeeds (only our *test's* verification step
        uses json, after the fact, on a separate import)."""
        import sys
        xf = write_xml(tmp_path, b'<root><record id="1"><n>hi</n></record></root>')
        jf = str(tmp_path / "out.jsonl")

        # Temporarily make the json module unusable to prove jsonify's
        # internals never touch it.
        had_json = "json" in sys.modules
        fake = type(sys)("json")
        def _boom(*a, **k):
            raise AssertionError("json module should not be used internally")
        fake.dumps = _boom
        fake.loads = _boom
        fake.dump = _boom
        fake.load = _boom
        old = sys.modules.get("json")
        sys.modules["json"] = fake
        try:
            n = jsonify.stream_xml_to_json(xf, jf, record_tag="record")
            assert n == 1
        finally:
            if old is not None:
                sys.modules["json"] = old
            elif not had_json:
                del sys.modules["json"]

        # Now verify the output with a real json module.
        with open(jf) as f:
            line = f.readline().strip()
        assert json.loads(line) == {"@id": "1", "n": "hi"}
        