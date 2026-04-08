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
    root = doc.root

    print(f"Root element: {root.name}")

    # Iterate through books using XPath
    books = root.select_nodes("book")
    for book in books:
        node = book.node
        print(f"\nBook ID: {node.attribute('id').value}")
        title = node.child("title")
        author = node.child("author")
        year = node.child("year")

        print(f"  Title: {title.text()}")
        print(f"  Author: {author.text()}")
        print(f"  Year: {year.text()}")

    print("\n" + "=" * 50)


def example_create_xml():
    """Example: Create XML document from scratch"""
    print("=== Example: Create XML from scratch ===")

    doc = pygixml.XMLDocument()

    # Create root element
    root = doc.append_child("catalog")

    # Add products
    product1 = root.append_child("product")
    name1 = product1.append_child("name")
    name1.set_value("Laptop")
    price1 = product1.append_child("price")
    price1.set_value("999.99")

    product2 = root.append_child("product")
    name2 = product2.append_child("name")
    name2.set_value("Mouse")
    price2 = product2.append_child("price")
    price2.set_value("29.99")

    # Save to file
    doc.save_file("catalog.xml")
    print("✓ XML saved to 'catalog.xml'")

    # Verify by loading back
    doc2 = pygixml.parse_file("catalog.xml")
    root2 = doc2.root
    print(f"Loaded root: {root2.name}")

    import os

    if os.path.exists("catalog.xml"):
        os.unlink("catalog.xml")

    print("\n" + "=" * 50)


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
    root = doc.root
    employee = root.child("employee")

    # Modify values
    employee.child("name").set_value("Jane Smith")
    employee.child("salary").set_value("55000")

    # Add new element
    employee.append_child("department").set_value("Engineering")

    # Rename an element
    employee.child("position").name = "role"

    print("Modified XML structure:")
    print(f"  Name: {employee.child('name').text()}")
    print(f"  Role: {employee.child('role').text()}")
    print(f"  Salary: {employee.child('salary').text()}")
    print(f"  Department: {employee.child('department').text()}")

    print("\n" + "=" * 50)


if __name__ == "__main__":
    example_parse_string()
    example_create_xml()
    example_modify_xml()
    print("🎉 All examples completed successfully!")
