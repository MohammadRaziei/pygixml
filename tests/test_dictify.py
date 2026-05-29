"""
Tests for pygixml.dictify — dictify-compatible interface.

Run with:
    pytest tests/test_dictify.py -v
"""

import os
import tempfile

import pytest

from pygixml import dictify


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse(xml, **kw):
    return dictify.parse(xml, **kw)


def unparse(d, **kw):
    return dictify.unparse(d, **kw)


# ---------------------------------------------------------------------------
# 1. parse — basic structure
# ---------------------------------------------------------------------------

class TestParseBasic:

    def test_root_tag_is_key(self):
        assert "root" in parse("<root/>")

    def test_empty_element_is_none(self):
        assert parse("<root/>") == {"root": None}

    def test_empty_element_with_whitespace_text_is_none(self):
        assert parse("<root>   </root>") == {"root": None}

    def test_text_only_node(self):
        assert parse("<root>hello</root>") == {"root": "hello"}

    def test_nested_text_only(self):
        d = parse("<r><x>text</x></r>")
        assert d == {"r": {"x": "text"}}

    def test_nested_null(self):
        d = parse("<r><x/></r>")
        assert d == {"r": {"x": None}}

    def test_full_document(self):
        xml = ('<database name="users_db" version="1.2">'
               '<user-profile id="101" verified="true">'
               '<first_name>Mohammad</first_name>'
               '<balance>450.75</balance>'
               '</user-profile>'
               '<entry>Value A</entry>'
               '<entry>Value B</entry>'
               '<entry>Value C</entry>'
               '</database>')
        d = parse(xml)
        db = d["database"]
        assert db["@name"] == "users_db"
        assert db["@version"] == "1.2"
        up = db["user-profile"]
        assert up["@id"] == "101"
        assert up["@verified"] == "true"
        assert up["first_name"] == "Mohammad"
        assert up["balance"] == "450.75"
        assert db["entry"] == ["Value A", "Value B", "Value C"]


# ---------------------------------------------------------------------------
# 2. parse — attributes
# ---------------------------------------------------------------------------

class TestParseAttributes:

    def test_attribute_prefixed_with_at(self):
        d = parse('<r a="1"/>')
        assert d == {"r": {"@a": "1"}}

    def test_multiple_attributes(self):
        d = parse('<r a="1" b="2"/>')
        assert d["r"]["@a"] == "1"
        assert d["r"]["@b"] == "2"

    def test_custom_attr_prefix(self):
        d = parse('<r a="1">t</r>', attr_prefix="", cdata_key="text")
        assert d == {"r": {"a": "1", "text": "t"}}

    def test_empty_attr_prefix(self):
        d = parse('<r id="5"/>', attr_prefix="")
        assert d == {"r": {"id": "5"}}


# ---------------------------------------------------------------------------
# 3. parse — mixed content (attrs + text)
# ---------------------------------------------------------------------------

class TestParseMixed:

    def test_attr_and_text_uses_cdata_key(self):
        d = parse('<r attr="v">text</r>')
        assert d == {"r": {"@attr": "v", "#text": "text"}}

    def test_custom_cdata_key(self):
        d = parse('<r attr="v">text</r>', cdata_key="__text")
        assert d["r"]["__text"] == "text"

    def test_attr_and_children(self):
        d = parse('<r a="1"><x>v</x></r>')
        assert d["r"]["@a"] == "1"
        assert d["r"]["x"] == "v"

    def test_node_with_attr_and_text(self):
        d = parse('<r><x a="1">text</x></r>')
        assert d == {"r": {"x": {"@a": "1", "#text": "text"}}}


# ---------------------------------------------------------------------------
# 4. parse — repeated siblings → list
# ---------------------------------------------------------------------------

class TestParseRepeated:

    def test_repeated_siblings_become_list(self):
        d = parse("<r><x>a</x><x>b</x></r>")
        assert d == {"r": {"x": ["a", "b"]}}

    def test_three_siblings(self):
        d = parse("<r><x>a</x><x>b</x><x>c</x></r>")
        assert d["r"]["x"] == ["a", "b", "c"]

    def test_single_is_not_list_by_default(self):
        d = parse("<r><x>only</x></r>")
        assert d["r"]["x"] == "only"
        assert not isinstance(d["r"]["x"], list)

    def test_nested_repeated(self):
        d = parse("<r><x><y>1</y><y>2</y></x></r>")
        assert d["r"]["x"]["y"] == ["1", "2"]


# ---------------------------------------------------------------------------
# 5. parse — force_list
# ---------------------------------------------------------------------------

class TestParseForceList:

    def test_force_list_single(self):
        d = parse("<r><x>only one</x></r>", force_list={"x"})
        assert d == {"r": {"x": ["only one"]}}

    def test_force_list_already_multiple(self):
        d = parse("<r><x>a</x><x>b</x></r>", force_list={"x"})
        assert d["r"]["x"] == ["a", "b"]

    def test_force_list_true(self):
        d = parse("<r><x>v</x><y>w</y></r>", force_list=True)
        assert isinstance(d["r"]["x"], list)
        assert isinstance(d["r"]["y"], list)

    def test_force_list_unrelated_tag_unaffected(self):
        d = parse("<r><x>v</x><y>w</y></r>", force_list={"x"})
        assert isinstance(d["r"]["x"], list)
        assert not isinstance(d["r"]["y"], list)


# ---------------------------------------------------------------------------
# 6. parse — CDATA
# ---------------------------------------------------------------------------

class TestParseCDATA:

    def test_cdata_text(self):
        d = parse("<r><![CDATA[hello]]></r>")
        assert d == {"r": "hello"}

    def test_cdata_with_special_chars(self):
        d = parse("<r><![CDATA[<not>a</tag>]]></r>")
        assert d["r"] == "<not>a</tag>"


# ---------------------------------------------------------------------------
# 7. parse — edge cases
# ---------------------------------------------------------------------------

class TestParseEdgeCases:

    def test_malformed_raises(self):
        with pytest.raises(Exception):
            parse("not < valid")

    def test_unicode_text(self):
        d = parse("<r><city>تهران</city></r>")
        assert d["r"]["city"] == "تهران"

    def test_deeply_nested(self):
        d = parse("<a><b><c><d>v</d></c></b></a>")
        assert d["a"]["b"]["c"]["d"] == "v"

    def test_namespace_in_tag(self):
        d = parse('<r xmlns:ns="http://x"><ns:x/></r>')
        assert "@xmlns:ns" in d["r"]
        assert "ns:x" in d["r"]

    def test_numeric_attribute_stays_string(self):
        # dictify does not type-infer — values stay as strings
        d = parse('<r n="42"/>')
        assert d["r"]["@n"] == "42"
        assert isinstance(d["r"]["@n"], str)


# ---------------------------------------------------------------------------
# 8. parse_file
# ---------------------------------------------------------------------------

class TestParseFile:

    def test_parse_file_roundtrip(self):
        xml = '<root><item id="1">hello</item></root>'
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".xml", delete=False, encoding="utf-8"
        ) as f:
            f.write(xml)
            tmp = f.name
        try:
            d = dictify.parse_file(tmp)
            assert d["root"]["item"]["@id"] == "1"
            assert d["root"]["item"]["#text"] == "hello"
        finally:
            os.unlink(tmp)

    def test_parse_file_missing_raises(self):
        with pytest.raises(Exception):
            dictify.parse_file("/no/such/file_xyz.xml")


# ---------------------------------------------------------------------------
# 9. unparse — basic
# ---------------------------------------------------------------------------

class TestUnparseBasic:

    def test_unparse_simple(self):
        xml = unparse({"root": None})
        assert "<root/>" in xml

    def test_unparse_text(self):
        xml = unparse({"root": "hello"})
        assert "<root>hello</root>" in xml

    def test_unparse_attribute(self):
        xml = unparse({"root": {"@id": "1"}})
        assert 'id="1"' in xml

    def test_unparse_list(self):
        xml = unparse({"root": {"item": ["a", "b"]}})
        assert xml.count("<item>") == 2
        assert "<item>a</item>" in xml
        assert "<item>b</item>" in xml

    def test_unparse_nested(self):
        xml = unparse({"root": {"child": {"grandchild": "v"}}})
        assert "<grandchild>v</grandchild>" in xml

    def test_unparse_roundtrip(self):
        original = ('<database name="users_db">'
                    '<entry>Value A</entry>'
                    '<entry>Value B</entry>'
                    '</database>')
        d = parse(original)
        xml = unparse(d)
        d2 = parse(xml)
        assert d == d2

    def test_unparse_pretty_indents(self):
        xml = unparse({"root": {"x": "v"}}, pretty=True)
        assert "\n" in xml
        assert "\t" in xml

    def test_unparse_full_document_declaration(self):
        xml = unparse({"root": None}, full_document="true")
        assert "<?xml" in xml

    def test_unparse_no_declaration(self):
        xml = unparse({"root": None}, full_document="false")
        assert "<?xml" not in xml

    def test_unparse_wrong_root_raises(self):
        with pytest.raises(ValueError):
            unparse({"a": 1, "b": 2})

    def test_unparse_custom_indent(self):
        xml = unparse({"root": {"x": "v"}}, pretty=True, indent="  ")
        assert "  <x>" in xml
