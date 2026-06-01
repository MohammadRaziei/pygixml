"""
Tests for pygixml.jsonify — direct XML → JSON serialization.

Run with:
    pytest tests/test_jsonify.py -v
"""

import json
import os
import tempfile

import pytest

from pygixml import jsonify, objectify


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def xml_simple():
    return '<root id="1"><item>hello</item></root>'


@pytest.fixture
def xml_full():
    return """
<database name="users_db" version="1.2">
    <user-profile id="101" verified="true">
        <first_name>Mohammad</first_name>
        <balance>450.75</balance>
    </user-profile>
    <entry>Value A</entry>
    <entry>Value B</entry>
    <entry>Value C</entry>
</database>
"""


@pytest.fixture
def xml_mixed():
    return '<root attr="v">text</root>'


# ---------------------------------------------------------------------------
# Helper — parse JSON from jsonify output and compare to dictify reference
# ---------------------------------------------------------------------------

def parsed(xml, **kw):
    return json.loads(jsonify.dumps(xml, **kw))


# ---------------------------------------------------------------------------
# 1. Basic structure — matches dictify conventions
# ---------------------------------------------------------------------------

class TestBasicStructure:

    def test_root_key(self, xml_simple):
        d = parsed(xml_simple)
        assert "root" in d

    def test_empty_element_is_null(self):
        assert parsed("<root/>") == {"root": None}

    def test_whitespace_only_is_null(self):
        assert parsed("<root>   </root>") == {"root": None}

    def test_text_only(self):
        assert parsed("<root>hello</root>") == {"root": "hello"}

    def test_nested_text(self):
        d = parsed("<r><x>text</x></r>")
        assert d == {"r": {"x": "text"}}

    def test_attribute_prefixed(self, xml_simple):
        d = parsed(xml_simple)
        assert d["root"]["@id"] == "1"

    def test_text_and_attr(self, xml_mixed):
        d = parsed(xml_mixed)
        assert d["root"]["@attr"] == "v"
        assert d["root"]["#text"] == "text"

    def test_repeated_siblings_become_array(self, xml_full):
        d = parsed(xml_full)
        assert isinstance(d["database"]["entry"], list)
        assert d["database"]["entry"] == ["Value A", "Value B", "Value C"]

    def test_full_document(self, xml_full):
        d = parsed(xml_full)
        db = d["database"]
        assert db["@name"] == "users_db"
        assert db["@version"] == "1.2"
        up = db["user-profile"]
        assert up["@id"] == "101"
        assert up["first_name"] == "Mohammad"
        assert up["balance"] == "450.75"


# ---------------------------------------------------------------------------
# 2. Output is valid JSON
# ---------------------------------------------------------------------------

class TestValidJson:

    def test_parses_without_error(self, xml_full):
        result = jsonify.dumps(xml_full)
        json.loads(result)   # must not raise

    def test_special_chars_escaped(self):
        xml = '<root msg="say &quot;hi&quot;"/>'
        result = jsonify.dumps(xml)
        d = json.loads(result)
        assert '"' in d["root"]["@msg"]

    def test_unicode_preserved(self):
        xml = "<root><city>تهران</city></root>"
        d = parsed(xml)
        assert d["root"]["city"] == "تهران"

    def test_newline_in_text_escaped(self):
        xml = "<root><msg>line1\nline2</msg></root>"
        result = jsonify.dumps(xml)
        json.loads(result)   # must not raise


# ---------------------------------------------------------------------------
# 3. Options — attr_prefix, cdata_key
# ---------------------------------------------------------------------------

class TestOptions:

    def test_custom_attr_prefix(self):
        d = parsed('<r a="1"/>', attr_prefix="")
        assert d["r"]["a"] == "1"

    def test_custom_cdata_key(self, xml_mixed):
        d = parsed(xml_mixed, cdata_key="__text")
        assert "__text" in d["root"]
        assert "#text" not in d["root"]

    def test_empty_attr_prefix(self):
        d = parsed('<r id="5"/>', attr_prefix="")
        assert d["r"]["id"] == "5"


# ---------------------------------------------------------------------------
# 4. force_list
# ---------------------------------------------------------------------------

class TestForceList:

    def test_force_list_single(self):
        d = parsed("<r><x>only</x></r>", force_list={"x"})
        assert isinstance(d["r"]["x"], list)
        assert d["r"]["x"] == ["only"]

    def test_force_list_true(self):
        d = parsed("<r><x>v</x><y>w</y></r>", force_list=True)
        assert isinstance(d["r"]["x"], list)
        assert isinstance(d["r"]["y"], list)

    def test_force_list_already_multiple(self):
        d = parsed("<r><x>a</x><x>b</x></r>", force_list={"x"})
        assert d["r"]["x"] == ["a", "b"]

    def test_force_list_unrelated_unaffected(self):
        d = parsed("<r><x>v</x><y>w</y></r>", force_list={"x"})
        assert not isinstance(d["r"]["y"], list)


# ---------------------------------------------------------------------------
# 5. Pretty printing
# ---------------------------------------------------------------------------

class TestPretty:

    def test_pretty_has_newlines(self, xml_simple):
        result = jsonify.dumps(xml_simple, pretty=True)
        assert "\n" in result

    def test_pretty_has_indent(self, xml_simple):
        result = jsonify.dumps(xml_simple, pretty=True)
        assert "\t" in result

    def test_pretty_custom_indent(self, xml_simple):
        result = jsonify.dumps(xml_simple, pretty=True, indent="  ")
        assert "  " in result

    def test_compact_no_newlines(self, xml_full):
        result = jsonify.dumps(xml_full, pretty=False)
        assert "\n" not in result

    def test_pretty_still_valid_json(self, xml_full):
        result = jsonify.dumps(xml_full, pretty=True)
        json.loads(result)


# ---------------------------------------------------------------------------
# 6. dumps_file
# ---------------------------------------------------------------------------

class TestDumpsFile:

    def test_dumps_file_roundtrip(self, xml_full):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".xml", delete=False, encoding="utf-8"
        ) as f:
            f.write(xml_full)
            tmp = f.name
        try:
            result = jsonify.dumps_file(tmp)
            d = json.loads(result)
            assert "database" in d
        finally:
            os.unlink(tmp)

    def test_dumps_file_missing_raises(self):
        with pytest.raises(Exception):
            jsonify.dumps_file("/no/such/file_xyz.xml")


# ---------------------------------------------------------------------------
# 7. dumps_node — from ObjectifiedElement
# ---------------------------------------------------------------------------

class TestDumpsNode:

    def test_dumps_node_subtree(self, xml_full):
        root = objectify.from_string(xml_full)
        result = jsonify.dumps_node(root.user_profile)
        d = json.loads(result)
        assert "user-profile" in d
        assert d["user-profile"]["first_name"] == "Mohammad"

    def test_dumps_node_leaf(self, xml_full):
        root = objectify.from_string(xml_full)
        result = jsonify.dumps_node(root.user_profile.first_name)
        d = json.loads(result)
        assert d["first_name"] == "Mohammad"

    def test_dumps_node_wrong_type_raises(self):
        with pytest.raises(TypeError):
            jsonify.dumps_node("not an element")

    def test_dumps_node_pretty(self, xml_full):
        root = objectify.from_string(xml_full)
        result = jsonify.dumps_node(root, pretty=True)
        assert "\n" in result
        json.loads(result)


# ---------------------------------------------------------------------------
# 8. Consistency with dictify
# ---------------------------------------------------------------------------

class TestConsistencyWithDictify:
    """jsonify output must be consistent with dictify.parse output."""

    def test_same_structure_as_dictify(self, xml_full):
        from pygixml import dictify
        import json as _json

        d_dictify  = dictify.parse(xml_full)
        d_jsonify  = json.loads(jsonify.dumps(xml_full))
        assert d_dictify == d_jsonify

    def test_same_for_simple(self, xml_simple):
        from pygixml import dictify
        d_dictify = dictify.parse(xml_simple)
        d_jsonify = json.loads(jsonify.dumps(xml_simple))
        assert d_dictify == d_jsonify

    def test_same_for_mixed(self, xml_mixed):
        from pygixml import dictify
        d_dictify = dictify.parse(xml_mixed)
        d_jsonify = json.loads(jsonify.dumps(xml_mixed))
        assert d_dictify == d_jsonify


# ---------------------------------------------------------------------------
# 9. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_malformed_raises(self):
        with pytest.raises(Exception):
            jsonify.dumps("not < valid")

    def test_deeply_nested(self):
        xml = "<a><b><c><d><e>deep</e></d></c></b></a>"
        d = parsed(xml)
        assert d["a"]["b"]["c"]["d"]["e"] == "deep"

    def test_empty_root(self):
        assert parsed("<root/>") == {"root": None}

    def test_numeric_attribute_stays_string(self):
        # jsonify does not type-infer — consistent with dictify
        d = parsed('<r n="42"/>')
        assert d["r"]["@n"] == "42"
        assert isinstance(d["r"]["@n"], str)
