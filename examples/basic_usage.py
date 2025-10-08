#!/usr/bin/env python3
"""
Basic usage examples for pygixml
"""

import pygixml

def example_parse_string():
    """Example: Parse XML from string"""
    print("=== Example: Parse XML from string ===")
    
    xml_string = """
    <library>
        <book id="1">
            <title>The Great Gatsby</title>
            <author>F. Scott Fitzgerald</author>
            <year>1925</year>
        </book>
        <book id="2">
            <title>1984</title>
            <author>George Orwell</author>
            <year>1949</year>
        </book>
    </library>
    """
    
    doc = pygixml.parse_string(xml_string)
    root = doc.first_child()
    
    print(f"Root element: {root.name()}")
    
    # Iterate through books
    book = root.first_child()
    while book:
        print(f"\nBook ID: {book.name()}")
        title = book.child("title")
        author = book.child("author")
        year = book.child("year")
        
        print(f"  Title: {title.child_value()}")
        print(f"  Author: {author.child_value()}")
        print(f"  Year: {year.child_value()}")
        
        book = book.next_sibling()
    
    print("\n" + "="*50)

def example_create_xml():
    """Example: Create XML document from scratch"""
    print("=== Example: Create XML from scratch ===")
    
    doc = pygixml.XMLDocument()
    
    # Create root element
    root = doc.append_child("catalog")
    
    # Add products
    product1 = root.append_child("product")
    product1.set_name("product")
    name1 = product1.append_child("name")
    name1.set_value("Laptop")
    price1 = product1.append_child("price")
    price1.set_value("999.99")
    
    product2 = root.append_child("product")
    product2.set_name("product")
    name2 = product2.append_child("name")
    name2.set_value("Mouse")
    price2 = product2.append_child("price")
    price2.set_value("29.99")
    
    # Save to file
    doc.save_file("catalog.xml")
    print("✓ XML saved to 'catalog.xml'")
    
    # Verify by loading back
    doc2 = pygixml.parse_file("catalog.xml")
    root2 = doc2.first_child()
    print(f"Loaded root: {root2.name()}")
    
    import os
    if os.path.exists("catalog.xml"):
        os.unlink("catalog.xml")
    
    print("\n" + "="*50)

def example_modify_xml():
    """Example: Modify existing XML"""
    print("=== Example: Modify XML ===")
    
    xml_string = """
    <employees>
        <employee>
            <name>John Doe</name>
            <position>Developer</position>
            <salary>50000</salary>
        </employee>
    </employees>
    """
    
    doc = pygixml.parse_string(xml_string)
    root = doc.first_child()
    employee = root.first_child()
    
    # Modify values
    name = employee.child("name")
    name.set_value("Jane Smith")
    
    salary = employee.child("salary")
    salary.set_value("55000")
    
    # Add new element
    department = employee.append_child("department")
    department.set_value("Engineering")
    
    print("Modified XML structure:")
    print(f"  Name: {employee.child('name').child_value()}")
    print(f"  Position: {employee.child('position').child_value()}")
    print(f"  Salary: {employee.child('salary').child_value()}")
    print(f"  Department: {employee.child('department').child_value()}")
    
    print("\n" + "="*50)

if __name__ == "__main__":
    example_parse_string()
    example_create_xml()
    example_modify_xml()
    print("🎉 All examples completed successfully!")
