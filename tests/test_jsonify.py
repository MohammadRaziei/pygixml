"""
Tests for pygixml.jsonify — typed entry points + smart dispatcher.

Run with:
    pytest tests/test_jsonify.py -v
"""

import json
import os
import tempfile

import pytest

import pygixml
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


@pytest.fixture
def doc(xml_full):
    return pygixml.parse_string(xml_full)


def p(source, **kw):
    """Parse JSON from jsonify output."""
    return json.loads(jsonify.dumps(source, **kw))


# ---------------------------------------------------------------------------
# 1. dumps_str
# ---------------------------------------------------------------------------

class TestDumpsStr:

    def test_basic(self, xml_simple):
        d = json.loads(jsonify.dumps_str(xml_simple))
        assert d["root"]["@id"] == "1"
        assert d["root"]["item"] == "hello"

    def test_repeated_siblings(self, xml_full):
        d = json.loads(jsonify.dumps_str(xml_full))
        assert d["database"]["entry"] == ["Value A", "Value B", "Value C"]

    def test_malformed_raises(self):
        with pytest.raises(Exception):
            jsonify.dumps_str("not < valid")

    def test_returns_valid_json(self, xml_full):
        json.loads(jsonify.dumps_str(xml_full))

    def test_pretty(self, xml_simple):
        result = jsonify.dumps_str(xml_simple, pretty=True)
        assert "\n" in result
        json.loads(result)

    def test_force_list(self):
        d = json.loads(jsonify.dumps_str("<r><x>one</x></r>", force_list={"x"}))
        assert d["r"]["x"] == ["one"]

    def test_force_list_true(self):
        d = json.loads(jsonify.dumps_str("<r><x>v</x></r>", force_list=True))
        assert isinstance(d["r"]["x"], list)

    def test_custom_attr_prefix(self, xml_simple):
        d = json.loads(jsonify.dumps_str(xml_simple, attr_prefix=""))
        assert d["root"]["id"] == "1"

    def test_unicode(self):
        d = json.loads(jsonify.dumps_str("<r><c>تهران</c></r>"))
        assert d["r"]["c"] == "تهران"


# ---------------------------------------------------------------------------
# 2. dumps_file
# ---------------------------------------------------------------------------

class TestDumpsFile:

    def test_basic(self, xml_full):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".xml", delete=False, encoding="utf-8"
        ) as f:
            f.write(xml_full)
            tmp = f.name
        try:
            d = json.loads(jsonify.dumps_file(tmp))
            assert "database" in d
            assert d["database"]["@name"] == "users_db"
        finally:
            os.unlink(tmp)

    def test_missing_raises(self):
        with pytest.raises(Exception):
            jsonify.dumps_file("/no/such/file_xyz.xml")

    def test_pretty(self, xml_full):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".xml", delete=False, encoding="utf-8"
        ) as f:
            f.write(xml_full)
            tmp = f.name
        try:
            result = jsonify.dumps_file(tmp, pretty=True)
            assert "\n" in result
            json.loads(result)
        finally:
            os.unlink(tmp)


# ---------------------------------------------------------------------------
# 3. dumps_obj (ObjectifiedElement)
# ---------------------------------------------------------------------------

class TestDumpsObj:

    def test_root(self, root):
        d = json.loads(jsonify.dumps_obj(root))
        assert "database" in d

    def test_subtree(self, root):
        d = json.loads(jsonify.dumps_obj(root.user_profile))
        assert "user-profile" in d
        assert d["user-profile"]["first_name"] == "Mohammad"
        assert d["user-profile"]["@id"] == "101"

    def test_leaf_node(self, root):
        d = json.loads(jsonify.dumps_obj(root.user_profile.first_name))
        assert d["first_name"] == "Mohammad"

    def test_wrong_type_raises(self):
        with pytest.raises(TypeError):
            jsonify.dumps_obj("not an element")

    def test_pretty(self, root):
        result = jsonify.dumps_obj(root, pretty=True)
        assert "\n" in result
        json.loads(result)

    def test_namespaced_element(self):
        xml = '<root xmlns:ns="http://ns.com"><ns:item>x</ns:item></root>'
        r = objectify.from_string(xml)
        d = json.loads(jsonify.dumps_obj(r))
        assert "root" in d


# ---------------------------------------------------------------------------
# 4. dumps_node (XMLNode)
# ---------------------------------------------------------------------------

class TestDumpsNode:

    def test_root_node(self, doc):
        d = json.loads(jsonify.dumps_node(doc.root))
        assert "database" in d

    def test_child_node(self, doc):
        child = doc.root.child("user-profile")
        d = json.loads(jsonify.dumps_node(child))
        assert "user-profile" in d

    def test_wrong_type_raises(self):
        with pytest.raises(TypeError):
            jsonify.dumps_node("not a node")

    def test_wrong_type_objectified_raises(self, root):
        # ObjectifiedElement is not XMLNode — use dumps_obj for that
        with pytest.raises(TypeError):
            jsonify.dumps_node(root)

    def test_pretty(self, doc):
        result = jsonify.dumps_node(doc.root, pretty=True)
        assert "\n" in result
        json.loads(result)


# ---------------------------------------------------------------------------
# 5. dumps — smart dispatcher
# ---------------------------------------------------------------------------

class TestDumpsDispatcher:

    def test_routes_xml_string(self, xml_simple):
        d = p(xml_simple)
        assert "root" in d

    def test_routes_objectified_element(self, root):
        d = p(root)
        assert "database" in d

    def test_routes_objectified_subtree(self, root):
        d = p(root.user_profile)
        assert "user-profile" in d

    def test_routes_xmlnode(self, doc):
        d = p(doc.root)
        assert "database" in d

    def test_str_without_angle_raises_value_error(self):
        with pytest.raises(ValueError, match="<"):
            jsonify.dumps("data.xml")

    def test_wrong_type_raises_type_error(self):
        with pytest.raises(TypeError):
            jsonify.dumps(12345)

    def test_file_not_routed_through_dumps(self, xml_full):
        # dumps does NOT accept file paths — must use dumps_file
        with pytest.raises((ValueError, TypeError)):
            jsonify.dumps("data.xml")

    def test_options_passed_through(self, xml_simple):
        result = jsonify.dumps(xml_simple, pretty=True)
        assert "\n" in result

    def test_force_list_passed_through(self):
        xml = "<r><x>one</x></r>"
        d = p(xml, force_list={"x"})
        assert d["r"]["x"] == ["one"]


# ---------------------------------------------------------------------------
# 6. Consistency with dictify
# ---------------------------------------------------------------------------

class TestConsistencyWithDictify:

    def test_dumps_str_matches_dictify(self, xml_full):
        from pygixml import dictify
        assert dictify.parse(xml_full) == json.loads(jsonify.dumps_str(xml_full))

    def test_dumps_obj_matches_dictify(self, xml_full, root):
        from pygixml import dictify
        assert dictify.parse(xml_full) == json.loads(jsonify.dumps_obj(root))

    def test_dumps_node_matches_dictify(self, xml_full, doc):
        from pygixml import dictify
        assert dictify.parse(xml_full) == json.loads(jsonify.dumps_node(doc.root))

    def test_dumps_dispatcher_matches_dictify(self, xml_full):
        from pygixml import dictify
        assert dictify.parse(xml_full) == p(xml_full)


# ---------------------------------------------------------------------------
# 7. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_empty_element(self):
        assert json.loads(jsonify.dumps_str("<root/>")) == {"root": None}

    def test_deeply_nested(self):
        xml = "<a><b><c><d><e>deep</e></d></c></b></a>"
        d = json.loads(jsonify.dumps_str(xml))
        assert d["a"]["b"]["c"]["d"]["e"] == "deep"

    def test_numeric_attr_stays_string(self):
        d = json.loads(jsonify.dumps_str('<r n="42"/>'))
        assert isinstance(d["r"]["@n"], str)

    def test_compact_no_newlines(self, xml_full):
        assert "\n" not in jsonify.dumps_str(xml_full, pretty=False)

    def test_custom_indent(self, xml_simple):
        result = jsonify.dumps_str(xml_simple, pretty=True, indent="  ")
        assert "  " in result
        json.loads(result)
