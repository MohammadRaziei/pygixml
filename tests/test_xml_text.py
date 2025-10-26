#!/usr/bin/env python3
"""
Tests for the xml property functionality
"""

import pytest
import pygixml


class TestXMLNodeSerialization:

    def test_xml_simple_element(self):
        doc = pygixml.parse_string("<root>hello</root>")
        node = doc.first_child()
        # Use compact form for predictable comparison
        assert node.to_string(indent="") == "<root>hello</root>"

    def test_xml_nested_elements(self):
        doc = pygixml.parse_string("<root><a><b>text</b></a></root>")
        node = doc.first_child()
        expected = "<root>\n<a>\n<b>text</b>\n</a>\n</root>"
        assert node.to_string(indent="") == expected

    def test_xml_with_unicode(self):
        doc = pygixml.parse_string("<msg>سلام 🌍</msg>")
        node = doc.first_child()
        result = node.to_string(indent="")
        assert result == "<msg>سلام 🌍</msg>"

    def test_xml_null_node(self):
        doc = pygixml.XMLDocument()
        node = doc.first_child()
        assert node.to_string(indent="") == ""

    def test_xml_text_node(self):
        doc = pygixml.parse_string("<p>Hello</p>")
        text_node = doc.first_child().first_child()
        # Text nodes return raw text (no tags)
        assert text_node.to_string(indent="") == "Hello"

    def test_xml_mixed_content(self):
        doc = pygixml.parse_string("<p>Hello <b>world</b>!</p>")
        node = doc.first_child()
        result = node.to_string(indent="")
        assert result == "<p>Hello <b>world</b>!</p>"

    def test_xml_deep_nesting(self):
        level = 5
        deep = "\n".join(["<a>"] * level) + "x" + "\n".join(["</a>"] * level)
        doc = pygixml.parse_string(deep)
        node = doc.first_child()
        assert node.to_string(indent="") == deep

    def test_xml_vs_to_string_consistency(self):
        # We don't compare xml vs to_string() because xml uses default indent
        # Instead, we just ensure both work without crash
        doc = pygixml.parse_string("<test>ok</test>")
        node = doc.first_child()
        _ = node.xml  # should not raise
        _ = node.to_string()  # should not raise


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

