#!/usr/bin/env python3
"""
Tests for pygixml.objectify — lxml.objectify-style interface.

Run with:
    pytest tests/test_objectify.py -v
"""

import os
import tempfile

import pytest

# The module lives at src/pygixml/objectify.py, installed as pygixml.objectify
from pygixml import objectify
from pygixml.objectify import ObjectifiedElement, NodeSequence


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

FULL_XML = """
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
def root():
    return objectify.from_string(FULL_XML)


# ---------------------------------------------------------------------------
# 1.  Entry points
# ---------------------------------------------------------------------------

class TestEntryPoints:
    """from_string and from_file return ObjectifiedElement."""

    def test_from_string_returns_objectified_element(self, root):
        assert isinstance(root, ObjectifiedElement)

    def test_from_string_root_tag(self, root):
        assert root.tag == "database"

    def test_from_file_roundtrip(self, root):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".xml", delete=False, encoding="utf-8"
        ) as f:
            f.write(FULL_XML)
            tmp = f.name
        try:
            loaded = objectify.from_file(tmp)
            assert isinstance(loaded, ObjectifiedElement)
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
# 2.  Dotted navigation (child elements)
# ---------------------------------------------------------------------------

class TestDottedNavigation:
    """Attribute access walks the child element tree."""

    def test_single_child_returns_element(self, root):
        up = root.user_profile
        assert isinstance(up, ObjectifiedElement)

    def test_nested_child(self, root):
        assert isinstance(root.user_profile.first_name, ObjectifiedElement)

    def test_missing_child_raises_attribute_error(self, root):
        with pytest.raises(AttributeError):
            _ = root.does_not_exist

    def test_missing_nested_raises_attribute_error(self, root):
        with pytest.raises(AttributeError):
            _ = root.user_profile.ghost


# ---------------------------------------------------------------------------
# 3.  Identifier mapping: underscores → hyphens
# ---------------------------------------------------------------------------

class TestHyphenMapping:
    """Python underscores are transparently mapped to XML hyphens."""

    def test_underscore_finds_hyphen_tag(self, root):
        # <user-profile> found via root.user_profile
        up = root.user_profile
        assert up.tag == "user-profile"

    def test_direct_underscore_tag_wins(self):
        # An actual underscore tag must win over the hyphen variant
        xml = "<root><a_b>underscore</a_b><a-b>hyphen</a-b></root>"
        r = objectify.from_string(xml)
        # a_b (literal) is tried first; it exists → return it, not a-b
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
# 4.  Attribute access and type inference
# ---------------------------------------------------------------------------

class TestAttributeAccess:
    """Attributes fall through from __getattr__ when no child matches."""

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
        val = root.user_profile.verified
        assert val is True
        assert isinstance(val, bool)

    def test_bool_false_attribute(self):
        xml = '<root active="false"/>'
        r = objectify.from_string(xml)
        val = r.active
        assert val is False
        assert isinstance(val, bool)

    def test_bool_case_insensitive(self):
        xml = '<root a="True" b="FALSE" c="TRUE"/>'
        r = objectify.from_string(xml)
        assert r.a is True
        assert r.b is False
        assert r.c is True

    def test_integer_string_becomes_int(self):
        xml = '<root count="7"/>'
        assert objectify.from_string(xml).count == 7

    def test_float_string_becomes_float(self):
        xml = '<root ratio="3.14"/>'
        val = objectify.from_string(xml).ratio
        assert abs(val - 3.14) < 1e-9
        assert isinstance(val, float)

    def test_plain_string_stays_string(self):
        xml = '<root label="hello"/>'
        val = objectify.from_string(xml).label
        assert val == "hello"
        assert isinstance(val, str)


# ---------------------------------------------------------------------------
# 5.  Type inference for leaf-node text
# ---------------------------------------------------------------------------

class TestTypeInferenceText:
    """Calling an element returns the type-inferred text content."""

    def test_call_returns_float(self, root):
        val = root.user_profile.balance()
        assert val == 450.75
        assert isinstance(val, float)

    def test_call_returns_str(self, root):
        val = root.user_profile.first_name()
        assert val == "Mohammad"
        assert isinstance(val, str)

    def test_call_returns_int_text(self):
        xml = "<root><count>42</count></root>"
        r = objectify.from_string(xml)
        assert r.count() == 42
        assert isinstance(r.count(), int)

    def test_call_returns_bool_text(self):
        xml = "<root><flag>true</flag></root>"
        r = objectify.from_string(xml)
        assert r.flag() is True

    def test_call_empty_node_returns_none(self):
        xml = "<root><empty/></root>"
        r = objectify.from_string(xml)
        assert r.empty() is None


# ---------------------------------------------------------------------------
# 6.  str() access
# ---------------------------------------------------------------------------

class TestStrAccess:
    """str(elem) always returns a plain string."""

    def test_str_returns_text(self, root):
        assert str(root.user_profile.first_name) == "Mohammad"

    def test_str_on_float_node_returns_string(self, root):
        result = str(root.user_profile.balance)
        # It's a string, not a float
        assert isinstance(result, str)
        assert "450.75" in result

    def test_str_empty_node_returns_empty_string(self):
        xml = "<root><empty/></root>"
        r = objectify.from_string(xml)
        assert str(r.empty) == ""


# ---------------------------------------------------------------------------
# 7.  Sequence handling: NodeSequence
# ---------------------------------------------------------------------------

class TestSequenceHandling:
    """Multiple same-name siblings produce a NodeSequence."""

    def test_multiple_siblings_return_node_sequence(self, root):
        assert isinstance(root.entry, NodeSequence)

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
        texts = [str(e) for e in root.entry]
        assert texts == ["Value A", "Value B", "Value C"]

    def test_single_child_returns_element_not_sequence(self, root):
        # user-profile appears only once → plain ObjectifiedElement
        assert isinstance(root.user_profile, ObjectifiedElement)

    def test_sequence_bool_true(self, root):
        assert bool(root.entry) is True

    def test_sequence_bool_false_empty():
        # Fabricate an empty sequence
        seq = NodeSequence([])
        assert bool(seq) is False

    def test_sequence_call_single_item(self):
        xml = "<root><x>3.5</x></root>"
        r = objectify.from_string(xml)
        # x appears once → ObjectifiedElement, calling it gives float
        assert r.x() == 3.5

    def test_sequence_call_multi_raises(self, root):
        with pytest.raises(TypeError):
            root.entry()

    def test_sequence_index_out_of_range(self, root):
        with pytest.raises(IndexError):
            _ = root.entry[99]


# ---------------------------------------------------------------------------
# 8.  Conflict resolution: children beat attributes
# ---------------------------------------------------------------------------

class TestConflictResolution:
    """When a child element and an attribute share a name, the child wins."""

    def test_child_beats_attribute(self):
        # <root name="attr_value"><name>child_value</name></root>
        xml = '<root name="attr_value"><name>child_value</name></root>'
        r = objectify.from_string(xml)
        result = r.name
        # Must be the child element, not the string "attr_value"
        assert isinstance(result, ObjectifiedElement)
        assert str(result) == "child_value"

    def test_attribute_accessed_directly_via_node(self):
        xml = '<root name="attr_value"><name>child_value</name></root>'
        r = objectify.from_string(xml)
        raw_attr = r._node.attribute("name")
        assert raw_attr.value == "attr_value"


# ---------------------------------------------------------------------------
# 9.  ObjectifiedElement properties
# ---------------------------------------------------------------------------

class TestElementProperties:
    """tag, text_content, attrib, xml properties."""

    def test_tag_property(self, root):
        assert root.tag == "database"

    def test_attrib_dict(self, root):
        d = root.attrib
        assert isinstance(d, dict)
        assert d["name"] == "users_db"
        assert d["version"] == 1.2

    def test_attrib_type_inference(self, root):
        up_attrib = root.user_profile.attrib
        assert up_attrib["id"] == 101
        assert up_attrib["verified"] is True

    def test_xml_property_contains_tag(self, root):
        xml_str = root.xml
        assert "database" in xml_str
        assert "user-profile" in xml_str

    def test_text_content_property(self, root):
        assert root.user_profile.first_name.text_content == "Mohammad"


# ---------------------------------------------------------------------------
# 10.  Iteration and len on ObjectifiedElement
# ---------------------------------------------------------------------------

class TestIterationAndLen:
    """__iter__ and __len__ walk direct child elements."""

    def test_iter_children(self, root):
        tags = [child.tag for child in root]
        # user-profile + entry + entry + entry = 4
        assert "user-profile" in tags
        assert tags.count("entry") == 3

    def test_len(self, root):
        assert len(root) == 4   # user-profile + 3 entries

    def test_len_leaf(self, root):
        assert len(root.user_profile.first_name) == 0

    def test_bool_non_null(self, root):
        assert bool(root) is True

    def test_bool_null_like(self):
        # A child that doesn't exist should raise AttributeError, not return falsy
        xml = "<root/>"
        r = objectify.from_string(xml)
        with pytest.raises(AttributeError):
            _ = r.missing


# ---------------------------------------------------------------------------
# 11.  Equality
# ---------------------------------------------------------------------------

class TestEquality:
    """Two wrappers around the same node compare equal."""

    def test_same_node_equal(self):
        xml = "<root><item/></root>"
        r = objectify.from_string(xml)
        a = r.item
        b = r.item
        assert a == b

    def test_different_nodes_not_equal(self, root):
        assert root.user_profile != root.entry[0]

    def test_not_equal_to_non_element(self, root):
        assert root != "database"


# ---------------------------------------------------------------------------
# 12.  Document lifetime (GC safety)
# ---------------------------------------------------------------------------

class TestDocumentLifetime:
    """The wrapper keeps the XMLDocument alive via _doc_ref."""

    def test_doc_ref_survives_gc(self):
        import gc
        root = objectify.from_string("<root><child>alive</child></root>")
        # Force a GC cycle; the document must not be collected
        gc.collect()
        assert str(root.child) == "alive"

    def test_nested_access_after_gc(self):
        import gc
        root = objectify.from_string(FULL_XML)
        up = root.user_profile
        gc.collect()
        assert str(up.first_name) == "Mohammad"


# ---------------------------------------------------------------------------
# 13.  Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Boundary conditions and unusual XML."""

    def test_numeric_zero_attribute(self):
        xml = '<root count="0"/>'
        r = objectify.from_string(xml)
        assert r.count == 0
        assert isinstance(r.count, int)

    def test_negative_number_attribute(self):
        xml = '<root delta="-3.5"/>'
        r = objectify.from_string(xml)
        assert r.delta == -3.5

    def test_scientific_notation_attribute(self):
        xml = '<root eps="1e-5"/>'
        r = objectify.from_string(xml)
        assert abs(r.eps - 1e-5) < 1e-15

    def test_unicode_text(self):
        xml = "<root><city>تهران</city></root>"
        r = objectify.from_string(xml)
        assert str(r.city) == "تهران"

    def test_empty_root(self):
        r = objectify.from_string("<root/>")
        assert len(r) == 0
        assert list(r) == []

    def test_deeply_nested(self):
        xml = "<a><b><c><d><e>deep</e></d></c></b></a>"
        r = objectify.from_string(xml)
        assert str(r.b.c.d.e) == "deep"

    def test_whitespace_text_stripped_by_infer(self):
        xml = "<root><n>  42  </n></root>"
        r = objectify.from_string(xml)
        # _infer_type strips before conversion
        assert r.n() == 42

    def test_attrib_empty(self):
        xml = "<root/>"
        r = objectify.from_string(xml)
        assert r.attrib == {}

    def test_repr_contains_tag(self, root):
        assert "database" in repr(root)

    def test_node_sequence_repr(self, root):
        assert "NodeSequence" in repr(root.entry)