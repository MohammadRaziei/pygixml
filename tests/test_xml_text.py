#!/usr/bin/env python3
"""
Tests for the xml property functionality
"""

import pytest
import pygixml



import pytest
import pygixml


class TestXMLNodeText:
    """Tests for the XMLNode.text() method in pygixml"""

    def test_simple_text_direct(self):
        xml = "<root>Hello World</root>"
        doc = pygixml.parse_string(xml)
        root = doc.first_child()

        # Only one text node
        assert root.text(recursive=False) == "Hello World"
        assert root.text(recursive=True) == "Hello World"

    def test_nested_text_recursive_vs_direct(self):
        xml = """
        <root>
            Text1
            <child>Inner</child>
            Text2
        </root>
        """
        doc = pygixml.parse_string(xml)
        root = doc.first_child()

        # Non-recursive: only text directly under <root>
        direct = root.text(recursive=False)
        assert "Text1" in direct
        assert "Inner" not in direct
        assert "Text2" in direct

        # Recursive: includes <child> text
        recursive_text = root.text(recursive=True)
        assert "Inner" in recursive_text
        assert "Text1" in recursive_text
        assert "Text2" in recursive_text

    def test_cdata_nodes(self):
        xml = "<root><![CDATA[<raw>text</raw>]]></root>"
        doc = pygixml.parse_string(xml)
        root = doc.first_child()

        # CDATA should be included as plain text
        assert root.text(recursive=True) == "<raw>text</raw>"

    def test_mixed_text_with_join(self):
        xml = """
        <root>
            hello
            <a>world</a>
            <b>again</b>
        </root>
        """
        doc = pygixml.parse_string(xml)
        root = doc.first_child()

        # Custom join string
        joined = root.text(recursive=True, join="|")
        parts = joined.split("|")

        assert "hello" in joined
        assert "world" in joined
        assert "again" in joined
        assert "|" in joined
        assert len(parts) == 3

    def test_empty_node_text(self):
        xml = "<root></root>"
        doc = pygixml.parse_string(xml)
        root = doc.first_child()

        assert root.text(recursive=False) == ""
        assert root.text(recursive=True) == ""

    def test_nested_multiple_levels(self):
        xml = """
        <root>
            <a>One</a>
            <b>
                <c>Two</c>
                <d><e>Three</e></d>
            </b>
        </root>
        """
        doc = pygixml.parse_string(xml)
        root = doc.first_child()

        t = root.text(recursive=True)
        assert "One" in t
        assert "Two" in t
        assert "Three" in t

    def test_comment_node_ignored(self):
        xml = "<root><!-- comment --><child>Text</child></root>"
        doc = pygixml.parse_string(xml)
        root = doc.first_child()

        txt = root.text(recursive=True)
        assert "Text" in txt
        assert "comment" not in txt

    def test_processing_instruction_node_ignored(self):
        xml = """<?xml version="1.0"?><root>content</root>"""
        doc = pygixml.parse_string(xml)
        root = doc.first_child()

        assert root.text(recursive=True) == "content"



class TestXMLProperty:
    """Test XML property functionality"""
    
    def test_xml_property_element_node(self):
        """Test xml property for element nodes"""
        xml_string = "<root><child>text</child></root>"
        doc = pygixml.parse_string(xml_string)
        root = doc.first_child()
        
        # Element nodes should return XML representation
        assert root.xml == "<root/>"
        
    def test_xml_property_text_node(self):
        """Test xml property for text nodes"""
        xml_string = "<root>text content</root>"
        doc = pygixml.parse_string(xml_string)
        root = doc.first_child()
        text_node = root.first_child()
        
        # Text nodes should return their text content
        assert text_node.xml == "text content"
        
    def test_xml_property_with_attributes(self):
        """Test xml property for elements with attributes"""
        xml_string = '<book id="1" category="fiction"/>'
        doc = pygixml.parse_string(xml_string)
        book = doc.first_child()
        
        # Currently returns simple representation without attributes
        # This is expected behavior for the current implementation
        assert book.xml == "<book/>"
        
    def test_xml_property_empty_element(self):
        """Test xml property for empty elements"""
        xml_string = "<empty/>"
        doc = pygixml.parse_string(xml_string)
        empty = doc.first_child()
        
        assert empty.xml == "<empty/>"
        
    def test_xml_property_nested_elements(self):
        """Test xml property for nested elements"""
        xml_string = "<root><parent><child>value</child></parent></root>"
        doc = pygixml.parse_string(xml_string)
        root = doc.first_child()
        parent = root.first_child()
        child = parent.first_child()
        
        # Each element should return its own XML representation
        assert root.xml == "<root/>"
        assert parent.xml == "<parent/>"
        assert child.xml == "<child/>"
        
    def test_xml_property_readonly(self):
        """Test that xml property is readonly"""
        xml_string = "<test>content</test>"
        doc = pygixml.parse_string(xml_string)
        node = doc.first_child()
        
        # Verify it's a property and can't be set
        assert hasattr(node, 'xml')
        
        # Attempting to set should raise AttributeError
        with pytest.raises(AttributeError):
            node.xml = "<new>content</new>"
            
    def test_xml_property_complex_structure(self):
        """Test xml property with complex XML structure"""
        xml_string = """
        <library>
            <book id="1">
                <title>Book One</title>
                <author>Author One</author>
            </book>
            <book id="2">
                <title>Book Two</title>
                <author>Author Two</author>
            </book>
        </library>
        """
        
        doc = pygixml.parse_string(xml_string)
        library = doc.first_child()
        first_book = library.child("book")
        title = first_book.child("title")
        title_text = title.first_child()
        
        # Test various node types
        assert library.xml == "<library/>"
        assert first_book.xml == "<book/>"
        assert title.xml == "<title/>"
        assert title_text.xml == "Book One"
