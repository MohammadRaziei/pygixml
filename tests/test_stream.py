"""
Tests for pygixml's streaming/iterparse API (PullParser, StreamElement,
iterparse, iterfind -- implemented in stream.pxi on top of the embedded
yxml parser).

Run with:
    pytest tests/test_stream.py -v
"""

import io
import os
import tempfile

import pytest

import pygixml


SAMPLE = b"""<?xml version="1.0" encoding="UTF-8"?>
<database version="1.0">
    <host>localhost</host>
    <records>
        <record id="1"><name>Ali</name><city>Tehran</city></record>
        <record id="2"><name>Sara</name><city>Shiraz</city></record>
        <record id="3"><name>Reza</name><city>Isfahan</city></record>
    </records>
</database>
"""


# ---------------------------------------------------------------------------
# iterparse: basic events
# ---------------------------------------------------------------------------

class TestIterparseBasics:
    def test_default_events_is_end_only(self):
        events = [ev for ev, _ in pygixml.iterparse(SAMPLE)]
        assert set(events) == {"end"}

    def test_start_and_end_events(self):
        events = [ev for ev, _ in pygixml.iterparse(SAMPLE, events=("start", "end"))]
        assert events.count("start") == events.count("end")
        assert events[0] == "start"
        assert events[-1] == "end"

    def test_root_element_seen(self):
        roots = [el for ev, el in pygixml.iterparse(SAMPLE, events=("end",))
                 if el.tag == "database"]
        assert len(roots) == 1
        assert roots[0].get("version") == "1.0"

    def test_text_content(self):
        for ev, el in pygixml.iterparse(SAMPLE, events=("end",)):
            if el.tag == "host":
                assert el.text == "localhost"
                break
        else:
            pytest.fail("host element not found")

    def test_attributes(self):
        records = [el for ev, el in pygixml.iterparse(SAMPLE, events=("end",))
                   if el.tag == "record"]
        assert [r.get("id") for r in records] == ["1", "2", "3"]

    def test_start_event_has_attributes_already(self):
        # ELEMSTART in yxml fires *before* attributes are parsed; the
        # wrapper must buffer until the start tag is fully read.
        for ev, el in pygixml.iterparse(SAMPLE, events=("start",)):
            if el.tag == "record":
                assert el.attrib  # attributes must be present at "start" time
                assert "id" in el.attrib


# ---------------------------------------------------------------------------
# tag filtering
# ---------------------------------------------------------------------------

class TestTagFilter:
    def test_only_matching_tag_yields_events(self):
        tags = {el.tag for ev, el in pygixml.iterparse(SAMPLE, events=("start", "end"), tag="record")}
        assert tags == {"record"}

    def test_subtree_still_built_for_filtered_tag(self):
        # even though only "records" produces events, its <record> children
        # (and their children) must still be fully built.
        for ev, el in pygixml.iterparse(SAMPLE, events=("end",), tag="records"):
            assert el.tag == "records"
            assert len(el) == 3
            for rec in el:
                assert rec.tag == "record"
                assert rec.find("name") is not None
                assert rec.find("city") is not None


# ---------------------------------------------------------------------------
# iterfind
# ---------------------------------------------------------------------------

class TestIterfind:
    def test_iterfind_yields_elements_directly(self):
        names = [rec.find("name").text for rec in pygixml.iterfind(SAMPLE, "record")]
        assert names == ["Ali", "Sara", "Reza"]

    def test_iterfind_empty_when_tag_absent(self):
        assert list(pygixml.iterfind(SAMPLE, "nope")) == []


# ---------------------------------------------------------------------------
# clear() / memory-management idiom
# ---------------------------------------------------------------------------

class TestClear:
    def test_clear_resets_element(self):
        for rec in pygixml.iterfind(SAMPLE, "record"):
            rec.clear()
            assert len(rec) == 0
            assert rec.attrib == {}
            assert rec.text is None
            assert rec.find("name") is None

    def test_cleared_children_remain_in_parent_as_placeholders(self):
        records_holder = []
        for ev, el in pygixml.iterparse(SAMPLE, events=("start", "end")):
            if ev == "start" and el.tag == "records":
                records_holder.append(el)
            if ev == "end" and el.tag == "record":
                el.clear()

        records = records_holder[0]
        assert len(records) == 3
        for rec in records:
            assert rec.tag == "record"
            assert len(rec) == 0  # children dropped by clear()


# ---------------------------------------------------------------------------
# StreamElement API (find/findall/findtext/iter/get/items/keys/len/bool)
# ---------------------------------------------------------------------------

class TestStreamElement:
    def setup_method(self):
        self.db = next(el for ev, el in pygixml.iterparse(SAMPLE, events=("end",))
                        if el.tag == "database")

    def test_find_direct_child(self):
        assert self.db.find("host").text == "localhost"

    def test_find_path(self):
        rec = self.db.find("records/record")
        assert rec.tag == "record"
        assert rec.get("id") == "1"

    def test_findall_returns_all_matches(self):
        records = self.db.find("records").findall("record")
        assert [r.get("id") for r in records] == ["1", "2", "3"]

    def test_findall_wildcard(self):
        children = self.db.findall("*")
        assert [c.tag for c in children] == ["host", "records"]

    def test_findall_descendant(self):
        names = self.db.findall(".//name")
        assert [n.text for n in names] == ["Ali", "Sara", "Reza"]

    def test_find_missing_returns_none(self):
        assert self.db.find("nonexistent") is None

    def test_findtext(self):
        assert self.db.findtext("host") == "localhost"
        assert self.db.findtext("nope", default="fallback") == "fallback"

    def test_iter_includes_self_and_descendants(self):
        tags = [el.tag for el in self.db.iter()]
        assert tags[0] == "database"
        assert "record" in tags
        assert tags.count("record") == 3

    def test_iter_with_tag_filter(self):
        names = [el.text for el in self.db.iter("name")]
        assert names == ["Ali", "Sara", "Reza"]

    def test_get_keys_items(self):
        rec = self.db.find("records/record")
        assert rec.get("id") == "1"
        assert rec.get("missing", "default") == "default"
        assert list(rec.keys()) == ["id"]
        assert list(rec.items()) == [("id", "1")]

    def test_len_iter_getitem(self):
        records = self.db.find("records")
        assert len(records) == 3
        assert records[0].get("id") == "1"
        assert [r.get("id") for r in records] == ["1", "2", "3"]

    def test_bool(self):
        records = self.db.find("records")
        assert bool(records) is True
        empty = self.db.find("host")
        assert bool(empty) is False  # no children


# ---------------------------------------------------------------------------
# Mixed content / text / tail
# ---------------------------------------------------------------------------

class TestMixedContent:
    def test_text_and_tail(self):
        xml = b"<p>before<b>bold</b>after</p>"
        elems = {el.tag: el for ev, el in pygixml.iterparse(xml, events=("end",))}
        assert elems["b"].text == "bold"
        assert elems["b"].tail == "after"
        assert elems["p"].text == "before"

    def test_self_closing_and_empty(self):
        xml = b"<a><b/><c></c><d>x</d></a>"
        elems = {el.tag: el for ev, el in pygixml.iterparse(xml, events=("end",))}
        assert elems["b"].text is None
        assert elems["c"].text is None
        assert elems["d"].text == "x"
        assert len(elems["a"]) == 3


# ---------------------------------------------------------------------------
# Entities, CDATA, attribute decoding, namespaces
# ---------------------------------------------------------------------------

class TestDecoding:
    def test_entity_references_decoded(self):
        xml = b"<a>Tom &amp; Jerry &lt;3&gt; &#65;&#x42;</a>"
        for ev, el in pygixml.iterparse(xml, events=("end",)):
            assert el.text == "Tom & Jerry <3> AB"

    def test_cdata_merged_into_text(self):
        xml = b"<a><![CDATA[<raw> & stuff]]></a>"
        for ev, el in pygixml.iterparse(xml, events=("end",)):
            assert el.text == "<raw> & stuff"

    def test_attribute_entities_decoded(self):
        xml = b'<a x="1 &lt; 2 &amp; 3"/>'
        for ev, el in pygixml.iterparse(xml, events=("end",)):
            assert el.get("x") == "1 < 2 & 3"

    def test_unicode_content(self):
        xml = "<a>سلام دنیا</a>".encode("utf-8")
        for ev, el in pygixml.iterparse(xml, events=("end",)):
            assert el.text == "سلام دنیا"

    def test_namespace_prefixes_kept_raw(self):
        xml = (b'<ns:root xmlns:ns="http://example.com">'
               b'<ns:child a="1"/></ns:root>')
        tags = []
        for ev, el in pygixml.iterparse(xml, events=("end",)):
            tags.append(el.tag)
        assert "ns:root" in tags
        assert "ns:child" in tags

    def test_xmlns_appears_as_attribute(self):
        xml = b'<root xmlns:ns="http://example.com"><ns:child/></root>'
        for ev, el in pygixml.iterparse(xml, events=("end",)):
            if el.tag == "root":
                assert el.get("xmlns:ns") == "http://example.com"


# ---------------------------------------------------------------------------
# Processing instructions
# ---------------------------------------------------------------------------

class TestProcessingInstructions:
    def test_pi_event_emitted(self):
        xml = b'<?xml-stylesheet type="text/xsl" href="x.xsl"?><root/>'
        pis = [val for ev, val in pygixml.iterparse(xml, events=("pi", "end"))
               if ev == "pi"]
        assert len(pis) == 1
        target, content = pis[0]
        assert target == "xml-stylesheet"
        assert "x.xsl" in content

    def test_pi_not_emitted_unless_requested(self):
        xml = b'<?xml-stylesheet type="text/xsl" href="x.xsl"?><root/>'
        events = [ev for ev, _ in pygixml.iterparse(xml, events=("end",))]
        assert "pi" not in events


# ---------------------------------------------------------------------------
# Source types
# ---------------------------------------------------------------------------

class TestSourceTypes:
    def test_bytes_source(self):
        assert sum(1 for _ in pygixml.iterfind(SAMPLE, "record")) == 3

    def test_bytearray_source(self):
        assert sum(1 for _ in pygixml.iterfind(bytearray(SAMPLE), "record")) == 3

    def test_bytesio_source(self):
        assert sum(1 for _ in pygixml.iterfind(io.BytesIO(SAMPLE), "record")) == 3

    def test_file_path_source(self, tmp_path):
        p = tmp_path / "data.xml"
        p.write_bytes(SAMPLE)
        assert sum(1 for _ in pygixml.iterfind(str(p), "record")) == 3

    def test_pathlib_path_source(self, tmp_path):
        p = tmp_path / "data.xml"
        p.write_bytes(SAMPLE)
        assert sum(1 for _ in pygixml.iterfind(p, "record")) == 3

    def test_bom_is_stripped(self):
        xml = b"\xef\xbb\xbf<root>ok</root>"
        for ev, el in pygixml.iterparse(xml, events=("end",)):
            assert el.tag == "root"
            assert el.text == "ok"

    def test_small_chunk_size(self):
        # force many feed() calls / chunk boundaries
        assert sum(1 for _ in pygixml.iterfind(SAMPLE, "record", chunk_size=3)) == 3


# ---------------------------------------------------------------------------
# PullParser (low-level incremental API)
# ---------------------------------------------------------------------------

class TestPullParser:
    def test_feed_in_arbitrary_chunks(self):
        p = pygixml.PullParser(events=("start", "end"))
        chunks = [b'<a x="hel', b'lo &amp; w', b'orld">te', b'xt&#65;end</a>']
        events = []
        for c in chunks:
            p.feed(c)
            events.extend(p.read_events())
        p.close()
        events.extend(p.read_events())

        assert [ev for ev, _ in events] == ["start", "end"]
        elem = events[0][1]
        assert elem.tag == "a"
        assert elem.attrib == {"x": "hello & world"}
        assert elem.text == "textAend"

    def test_feed_byte_by_byte(self):
        p = pygixml.PullParser(events=("end",))
        data = b"<root><a>1</a><b>2</b></root>"
        events = []
        for byte in data:
            p.feed(bytes([byte]))
            events.extend(p.read_events())
        p.close()
        events.extend(p.read_events())

        tags = [el.tag for _, el in events]
        assert tags == ["a", "b", "root"]

    def test_close_is_idempotent(self):
        p = pygixml.PullParser()
        p.feed(b"<root/>")
        p.close()
        p.close()  # must not raise

    def test_feed_after_close_raises(self):
        p = pygixml.PullParser()
        p.feed(b"<root/>")
        p.close()
        with pytest.raises(pygixml.PygiXMLError):
            p.feed(b"<more/>")

    def test_line_and_position_tracking(self):
        p = pygixml.PullParser()
        p.feed(b"<root>\nhello\n</root>")
        p.close()
        assert p.line >= 1
        assert p.position == len(b"<root>\nhello\n</root>")


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrors:
    def test_mismatched_closing_tag(self):
        with pytest.raises(pygixml.PygiXMLError):
            pygixml.PullParser().feed(b"<a><b></a></b>")

    def test_unclosed_root_raises_on_close(self):
        p = pygixml.PullParser()
        p.feed(b"<root><a/>")
        with pytest.raises(pygixml.PygiXMLError):
            p.close()

    def test_syntax_error(self):
        with pytest.raises(pygixml.PygiXMLError):
            pygixml.PullParser().feed(b"<<<not xml")

    def test_stack_too_small_raises(self):
        nested = "".join(f"<verylongtagname{i}>" for i in range(50)).encode()
        with pytest.raises(pygixml.PygiXMLError):
            list(pygixml.iterparse(nested, events=("start",), stack_size=64))

    def test_stack_size_minimum_enforced(self):
        with pytest.raises(ValueError):
            pygixml.PullParser(stack_size=10)

    def test_invalid_event_name(self):
        with pytest.raises(ValueError):
            pygixml.PullParser(events=("bogus",))

    def test_unsupported_source_type(self):
        with pytest.raises(TypeError):
            list(pygixml.iterparse(12345))


# ---------------------------------------------------------------------------
# Large-ish document smoke test
# ---------------------------------------------------------------------------

class TestLargeDocument:
    def test_many_records(self):
        n = 5000
        parts = [b"<root>"]
        for i in range(n):
            parts.append(
                f'<item id="{i}"><name>Item {i}</name></item>'.encode("utf-8")
            )
        parts.append(b"</root>")
        data = b"".join(parts)

        count = 0
        total = 0
        for elem in pygixml.iterfind(data, "item"):
            count += 1
            total += int(elem.get("id"))
            elem.clear()

        assert count == n
        assert total == sum(range(n))

    def test_file_streaming(self, tmp_path):
        n = 2000
        p = tmp_path / "big.xml"
        with open(p, "wb") as f:
            f.write(b"<root>")
            for i in range(n):
                f.write(f'<item id="{i}"/>'.encode("utf-8"))
            f.write(b"</root>")

        ids = [int(el.get("id")) for el in pygixml.iterfind(str(p), "item", chunk_size=4096)]
        assert ids == list(range(n))
        