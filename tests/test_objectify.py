"""
Tests for pygixml.objectify (cdef class implementation in pygixml_cy.pyx).

Run with:
    pytest tests/test_objectify.py -v
"""

import os
import tempfile

import pytest

from pygixml import objectify


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def xml_database():
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
def root(xml_database):
    return objectify.from_string(xml_database)


@pytest.fixture
def xml_nested():
    return """
<root>
    <item>a</item>
    <group>
        <item>b</item>
        <item>c</item>
    </group>
    <item>d</item>
</root>
"""

@pytest.fixture
def root_nested(xml_nested):
    return objectify.from_string(xml_nested)


# ---------------------------------------------------------------------------
# 1. Entry points
# ---------------------------------------------------------------------------

class TestEntryPoints:

    def test_from_string_returns_objectified_element(self, root):
        assert isinstance(root, objectify.ObjectifiedElement)

    def test_from_string_root_tag(self, root):
        assert root.tag == "database"

    def test_from_file_roundtrip(self, xml_database):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".xml", delete=False, encoding="utf-8"
        ) as f:
            f.write(xml_database)
            tmp = f.name
        try:
            loaded = objectify.from_file(tmp)
            assert isinstance(loaded, objectify.ObjectifiedElement)
            assert loaded.tag == "database"
        finally:
            os.unlink(tmp)

    def test_from_string_malformed_raises(self):
        with pytest.raises(Exception):
            objectify.from_string("not < valid > xml <<<")

    def test_from_file_missing_raises(self):
        with pytest.raises(Exception):
            objectify.from_file("/no/such/file_xyz_abc.xml")


# ---------------------------------------------------------------------------
# 2. Dotted navigation
# ---------------------------------------------------------------------------

class TestDottedNavigation:

    def test_single_child_returns_element(self, root):
        assert isinstance(root.user_profile, objectify.ObjectifiedElement)

    def test_nested_child(self, root):
        assert isinstance(root.user_profile.first_name, objectify.ObjectifiedElement)

    def test_missing_child_raises_attribute_error(self, root):
        with pytest.raises(AttributeError):
            _ = root.does_not_exist

    def test_missing_nested_raises_attribute_error(self, root):
        with pytest.raises(AttributeError):
            _ = root.user_profile.ghost


# ---------------------------------------------------------------------------
# 3. Hyphen / underscore mapping
# ---------------------------------------------------------------------------

class TestHyphenMapping:

    def test_underscore_finds_hyphen_tag(self, root):
        assert root.user_profile.tag == "user-profile"

    def test_direct_underscore_tag_wins(self):
        xml = "<root><a_b>underscore</a_b><a-b>hyphen</a-b></root>"
        r = objectify.from_string(xml)
        assert str(r.a_b) == "underscore"

    def test_only_hyphen_exists(self):
        xml = "<root><foo-bar>hello</foo-bar></root>"
        r = objectify.from_string(xml)
        assert str(r.foo_bar) == "hello"

    def test_attribute_hyphen_mapping(self):
        xml = '<root data-id="42"/>'
        r = objectify.from_string(xml)
        assert r.data_id == 42


# ---------------------------------------------------------------------------
# 4. Attribute access and type inference
# ---------------------------------------------------------------------------

class TestAttributeAccess:

    def test_string_attribute(self, root):
        assert root.name == "users_db"

    def test_float_attribute(self, root):
        val = root.version
        assert val == 1.2
        assert isinstance(val, float)

    def test_int_attribute(self, root):
        val = root.user_profile.id
        assert val == 101
        assert isinstance(val, int)

    def test_bool_true_attribute(self, root):
        assert root.user_profile.verified is True

    def test_bool_false_attribute(self):
        r = objectify.from_string('<root active="false"/>')
        assert r.active is False

    def test_bool_case_insensitive(self):
        r = objectify.from_string('<root a="True" b="FALSE" c="TRUE"/>')
        assert r.a is True
        assert r.b is False
        assert r.c is True

    def test_integer_string_becomes_int(self):
        r = objectify.from_string('<root count="7"/>')
        assert r.count == 7
        assert isinstance(r.count, int)

    def test_float_string_becomes_float(self):
        r = objectify.from_string('<root ratio="3.14"/>')
        val = r.ratio
        assert abs(val - 3.14) < 1e-9
        assert isinstance(val, float)

    def test_plain_string_stays_string(self):
        r = objectify.from_string('<root label="hello"/>')
        assert r.label == "hello"
        assert isinstance(r.label, str)


# ---------------------------------------------------------------------------
# 5. Type inference for leaf-node text
# ---------------------------------------------------------------------------

class TestTypeInferenceText:

    def test_call_returns_float(self, root):
        val = root.user_profile.balance()
        assert val == 450.75
        assert isinstance(val, float)

    def test_call_returns_str(self, root):
        val = root.user_profile.first_name()
        assert val == "Mohammad"
        assert isinstance(val, str)

    def test_call_returns_int_text(self):
        r = objectify.from_string("<root><count>42</count></root>")
        assert r.count() == 42
        assert isinstance(r.count(), int)

    def test_call_returns_bool_text(self):
        r = objectify.from_string("<root><flag>true</flag></root>")
        assert r.flag() is True

    def test_call_empty_node_returns_none(self):
        r = objectify.from_string("<root><empty/></root>")
        assert r.empty() is None


# ---------------------------------------------------------------------------
# 6. str() access
# ---------------------------------------------------------------------------

class TestStrAccess:

    def test_str_returns_text(self, root):
        assert str(root.user_profile.first_name) == "Mohammad"

    def test_str_always_returns_string_type(self, root):
        assert isinstance(str(root.user_profile.balance), str)

    def test_str_empty_node_returns_empty_string(self):
        r = objectify.from_string("<root><empty/></root>")
        assert str(r.empty) == ""


# ---------------------------------------------------------------------------
# 7. Sequence handling (NodeSequence)
# ---------------------------------------------------------------------------

class TestSequenceHandling:

    def test_multiple_siblings_return_node_sequence(self, root):
        assert isinstance(root.entry, objectify.NodeSequence)

    def test_node_sequence_len(self, root):
        assert len(root.entry) == 3

    def test_index_zero(self, root):
        assert str(root.entry[0]) == "Value A"

    def test_index_one(self, root):
        assert str(root.entry[1]) == "Value B"

    def test_index_two(self, root):
        assert str(root.entry[2]) == "Value C"

    def test_negative_index(self, root):
        assert str(root.entry[-1]) == "Value C"

    def test_iteration(self, root):
        assert [str(e) for e in root.entry] == ["Value A", "Value B", "Value C"]

    def test_single_child_is_element_not_sequence(self, root):
        assert isinstance(root.user_profile, objectify.ObjectifiedElement)

    def test_sequence_bool_true(self, root):
        assert bool(root.entry) is True

    def test_sequence_bool_false_empty(self):
        seq = objectify.NodeSequence([])
        assert bool(seq) is False

    def test_sequence_call_single_item(self):
        r = objectify.from_string("<root><x>3.5</x></root>")
        assert r.x() == 3.5

    def test_sequence_call_multi_raises(self, root):
        with pytest.raises(TypeError):
            root.entry()

    def test_sequence_index_out_of_range(self, root):
        with pytest.raises(IndexError):
            _ = root.entry[99]


# ---------------------------------------------------------------------------
# 8. Conflict resolution: child beats attribute
# ---------------------------------------------------------------------------

class TestConflictResolution:

    def test_child_beats_attribute(self):
        xml = '<root name="attr_value"><name>child_value</name></root>'
        r = objectify.from_string(xml)
        assert isinstance(r.name, objectify.ObjectifiedElement)
        assert str(r.name) == "child_value"

    def test_attribute_still_accessible_via_attrib(self):
        xml = '<root name="attr_value"><name>child_value</name></root>'
        r = objectify.from_string(xml)
        assert r.attrib["name"] == "attr_value"


# ---------------------------------------------------------------------------
# 9. ObjectifiedElement properties
# ---------------------------------------------------------------------------

class TestElementProperties:

    def test_tag_property(self, root):
        assert root.tag == "database"

    def test_attrib_dict(self, root):
        d = root.attrib
        assert isinstance(d, dict)
        assert d["name"] == "users_db"
        assert d["version"] == 1.2

    def test_attrib_type_inference(self, root):
        d = root.user_profile.attrib
        assert d["id"] == 101
        assert d["verified"] is True

    def test_attrib_empty(self):
        r = objectify.from_string("<root/>")
        assert r.attrib == {}

    def test_xml_property_contains_tag(self, root):
        assert "database" in root.xml
        assert "user-profile" in root.xml

    def test_text_content_property(self, root):
        assert root.user_profile.first_name.text_content == "Mohammad"


# ---------------------------------------------------------------------------
# 10. Iteration and len
# ---------------------------------------------------------------------------

class TestIterationAndLen:

    def test_iter_yields_elements(self, root):
        tags = [child.tag for child in root]
        assert "user-profile" in tags
        assert tags.count("entry") == 3

    def test_len(self, root):
        assert len(root) == 4  # user-profile + 3 entries

    def test_len_leaf_node(self, root):
        assert len(root.user_profile.first_name) == 0

    def test_bool_non_null(self, root):
        assert bool(root) is True

    def test_missing_attr_raises_not_returns_falsy(self):
        r = objectify.from_string("<root/>")
        with pytest.raises(AttributeError):
            _ = r.missing


# ---------------------------------------------------------------------------
# 11. Equality
# ---------------------------------------------------------------------------

class TestEquality:

    def test_same_node_equal(self):
        r = objectify.from_string("<root><item/></root>")
        assert r.item == r.item

    def test_different_nodes_not_equal(self, root):
        assert root.user_profile != root.entry[0]

    def test_not_equal_to_non_element(self, root):
        assert root != "database"


# ---------------------------------------------------------------------------
# 12. Document lifetime (GC safety)
# ---------------------------------------------------------------------------

class TestDocumentLifetime:

    def test_doc_ref_survives_gc(self):
        import gc
        root = objectify.from_string("<root><child>alive</child></root>")
        gc.collect()
        assert str(root.child) == "alive"

    def test_nested_access_after_gc(self, xml_database):
        import gc
        root = objectify.from_string(xml_database)
        up = root.user_profile
        gc.collect()
        assert str(up.first_name) == "Mohammad"


# ---------------------------------------------------------------------------
# 13. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_numeric_zero_attribute(self):
        r = objectify.from_string('<root count="0"/>')
        assert r.count == 0
        assert isinstance(r.count, int)

    def test_negative_number_attribute(self):
        r = objectify.from_string('<root delta="-3.5"/>')
        assert r.delta == -3.5

    def test_scientific_notation_attribute(self):
        r = objectify.from_string('<root eps="1e-5"/>')
        assert abs(r.eps - 1e-5) < 1e-15

    def test_unicode_text(self):
        r = objectify.from_string("<root><city>تهران</city></root>")
        assert str(r.city) == "تهران"

    def test_empty_root(self):
        r = objectify.from_string("<root/>")
        assert len(r) == 0
        assert list(r) == []

    def test_deeply_nested(self):
        r = objectify.from_string("<a><b><c><d><e>deep</e></d></c></b></a>")
        assert str(r.b.c.d.e) == "deep"

    def test_whitespace_text_stripped_by_infer(self):
        r = objectify.from_string("<root><n>  42  </n></root>")
        assert r.n() == 42

    def test_repr_contains_tag(self, root):
        assert "database" in repr(root)

    def test_node_sequence_repr(self, root):
        assert "NodeSequence" in repr(root.entry)

    def test_cdef_class_has_no_dict(self, root):
        assert not hasattr(root, "__dict__")


# ---------------------------------------------------------------------------
# 14. get() — safe attribute access
# ---------------------------------------------------------------------------

class TestGet:

    def test_get_existing_int(self, root):
        assert root.user_profile.get("id") == 101

    def test_get_existing_bool(self, root):
        assert root.user_profile.get("verified") is True

    def test_get_existing_string(self, root):
        assert root.get("name") == "users_db"

    def test_get_missing_returns_none(self, root):
        assert root.get("no_such_attr") is None

    def test_get_missing_returns_default(self, root):
        assert root.get("no_such_attr", -1) == -1

    def test_get_missing_default_zero(self, root):
        assert root.get("missing", 0) == 0

    def test_get_missing_default_false(self, root):
        assert root.get("missing", False) is False

    def test_get_hyphen_mapping(self):
        r = objectify.from_string('<root data-id="7"/>')
        assert r.get("data_id") == 7

    def test_get_does_not_find_child_elements(self, root):
        assert root.get("entry") is None
        assert root.get("entry", "nope") == "nope"

    def test_get_never_raises(self, root):
        assert root.get("__totally_missing__", "safe") == "safe"

    def test_get_type_inference(self):
        r = objectify.from_string('<r x="3.14" y="0" z="false"/>')
        assert isinstance(r.get("x"), float)
        assert r.get("y") == 0
        assert r.get("z") is False


# ---------------------------------------------------------------------------
# 15. find() — first matching descendant
# ---------------------------------------------------------------------------

class TestFind:

    def test_find_direct_child(self, root):
        result = root.find("entry")
        assert isinstance(result, objectify.ObjectifiedElement)
        assert str(result) == "Value A"

    def test_find_deep(self, root):
        result = root.find("first_name")
        assert result is not None
        assert str(result) == "Mohammad"

    def test_find_missing_returns_none(self, root):
        assert root.find("no_such_tag") is None

    def test_find_non_recursive_direct_hit(self, root):
        result = root.find("entry", recursive=False)
        assert result is not None
        assert str(result) == "Value A"

    def test_find_non_recursive_misses_deep(self, root):
        assert root.find("first_name", recursive=False) is None

    def test_find_hyphen_mapping(self, root):
        result = root.find("user_profile")
        assert result is not None
        assert result.tag == "user-profile"

    def test_find_returns_first(self):
        r = objectify.from_string("<root><item>first</item><item>second</item></root>")
        assert str(r.find("item")) == "first"

    def test_find_deeply_nested(self):
        r = objectify.from_string("<a><b><c><d><target>deep</target></d></c></b></a>")
        assert str(r.find("target")) == "deep"

    def test_find_on_leaf_returns_none(self, root):
        assert root.user_profile.first_name.find("anything") is None


# ---------------------------------------------------------------------------
# 16. findall() — all matching descendants
# ---------------------------------------------------------------------------

class TestFindAll:

    def test_findall_direct_children(self, root):
        results = root.findall("entry", recursive=False)
        assert [str(r) for r in results] == ["Value A", "Value B", "Value C"]

    def test_findall_recursive(self, root_nested):
        results = root_nested.findall("item")
        assert [str(x) for x in results] == ["a", "b", "c", "d"]

    def test_findall_non_recursive_skips_nested(self, root_nested):
        results = root_nested.findall("item", recursive=False)
        assert [str(x) for x in results] == ["a", "d"]

    def test_findall_missing_returns_empty(self, root):
        assert root.findall("no_such_tag") == []

    def test_findall_hyphen_mapping(self, root):
        results = root.findall("user_profile")
        assert len(results) == 1
        assert results[0].tag == "user-profile"

    def test_findall_returns_objectified_elements(self, root):
        for elem in root.findall("entry"):
            assert isinstance(elem, objectify.ObjectifiedElement)

    def test_findall_document_order(self):
        r = objectify.from_string("<root><x>1</x><y><x>2</x></y><x>3</x></root>")
        assert [str(x) for x in r.findall("x")] == ["1", "2", "3"]

    def test_findall_on_leaf_returns_empty(self, root):
        assert root.user_profile.first_name.findall("anything") == []


# ---------------------------------------------------------------------------
# 17. __setattr__ — write support
# ---------------------------------------------------------------------------

@pytest.fixture
def mutable():
    return objectify.from_string("""
<database version="1.0">
    <host>localhost</host>
    <port>5432</port>
    <user-profile id="101" verified="true">
        <first_name>Mohammad</first_name>
        <balance>450.75</balance>
    </user-profile>
</database>
""")


class TestSetAttr:

    def test_set_child_text_content(self, mutable):
        mutable.host = "newhost"
        assert str(mutable.host) == "newhost"

    def test_set_child_accepts_int(self, mutable):
        mutable.port = 9999
        assert str(mutable.port) == "9999"

    def test_set_child_accepts_float(self, mutable):
        mutable.port = 3.14
        assert str(mutable.port) == "3.14"

    def test_set_child_accepts_bool(self, mutable):
        mutable.host = True
        assert str(mutable.host) == "True"

    def test_set_existing_attribute(self, mutable):
        mutable.version = "2.0"
        # type inference converts "2.0" back to float on read — that's correct
        assert mutable.version == 2.0

    def test_set_attribute_int_stored_as_string(self, mutable):
        mutable.version = 3
        assert mutable.version == 3   # type-inferred back on read

    def test_set_creates_new_child_when_missing(self, mutable):
        mutable.timeout = 30
        assert str(mutable.timeout) == "30"

    def test_new_child_is_element_not_attribute(self, mutable):
        mutable.newkey = "val"
        assert isinstance(mutable.newkey, objectify.ObjectifiedElement)

    def test_set_nested_child(self, mutable):
        mutable.user_profile.first_name = "Ali"
        assert str(mutable.user_profile.first_name) == "Ali"

    def test_set_hyphen_tag(self, mutable):
        # user_profile → <user-profile>, sets its text? No — sets child text.
        # Here we test that hyphen mapping works for attribute set
        mutable.user_profile.id = 999
        assert mutable.user_profile.id == 999

    def test_set_child_priority_over_attribute(self):
        # When both child and attribute share a name, child wins for set too
        xml = '<root name="attr"><name>child</name></root>'
        r = objectify.from_string(xml)
        r.name = "updated"
        assert str(r.name) == "updated"       # child updated
        assert r.attrib["name"] == "attr"     # attribute untouched

    def test_set_does_not_create_duplicate_children(self, mutable):
        mutable.host = "first"
        mutable.host = "second"
        assert len(mutable.findall("host", recursive=False)) == 1
        assert str(mutable.host) == "second"

    def test_set_reserved_names_do_not_touch_xml(self, mutable):
        # _node and _doc_ref are cdef fields — setting them via __setattr__
        # must not forward to XML. Verify by checking no XML child is created.
        before_len = len(mutable)
        try:
            mutable._doc_ref = None   # should go to object, not XML
        except (AttributeError, TypeError):
            pass  # cdef class may reject it — that's also fine
        assert len(mutable) == before_len   # no new child was created

    def test_xml_reflects_change(self, mutable):
        mutable.host = "changed"
        assert "changed" in mutable.xml

    def test_set_preserves_siblings(self, mutable):
        # setting host should not affect other children
        mutable.host = "x"
        assert str(mutable.port) == "5432"


# ---------------------------------------------------------------------------
# 18. __delattr__ — delete support
# ---------------------------------------------------------------------------

class TestDelAttr:

    def test_delete_child_element(self, mutable):
        del mutable.host
        assert mutable.find("host") is None

    def test_delete_attribute(self, mutable):
        del mutable.version
        assert mutable.get("version") is None

    def test_delete_hyphen_child(self, mutable):
        del mutable.user_profile
        assert mutable.find("user_profile") is None

    def test_delete_hyphen_attribute(self, mutable):
        del mutable.user_profile.verified
        assert mutable.user_profile.get("verified") is None

    def test_delete_missing_raises_attribute_error(self, mutable):
        with pytest.raises(AttributeError):
            del mutable.no_such_thing

    def test_delete_child_priority_over_attribute(self):
        xml = '<root name="attr"><name>child</name></root>'
        r = objectify.from_string(xml)
        del r.name                        # child removed
        assert r.find("name") is None
        assert r.attrib["name"] == "attr" # attribute still there

    def test_delete_reduces_len(self, mutable):
        before = len(mutable)
        del mutable.host
        assert len(mutable) == before - 1

    def test_xml_reflects_delete(self, mutable):
        del mutable.host
        assert "<host>" not in mutable.xml
        