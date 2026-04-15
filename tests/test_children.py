#!/usr/bin/env python3
"""
Tests for XMLNode.children() method
"""

import pygixml


class TestXMLNodeChildren:
    """Test XMLNode.children() method"""

    def test_children_direct(self):
        """children() should yield only direct child elements"""
        doc = pygixml.parse_string(
            "<class>"
            '<student id="1"/>'
            '<student id="2"/>'
            '<student id="3"/>'
            "</class>"
        )
        root = doc.root
        children = list(root.children())
        assert len(children) == 3
        assert [c.name for c in children] == ["student", "student", "student"]
        assert [c.attribute("id").value for c in children] == ["1", "2", "3"]

    def test_children_recursive(self):
        """children(True) should yield all descendant elements"""
        doc = pygixml.parse_string(
            "<root><a><a1/><a2/></a><b/></root>"
        )
        root = doc.root
        direct = [c.name for c in root.children()]
        assert direct == ["a", "b"]
        all_nodes = [c.name for c in root.children(True)]
        assert all_nodes == ["a", "a1", "a2", "b"]

    def test_children_skips_non_element(self):
        """children() should yield only element nodes"""
        doc = pygixml.parse_string("<root>text<a/><!--comment--><b/></root>")
        root = doc.root
        names = [c.name for c in root.children()]
        assert names == ["a", "b"]

    def test_children_empty(self):
        """children() on element with no children should yield nothing"""
        doc = pygixml.parse_string("<root/>")
        assert list(doc.root.children()) == []

    def test_children_vs_iteration(self):
        """children(True) and __iter__ should yield the same elements"""
        doc = pygixml.parse_string(
            "<root><a><a1/><a2/></a><b/></root>"
        )
        root = doc.root
        # __iter__ delegates to children(True)
        direct = list(root.children())
        all_iter = list(root)
        all_recursive = list(root.children(True))
        assert [c.name for c in all_iter] == [c.name for c in all_recursive]
        # direct children are a subset
        assert len(direct) == 2
        assert len(all_iter) == 4

    def test_children_with_attributes(self):
        """children() should return fully accessible nodes"""
        doc = pygixml.parse_string(
            '<class name="CS101">'
            '  <student id="001" firstName="Alice"/>'
            '  <student id="002" firstName="Bob"/>'
            '</class>'
        )
        root = doc.root
        students = list(root.children())
        assert len(students) == 2
        assert students[0].attribute("firstName").value == "Alice"
        assert students[1].attribute("firstName").value == "Bob"

    def test_prepend_child(self):
        doc = pygixml.parse_string(
            '<class name="CS101">'
            '  <student id="001" firstName="Alice"/>'
            '  <student id="002" firstName="Bob"/>'
            '</class>'
        )
        class_item = doc.first_child()
        new_student = class_item.prepend_child("student")
        attr = new_student.append_attribute("id")
        attr.set_value("007")

        elements = list(class_item.children())

        assert new_student is not None
        assert new_student.name == "student"
        assert new_student.attribute("id") is not None
        assert new_student.attribute("id").value == "007"
        assert len(elements) == 3
        assert elements[0].attribute("id") is not None
        assert elements[0].attribute("id").value == "007"

    def test_from_mem_id_unsafe_matches_find_mem_id(self):
        """from_mem_id_unsafe should produce the same node as find_mem_id"""
        doc = pygixml.parse_string("<root><item>Hello</item></root>")
        root = doc.root
        item = root.child("item")
        node_id = item.mem_id

        unsafe_node = pygixml.XMLNode.from_mem_id_unsafe(node_id)
        safe_node = root.find_mem_id(node_id)

        # Both should wrap the same underlying xml_node
        assert unsafe_node.name == safe_node.name == "item"
        assert unsafe_node.text() == safe_node.text() == "Hello"
        assert unsafe_node == safe_node
