#!/usr/bin/env python3
"""
Basic tests for pygixml
"""

import pytest
import tempfile
import os
import pygixml


class TestXMLDocument:
    """Test XMLDocument class functionality"""
    
    def test_create_document(self):
        """Test creating a new XML document"""
        doc = pygixml.XMLDocument()
        assert doc is not None
        
    def test_parse_string(self):
        """Test parsing XML from string"""
        xml_string = "<root><test>value</test></root>"
        doc = pygixml.parse_string(xml_string)
        assert doc is not None
        
        root = doc.first_child()
        assert root.name() == "root"
        
    def test_parse_invalid_string(self):
        """Test parsing invalid XML string"""
        with pytest.raises(ValueError):
            pygixml.parse_string("invalid xml")
            
    def test_save_and_load_file(self):
        """Test saving and loading XML file"""
        # Create test XML
        xml_string = "<root><data>test</data></root>"
        doc = pygixml.parse_string(xml_string)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            temp_file = f.name
        
        try:
            # Save file
            doc.save_file(temp_file)
            assert os.path.exists(temp_file)
            
            # Load file
            doc2 = pygixml.parse_file(temp_file)
            assert doc2 is not None
            
            # Verify content
            root = doc2.first_child()
            assert root.name() == "root"
            data = root.child("data")
            assert data.child_value() == "test"
            
        finally:
            # Clean up
            if os.path.exists(temp_file):
                os.unlink(temp_file)


class TestXMLNode:
    """Test XMLNode class functionality"""
    
    def setup_method(self):
        """Setup test XML document"""
        self.xml_string = """
        <library>
            <book>
                <title>Test Book</title>
                <author>Test Author</author>
            </book>
        </library>
        """
        self.doc = pygixml.parse_string(self.xml_string)
        self.root = self.doc.first_child()
        
    def test_node_name(self):
        """Test getting node name"""
        assert self.root.name() == "library"
        
    def test_child_access(self):
        """Test accessing child nodes"""
        book = self.root.child("book")
        assert book is not None
        assert book.name() == "book"
        
    def test_child_value(self):
        """Test getting child values"""
        book = self.root.child("book")
        title = book.child("title")
        assert title.child_value() == "Test Book"
        
    def test_set_value(self):
        """Test setting node value"""
        book = self.root.child("book")
        title = book.child("title")
        title.set_value("Modified Title")
        assert title.child_value() == "Modified Title"
        
    def test_append_child(self):
        """Test appending child nodes"""
        book = self.root.child("book")
        new_child = book.append_child("year")
        new_child.set_value("2024")
        
        year = book.child("year")
        assert year.child_value() == "2024"
        
    def test_first_child(self):
        """Test getting first child"""
        book = self.root.first_child()
        assert book.name() == "book"
        
    def test_nonexistent_child(self):
        """Test accessing non-existent child"""
        nonexistent = self.root.child("nonexistent")
        # Note: The current implementation returns an empty node instead of None
        # This is expected behavior for now
        assert nonexistent is not None
        assert nonexistent.name() == "nonexistent"


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def test_parse_string_function(self):
        """Test parse_string convenience function"""
        xml_string = "<root><item>test</item></root>"
        doc = pygixml.parse_string(xml_string)
        assert doc is not None
        root = doc.first_child()
        assert root.name() == "root"
        
    def test_parse_file_function(self):
        """Test parse_file convenience function"""
        # Create test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write('<root><data>file_test</data></root>')
            temp_file = f.name
        
        try:
            doc = pygixml.parse_file(temp_file)
            assert doc is not None
            root = doc.first_child()
            assert root.name() == "root"
            data = root.child("data")
            assert data.child_value() == "file_test"
            
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
                
    def test_parse_file_nonexistent(self):
        """Test parse_file with non-existent file"""
        with pytest.raises(ValueError):
            pygixml.parse_file("nonexistent_file.xml")
