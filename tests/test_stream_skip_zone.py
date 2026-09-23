"""
Regression tests for the PullParser "skip zone" optimization.

Background: when ``iterparse``/``iterfind`` is given a ``tag`` filter,
elements that are never part of a matching element's subtree used to
still be fully built into StreamElement objects (attrib dict, children
list, text/tail) even though nothing ever looks at them. PullParser now
represents such elements with a lightweight ``None`` marker on its
internal stack instead of allocating a real object for them.

These tests exercise the tricky edges that change introduces:
  - a match tag nested *inside* an otherwise-skipped ancestor
  - several skip zones and matches interleaved as siblings
  - matched elements immediately adjacent to skip zones (boundary
    conditions on text/tail assignment)
  - attributes, text and nested children on elements *inside* a skip
    zone must never surface anywhere, but must not crash the parser
  - the "no tag filter" path (must still fully build everything, byte
    for byte identical to before)
  - the same documents fed one byte at a time, to make sure the
    optimization behaves under the chunk boundaries PullParser.feed()
    can be called with.

Run with:
    pytest tests/test_stream_skip_zone.py -v
"""

import xml.etree.ElementTree as ET

import pytest

import pygixml


def _iterfind_all(xml_bytes, tag):
    """Collect (tag, attrib, text, [child tags]) for every match, in order."""
    out = []
    for elem in pygixml.iterfind(xml_bytes, tag):
        out.append((
            elem.tag,
            dict(elem.attrib),
            elem.text,
            [c.tag for c in elem],
        ))
    return out


def _feed_one_byte_at_a_time(xml_bytes, events=("end",), tag=None):
    parser = pygixml.PullParser(events=events, tag=tag)
    seen = []
    for b in xml_bytes:
        parser.feed(bytes([b]))
        for ev, el in parser.read_events():
            seen.append((ev, el))
    parser.close()
    for ev, el in parser.read_events():
        seen.append((ev, el))
    return seen


# ---------------------------------------------------------------------------
# Skip zones around matches
# ---------------------------------------------------------------------------

class TestSkipZoneCorrectness:
    XML = b"""<root>
        <ignore><nested attr="v">xxxxx</nested><more>y</more></ignore>
        <record id="1">A<child>B</child>tail</record>
        <ignore2>zzzz</ignore2>
        <wrap><record id="2">C</record></wrap>
    </root>"""

    def test_only_matching_tags_yielded(self):
        results = _iterfind_all(self.XML, "record")
        ids = [attrib.get("id") for _tag, attrib, _text, _children in results]
        assert ids == ["1", "2"]

    def test_first_record_text_and_children_preserved(self):
        results = _iterfind_all(self.XML, "record")
        tag, attrib, text, children = results[0]
        assert tag == "record"
        assert attrib == {"id": "1"}
        assert text == "A"
        assert children == ["child"]

    def test_first_record_child_text_and_tail(self):
        (elem,) = list(pygixml.iterfind(self.XML, "record"))[:1]
        child = elem[0]
        assert child.tag == "child"
        assert child.text == "B"
        assert child.tail == "tail"

    def test_second_record_nested_in_skip_zone(self):
        """<record id="2"> is a child of <wrap>, which never matches --
        the match must still be found and built even though its direct
        parent is inside a skip zone."""
        results = _iterfind_all(self.XML, "record")
        tag, attrib, text, children = results[1]
        assert tag == "record"
        assert attrib == {"id": "2"}
        assert text == "C"
        assert children == []

    def test_matches_independent_of_skip_ancestors(self):
        """Matched elements must not accidentally end up linked as
        children of an unbuilt ancestor (they're standalone roots)."""
        elems = list(pygixml.iterfind(self.XML, "record"))
        assert all(isinstance(e, pygixml.StreamElement) for e in elems)
        # each match's own children only contain what's really inside it
        assert len(elems[0]) == 1   # <child>
        assert len(elems[1]) == 0   # <record id="2">C</record> is a leaf

    def test_start_and_end_events_only_fire_for_matches(self):
        events = [ev for ev, _el in pygixml.iterparse(self.XML, events=("start", "end"), tag="record")]
        assert events == ["start", "end", "start", "end"]

    def test_no_crash_with_attrs_text_nested_children_in_skip_zone(self):
        # Sanity: the skip zone has its own attribute, text, and a
        # further-nested element -- none of it should ever surface, and
        # none of it should raise.
        results = _iterfind_all(self.XML, "record")
        assert len(results) == 2


# ---------------------------------------------------------------------------
# Interleaved skip/match siblings, various depths
# ---------------------------------------------------------------------------

class TestInterleavedSiblings:
    def _build(self, n_groups):
        parts = [b"<root>"]
        for i in range(n_groups):
            parts.append(f'<noise{i}><a><b>deep{i}</b></a></noise{i}>'.encode())
            parts.append(f'<item id="{i}">v{i}</item>'.encode())
        parts.append(b"</root>")
        return b"".join(parts)

    @pytest.mark.parametrize("n", [0, 1, 2, 5, 25])
    def test_matches_in_order(self, n):
        xml = self._build(n)
        results = _iterfind_all(xml, "item")
        assert [attrib["id"] for _t, attrib, _x, _c in results] == [str(i) for i in range(n)]
        assert [text for _t, _a, text, _c in results] == [f"v{i}" for i in range(n)]

    def test_deeply_nested_skip_zone_before_first_match(self):
        xml = b"<root>" + b"<a>" * 50 + b"<b>noise</b>" + b"</a>" * 50 + b'<item id="0">hit</item></root>'
        results = _iterfind_all(xml, "item")
        assert len(results) == 1
        assert results[0][1] == {"id": "0"}
        assert results[0][2] == "hit"


# ---------------------------------------------------------------------------
# Descendants of a match are always fully built, regardless of their tag
# ---------------------------------------------------------------------------

class TestMatchedSubtreeAlwaysBuilt:
    XML = b"""<root>
        <record id="1">
            <a><b><c>deep</c></b></a>
            <sibling>text</sibling>
        </record>
    </root>"""

    def test_full_subtree_of_a_match_is_built(self):
        elem = next(iter(pygixml.iterfind(self.XML, "record")))
        a = elem.findall("a")[0]
        b = a.findall("b")[0]
        c = b.findall("c")[0]
        assert c.text == "deep"
        sibling = elem.findall("sibling")[0]
        assert sibling.text == "text"

    def test_tag_matching_filter_nested_inside_a_match_also_fires(self):
        # a match nested inside another match: both must fire "end",
        # inner element closes (and is yielded) before the outer one.
        xml = b"<root><record><record>inner</record></record></root>"
        texts = [el.text for _ev, el in pygixml.iterparse(xml, events=("end",), tag="record")]
        assert texts == ["inner", None]


# ---------------------------------------------------------------------------
# No-filter path must be unaffected (always builds everything, as before)
# ---------------------------------------------------------------------------

class TestNoFilterUnaffected:
    XML = b"""<root a="1"><x>1</x><y><z>2</z></y><x>3</x></root>"""

    def test_full_tree_built_without_tag_filter(self):
        events = list(pygixml.iterparse(self.XML, events=("start", "end")))
        ends = {el.tag for ev, el in events if ev == "end"}
        assert ends == {"root", "x", "y", "z"}

    def test_matches_elementtree_structure(self):
        # cross-check against the stdlib for a document with several
        # different tags and no filter -- nothing should ever be skipped.
        pyg_tags = [el.tag for ev, el in pygixml.iterparse(self.XML, events=("end",))]
        et_tags = [el.tag for ev, el in ET.iterparse(__import__("io").BytesIO(self.XML), events=("end",))]
        assert sorted(pyg_tags) == sorted(et_tags)


# ---------------------------------------------------------------------------
# Same documents, fed one byte at a time (exercises state across feed() calls)
# ---------------------------------------------------------------------------

class TestByteAtATimeFeeding:
    XML = b"""<root>
        <ignore><nested>x</nested></ignore>
        <record id="1">A<child>B</child>tail</record>
        <wrap><record id="2">C</record></wrap>
    </root>"""

    def test_byte_at_a_time_matches_bulk_feed(self):
        bulk = _iterfind_all(self.XML, "record")

        byte_events = _feed_one_byte_at_a_time(self.XML, events=("end",), tag="record")
        byte_results = [
            (el.tag, dict(el.attrib), el.text, [c.tag for c in el])
            for _ev, el in byte_events
        ]
        assert byte_results == bulk

    def test_byte_at_a_time_child_tail_preserved(self):
        byte_events = _feed_one_byte_at_a_time(self.XML, events=("end",), tag="record")
        first = byte_events[0][1]
        assert first[0].text == "B"
        assert first[0].tail == "tail"


# ---------------------------------------------------------------------------
# Cross-check against ElementTree for a document with a large "noise"
# section outside the matched tag -- the actual scenario the optimization
# targets.
# ---------------------------------------------------------------------------

class TestAgainstElementTreeWithNoise:
    def _gen(self, n_noise, n_matches):
        parts = [b"<root>"]
        for i in range(n_noise):
            parts.append(
                f'<config><section name="s{i}"><opt k="{i}">val{i}</opt></section></config>'.encode()
            )
        for i in range(n_matches):
            parts.append(f'<record id="{i}" status="ok"><name>rec{i}</name><value>{i * 2}</value></record>'.encode())
        parts.append(b"</root>")
        return b"".join(parts)

    def test_matches_and_fields_match_elementtree(self):
        xml = self._gen(200, 30)

        pyg_records = []
        for elem in pygixml.iterfind(xml, "record"):
            pyg_records.append({
                "id": elem.get("id"),
                "status": elem.get("status"),
                "name": elem.findall("name")[0].text,
                "value": elem.findall("value")[0].text,
            })

        root = ET.fromstring(xml)
        et_records = []
        for elem in root.findall("record"):
            et_records.append({
                "id": elem.get("id"),
                "status": elem.get("status"),
                "name": elem.find("name").text,
                "value": elem.find("value").text,
            })

        assert pyg_records == et_records
        assert len(pyg_records) == 30
