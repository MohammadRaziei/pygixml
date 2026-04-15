#!/usr/bin/env python3
"""
Tests for attribute manipulation methods: append_attribute, prepend_attribute, remove_attribute
"""

import pytest
import pygixml


class TestAttributeMethods:
    """Test attribute manipulation methods"""

    def setup_method(self):
        """Setup test XML document"""
        self.xml_string = """
        <root>
            <item id="1" class="test">Content</item>
        </root>
        """
        self.doc = pygixml.parse_string(self.xml_string)
        self.root = self.doc.first_child()
        self.item = self.root.child("item")

    def test_first_attribute(self):
        """Test getting the first attribute"""
        # Tests getting the first attribute from a XMLNode
        attribute = self.item.first_attribute()
        assert attribute is not None
        assert attribute.name == "id"
        assert attribute.value == "1"

    def test_append_attribute(self):
        """Test appending attributes to a node"""
        # Test appending a new attribute
        new_attr = self.item.append_attribute("data-id")
        assert new_attr is not None
        assert new_attr.name == "data-id"

        # Set value and verify
        new_attr.value = "123"
        assert new_attr.value == "123"

        # Verify attribute exists in the node
        found_attr = self.item.attribute("data-id")
        assert found_attr is not None
        assert found_attr.value == "123"

    def test_prepend_attribute(self):
        """Test prepending attributes to a node"""
        # Test prepending a new attribute
        new_attr = self.item.prepend_attribute("priority")
        assert new_attr is not None
        assert new_attr.name == "priority"

        # Set value and verify
        new_attr.value = "high"
        assert new_attr.value == "high"

        # Verify attribute exists in the node
        found_attr = self.item.attribute("priority")
        assert found_attr is not None
        assert found_attr.value == "high"

        # Verify prepend worked by checking attribute order
        # The first attribute should be the one we prepended
        first_attr = self.item.first_attribute()
        assert first_attr.name == "priority"

    def test_remove_attribute(self):
        """Test removing attributes from a node"""
        # Test removing an existing attribute
        id_attr = self.item.attribute("id")
        assert id_attr is not None

        # Remove the attribute
        result = self.item.remove_attribute(id_attr)
        assert result is True

        # Verify attribute is removed
        removed_attr = self.item.attribute("id")
        assert removed_attr is not None
        assert not removed_attr  # Empty attribute evaluates to False

    def test_remove_nonexistent_attribute(self):
        """Test removing an attribute that doesn't exist"""
        # Create a new attribute that's not attached to any node
        fake_attr = pygixml.XMLAttribute()

        # Try to remove it (should fail gracefully)
        result = self.item.remove_attribute(fake_attr)
        assert result is False

    def test_append_multiple_attributes(self):
        """Test appending multiple attributes"""
        # Add multiple attributes
        attr1 = self.item.append_attribute("attr1")
        attr2 = self.item.append_attribute("attr2")
        attr3 = self.item.append_attribute("attr3")

        # Set values
        attr1.value = "value1"
        attr2.value = "value2"
        attr3.value = "value3"

        # Verify all attributes exist
        assert self.item.attribute("attr1").value == "value1"
        assert self.item.attribute("attr2").value == "value2"
        assert self.item.attribute("attr3").value == "value3"

    def test_prepend_multiple_attributes(self):
        """Test prepending multiple attributes"""
        # Add multiple attributes by prepending
        attr1 = self.item.prepend_attribute("first")
        attr2 = self.item.prepend_attribute("second")
        attr3 = self.item.prepend_attribute("third")

        # Set values
        attr1.value = "1"
        attr2.value = "2"
        attr3.value = "3"

        # Verify order: third should be first, then second, then first
        first_attr = self.item.first_attribute()
        assert first_attr.name == "third"
        assert first_attr.value == "3"

        # Get second attribute
        second_attr = first_attr.next_attribute
        assert second_attr.name == "second"
        assert second_attr.value == "2"

    def test_attribute_operations_on_empty_node(self):
        """Test attribute operations on a node with no attributes"""
        # Create a new node with no attributes
        new_node = self.root.append_child("empty_node")

        # Append an attribute
        new_attr = new_node.append_attribute("new_attr")
        assert new_attr is not None
        assert new_attr.name == "new_attr"

        # Verify it's the first attribute
        first_attr = new_node.first_attribute()
        assert first_attr.name == "new_attr"

        # Remove it
        result = new_node.remove_attribute(new_attr)
        assert result is True

        # Verify it's gone
        assert not new_node.first_attribute()

    def test_attribute_methods_with_special_characters(self):
        """Test attribute methods with special characters in names"""
        # Test with various special characters
        special_names = ["data-test", "test:attr", "test_attr", "test.attr"]

        for name in special_names:
            attr = self.item.append_attribute(name)
            assert attr is not None
            assert attr.name == name

            # Set and verify value
            attr.value = f"value_{name}"
            assert attr.value == f"value_{name}"

            # Verify we can find it
            found_attr = self.item.attribute(name)
            assert found_attr is not None
            assert found_attr.value == f"value_{name}"

            # Remove it
            result = self.item.remove_attribute(attr)
            assert result is True

    def test_attribute_roundtrip(self):
        """Test creating, modifying, and removing attributes"""
        # Create attribute
        attr = self.item.append_attribute("temp")
        attr.value = "temporary"

        # Verify it exists
        assert self.item.attribute("temp").value == "temporary"

        # Modify value
        attr.value = "modified"
        assert self.item.attribute("temp").value == "modified"

        # Remove it
        result = self.item.remove_attribute(attr)
        assert result is True

        # Verify it's gone
        assert not self.item.attribute("temp")

    def test_attribute_serialization(self):
        """Test that attributes are properly serialized"""
        # Add some attributes
        self.item.append_attribute("extra1").value = "val1"
        self.item.append_attribute("extra2").value = "val2"

        # Serialize to string
        xml_str = self.doc.to_string()

        # Verify attributes are in the output
        assert 'extra1="val1"' in xml_str
        assert 'extra2="val2"' in xml_str

        # Verify original attributes are still there
        assert 'id="1"' in xml_str
        assert 'class="test"' in xml_str


class TestAttributeEdgeCases:
    """Test edge cases for attribute methods"""

    def test_empty_attribute_name(self):
        """Test attribute operations with empty names"""
        doc = pygixml.XMLDocument()
        root = doc.append_child("root")

        # Try to append attribute with empty name
        # This should create an attribute, but the behavior may vary
        attr = root.append_attribute("")
        assert attr is not None

        # The name might be empty or the operation might fail
        # We'll just verify we get an attribute object back

    def test_unicode_attribute_names(self):
        """Test attribute operations with Unicode names"""
        doc = pygixml.XMLDocument()
        root = doc.append_child("root")

        # Test with Unicode characters
        unicode_names = ["测试", "тест", "اختبار", "🎉"]

        for name in unicode_names:
            attr = root.append_attribute(name)
            assert attr is not None
            assert attr.name == name

            attr.value = f"value_{name}"
            assert attr.value == f"value_{name}"

    def test_many_attributes(self):
        """Test operations with many attributes"""
        doc = pygixml.XMLDocument()
        root = doc.append_child("root")

        # Add many attributes
        num_attrs = 50
        for i in range(num_attrs):
            attr = root.append_attribute(f"attr{i}")
            attr.value = f"value{i}"

        # Verify we can access them all
        attr = root.first_attribute()
        count = 0
        while attr:
            count += 1
            attr = attr.next_attribute

        assert count == num_attrs

        # Remove some attributes
        for i in range(0, num_attrs, 2):  # Remove every other attribute
            attr_to_remove = root.attribute(f"attr{i}")
            if attr_to_remove:
                root.remove_attribute(attr_to_remove)

        # Count remaining attributes
        attr = root.first_attribute()
        remaining = 0
        while attr:
            remaining += 1
            attr = attr.next_attribute

        # Should have removed about half
        assert remaining == num_attrs // 2


class TestAttributeIntegration:
    """Test attribute methods in integration scenarios"""

    def test_build_element_with_attributes(self):
        """Test building an element with multiple attributes"""
        doc = pygixml.XMLDocument()
        root = doc.append_child("configuration")

        # Add an element with attributes
        settings = root.append_child("settings")

        # Add attributes using different methods
        settings.append_attribute("version").value = "1.0"
        settings.prepend_attribute("priority").value = "high"
        settings.append_attribute("enabled").value = "true"

        # Verify attributes
        assert settings.attribute("version").value == "1.0"
        assert settings.attribute("priority").value == "high"
        assert settings.attribute("enabled").value == "true"

        # Verify order (priority should be first)
        first_attr = settings.first_attribute()
        assert first_attr.name == "priority"

        second_attr = first_attr.next_attribute
        assert second_attr.name == "version"

    def test_modify_existing_document_attributes(self):
        """Test modifying attributes in an existing document"""
        xml_string = '<root><item id="1" class="test">Content</item></root>'

        doc = pygixml.parse_string(xml_string)
        item = doc.root.child("item")

        # Modify existing attributes
        item.attribute("class").value = "test modified"

        # Add new attributes
        item.append_attribute("data-new").value = "value"
        item.prepend_attribute("priority").value = "high"

        # Remove an attribute
        id_attr = item.attribute("id")
        removed = item.remove_attribute(id_attr)
        assert removed is True

        # Verify changes
        assert item.attribute("class").value == "test modified"
        assert item.attribute("data-new").value == "value"
        assert item.attribute("priority").value == "high"
        assert not item.attribute("id")  # Removed attribute

        # Verify attribute order
        first_attr = item.first_attribute()
        assert first_attr.name == "priority"

    def test_attribute_operations_preserve_structure(self):
        """Test that attribute operations don't affect node structure"""
        xml_string = """
        <root>
            <parent>
                <child1 attr1="value1">Content1</child1>
                <child2 attr2="value2">Content2</child2>
            </parent>
        </root>
        """

        doc = pygixml.parse_string(xml_string)
        parent = doc.root.child("parent")
        child1 = parent.child("child1")
        child2 = parent.child("child2")

        # Perform attribute operations
        child1.append_attribute("new_attr").value = "new_value"
        child1.remove_attribute(child1.attribute("attr1"))

        child2.prepend_attribute("priority").value = "high"

        # Verify structure is preserved
        assert parent.child("child1") is not None
        assert parent.child("child2") is not None
        assert child1.child_value() == "Content1"
        assert child2.child_value() == "Content2"

        # Verify sibling relationships
        assert child1.next_sibling == child2
        assert child2.previous_sibling == child1
