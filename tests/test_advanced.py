#!/usr/bin/env python3
"""
Advanced tests for pygixml - edge cases and complex scenarios
"""

import pytest
import pygixml


class TestAdvancedXML:
    """Test advanced XML scenarios"""
    
    def test_large_xml_structure(self):
        """Test handling of large XML structures"""
        # Create a moderately large XML structure
        doc = pygixml.XMLDocument()
        root = doc.append_child("catalog")
        
        # Add multiple items
        for i in range(100):
            product = root.append_child("product")
            product.set_name("product")
            
            id_elem = product.append_child("id")
            id_elem.set_value(str(i))
            
            name_elem = product.append_child("name")
            name_elem.set_value(f"Product {i}")
            
            price_elem = product.append_child("price")
            price_elem.set_value(str(i * 10.5))
        
        # Verify structure
        assert root.name() == "catalog"
        
        # Count products
        count = 0
        product = root.first_child()
        while product:
            count += 1
            product = product.next_sibling()
        
        assert count == 100
        
    def test_unicode_content(self):
        """Test handling of Unicode characters"""
        xml_string = """
        <root>
            <text>Hello 世界 🌍</text>
            <arabic>مرحبا</arabic>
            <russian>Привет</russian>
        </root>
        """
        
        doc = pygixml.parse_string(xml_string)
        root = doc.first_child()
        
        text = root.child("text")
        arabic = root.child("arabic")
        russian = root.child("russian")
        
        assert text.child_value() == "Hello 世界 🌍"
        assert arabic.child_value() == "مرحبا"
        assert russian.child_value() == "Привет"
        
    def test_empty_nodes(self):
        """Test handling of empty nodes"""
        xml_string = """
        <root>
            <empty1></empty1>
            <empty2/>
            <with_children>
                <child1/>
                <child2></child2>
            </with_children>
        </root>
        """
        
        doc = pygixml.parse_string(xml_string)
        root = doc.first_child()
        
        empty1 = root.child("empty1")
        empty2 = root.child("empty2")
        with_children = root.child("with_children")
        
        assert empty1.child_value() == ""
        assert empty2.child_value() == ""
        assert with_children is not None
        
    def test_nested_structure(self):
        """Test deeply nested XML structure"""
        xml_string = """
        <level1>
            <level2>
                <level3>
                    <level4>
                        <level5>Deep Value</level5>
                    </level4>
                </level3>
            </level2>
        </level1>
        """
        
        doc = pygixml.parse_string(xml_string)
        level1 = doc.first_child()
        level2 = level1.first_child()
        level3 = level2.first_child()
        level4 = level3.first_child()
        level5 = level4.first_child()
        
        assert level5.child_value() == "Deep Value"
        
    def test_modify_complex_structure(self):
        """Test modifying complex XML structure"""
        xml_string = """
        <company>
            <department name="Engineering">
                <employee id="1">
                    <name>Alice</name>
                    <role>Developer</role>
                </employee>
                <employee id="2">
                    <name>Bob</name>
                    <role>Manager</role>
                </employee>
            </department>
            <department name="Sales">
                <employee id="3">
                    <name>Charlie</name>
                    <role>Sales Rep</role>
                </employee>
            </department>
        </company>
        """
        
        doc = pygixml.parse_string(xml_string)
        company = doc.first_child()
        
        # Modify employee roles
        engineering = company.child("department")
        first_employee = engineering.first_child()
        first_role = first_employee.child("role")
        first_role.set_value("Senior Developer")
        
        # Add new employee
        new_employee = engineering.append_child("employee")
        new_employee.set_name("employee")
        new_name = new_employee.append_child("name")
        new_name.set_value("Diana")
        new_role = new_employee.append_child("role")
        new_role.set_value("QA Engineer")
        
        # Verify modifications
        first_employee = engineering.first_child()
        assert first_employee.child("role").child_value() == "Senior Developer"
        
        # Count employees in engineering
        count = 0
        employee = engineering.first_child()
        while employee:
            count += 1
            employee = employee.next_sibling()
        
        assert count == 3  # Original 2 + new 1


class TestErrorHandling:
    """Test error handling scenarios"""
    
    def test_malformed_xml(self):
        """Test handling of malformed XML"""
        malformed_xmls = [
            "<root><unclosed>",
            "<root>",
            "just text",
            "<root><tag></different_tag></root>",
        ]
        
        for xml in malformed_xmls:
            with pytest.raises(ValueError):
                pygixml.parse_string(xml)
                
    def test_empty_document_operations(self):
        """Test operations on empty document"""
        doc = pygixml.XMLDocument()
        
        # Should not crash on empty document operations
        root = doc.first_child()
        assert root is None
        
    def test_nonexistent_file_save(self):
        """Test saving to invalid file path"""
        doc = pygixml.XMLDocument()
        root = doc.append_child("test")
        
        # Try to save to invalid path
        with pytest.raises(ValueError):
            doc.save_file("/invalid/path/test.xml")


class TestPerformance:
    """Performance-related tests"""
    
    def test_rapid_node_creation(self):
        """Test rapid creation of many nodes"""
        doc = pygixml.XMLDocument()
        root = doc.append_child("root")
        
        # Create many nodes quickly
        for i in range(1000):
            node = root.append_child(f"node_{i}")
            node.set_value(f"value_{i}")
        
        # Verify all nodes were created
        count = 0
        node = root.first_child()
        while node:
            count += 1
            node = node.next_sibling()
        
        assert count == 1000
