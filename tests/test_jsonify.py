"""
Tests for pygixml.jsonify — smart dispatcher.

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


@pytest.fixture
def root(xml_full):
    return objectify.from_string(xml_full)


def parsed(source, **kw):
    return json.loads(jsonify.dumps(source, **kw))


# ---------------------------------------------------------------------------
# 1. Smart dispatcher routing
# ---------------------------------------------------------------------------

class TestDispatcher:

    def test_routes_xml_string(self, xml_simple):
        d = parsed(xml_simple)
        assert "root" in d

    def test_routes_xml_string_with_declaration(self):
        xml = '<?xml version="1.0"?><root/>'
        d = parsed(xml)
        assert "root" in d

    def test_routes_file_path_str(self, xml_full):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".xml", delete=False, encoding="utf-8"
        ) as f:
            f.write(xml_full)
            tmp = f.name
        try:
            d = parsed(tmp)
            assert "database" in d
        finally:
            os.unlink(tmp)

    def test_routes_pathlib_path(self, xml_full):
        from pathlib import Path
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".xml", delete=False, encoding="utf-8"
        ) as f:
            f.write(xml_full)
            tmp = f.name
        try:
            d = parsed(Path(tmp))
            assert "database" in d
        finally:
            os.unlink(tmp)

    def test_routes_objectified_element(self, root):
        d = parsed(root)
        assert "database" in d

    def test_routes_objectified_element_subtree(self, root):
        d = parsed(root.user_profile)
        assert "user-profile" in d

    def test_wrong_type_raises_type_error(self):
        with pytest.raises(TypeError):
            jsonify.dumps(12345)

    def test_wrong_type_error_message(self):
        with pytest.raises(TypeError, match="int"):
            jsonify.dumps(42)


# ---------------------------------------------------------------------------
# 2. Basic structure — same conventions as dictify
# ---------------------------------------------------------------------------

class TestBasicStructure:

    def test_empty_element_is_null(self):
        assert parsed("<root/>") == {"root": None}

    def test_whitespace_only_is_null(self):
        assert parsed("<root>   </root>") == {"root": None}

    def test_text_only(self):
        assert parsed("<root>hello</root>") == {"root": "hello"}

    def test_attribute_prefixed(self, xml_simple):
        assert parsed(xml_simple)["root"]["@id"] == "1"

    def test_repeated_siblings_become_array(self, xml_full):
        d = parsed(xml_full)
        assert d["database"]["entry"] == ["Value A", "Value B", "Value C"]

    def test_mixed_content(self, xml_mixed):
        d = parsed(xml_mixed)
        assert d["root"]["@attr"] == "v"
        assert d["root"]["#text"] == "text"

    def test_full_document(self, xml_full):
        d = parsed(xml_full)
        db = d["database"]
        assert db["@name"] == "users_db"
        assert db["user-profile"]["first_name"] == "Mohammad"


# ---------------------------------------------------------------------------
# 3. Valid JSON output
# ---------------------------------------------------------------------------

class TestValidJson:

    def test_parses_without_error(self, xml_full):
        json.loads(jsonify.dumps(xml_full))

    def test_unicode_preserved(self):
        xml = "<root><city>تهران</city></root>"
        assert parsed(xml)["root"]["city"] == "تهران"

    def test_special_chars_escaped(self):
        xml = '<root msg="a&amp;b"/>'
        json.loads(jsonify.dumps(xml))


# ---------------------------------------------------------------------------
# 4. Options
# ---------------------------------------------------------------------------

class TestOptions:

    def test_custom_attr_prefix(self, xml_simple):
        d = parsed(xml_simple, attr_prefix="")
        assert d["root"]["id"] == "1"

    def test_custom_cdata_key(self, xml_mixed):
        d = parsed(xml_mixed, cdata_key="__text")
        assert "__text" in d["root"]

    def test_force_list_single(self):
        d = parsed("<r><x>only</x></r>", force_list={"x"})
        assert d["r"]["x"] == ["only"]

    def test_force_list_true(self):
        d = parsed("<r><x>v</x><y>w</y></r>", force_list=True)
        assert isinstance(d["r"]["x"], list)
        assert isinstance(d["r"]["y"], list)

    def test_pretty_has_newlines(self, xml_simple):
        assert "\n" in jsonify.dumps(xml_simple, pretty=True)

    def test_pretty_custom_indent(self, xml_simple):
        assert "  " in jsonify.dumps(xml_simple, pretty=True, indent="  ")

    def test_compact_no_newlines(self, xml_full):
        assert "\n" not in jsonify.dumps(xml_full, pretty=False)

    def test_pretty_valid_json(self, xml_full):
        json.loads(jsonify.dumps(xml_full, pretty=True))


# ---------------------------------------------------------------------------
# 5. Consistency with dictify
# ---------------------------------------------------------------------------

class TestConsistencyWithDictify:

    def test_same_as_dictify_full(self, xml_full):
        from pygixml import dictify
        assert dictify.parse(xml_full) == parsed(xml_full)

    def test_same_as_dictify_simple(self, xml_simple):
        from pygixml import dictify
        assert dictify.parse(xml_simple) == parsed(xml_simple)

    def test_same_as_dictify_mixed(self, xml_mixed):
        from pygixml import dictify
        assert dictify.parse(xml_mixed) == parsed(xml_mixed)


# ---------------------------------------------------------------------------
# 6. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_malformed_str_raises(self):
        with pytest.raises(Exception):
            jsonify.dumps("not < valid")

    def test_missing_file_raises(self):
        with pytest.raises(Exception):
            jsonify.dumps("/no/such/file_xyz.xml")

    def test_deeply_nested(self):
        xml = "<a><b><c><d><e>deep</e></d></c></b></a>"
        assert parsed(xml)["a"]["b"]["c"]["d"]["e"] == "deep"

    def test_subtree_from_node(self, root):
        d = parsed(root.user_profile)
        assert d["user-profile"]["@id"] == "101"
        assert d["user-profile"]["balance"] == "450.75"

    def test_numeric_attr_stays_string(self):
        assert isinstance(parsed('<r n="42"/>')["r"]["@n"], str)
