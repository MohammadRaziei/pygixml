#!/usr/bin/env python3
"""
Example demonstrating the xml property functionality
"""

import pygixml


def example_xml_property_basic():
    """Basic usage of the xml property"""
    print("=== Basic XML Property Usage ===")
    
    # Parse XML from string
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
    
    print("Root element XML:")
    print(f"  {root.xml}")
    print()
    
    # Access child elements
    first_book = root.child("book")
    print("First book element XML:")
    print(f"  {first_book.xml}")
    print()
    
    # Access nested elements
    title = first_book.child("title")
    print("Title element XML:")
    print(f"  {title.xml}")
    print()
    
    # Access text content
    title_text = title.first_child()
    print("Title text content:")
    print(f"  {title_text.xml}")
    print()


def example_xml_property_iteration():
    """Using xml property while iterating through nodes"""
    print("=== XML Property with Iteration ===")
    
    xml_string = """
    <catalog>
        <product>
            <name>Laptop</name>
            <price>999.99</price>
        </product>
        <product>
            <name>Mouse</name>
            <price>29.99</price>
        </product>
        <product>
            <name>Keyboard</name>
            <price>79.99</price>
        </product>
    </catalog>
    """
    
    doc = pygixml.parse_string(xml_string)
    catalog = doc.first_child()
    
    print("Iterating through products:")
    product = catalog.first_child()
    while product:
        print(f"  Product XML: {product.xml}")
        
        # Access child elements
        name = product.child("name")
        price = product.child("price")
        
        print(f"    Name XML: {name.xml}")
        print(f"    Price XML: {price.xml}")
        print()
        
        product = product.next_sibling()


def example_xml_property_readonly():
    """Demonstrating that xml property is readonly"""
    print("=== XML Property is Readonly ===")
    
    xml_string = "<config><setting>value</setting></config>"
    doc = pygixml.parse_string(xml_string)
    setting = doc.first_child().first_child()
    
    print(f"Original XML: {setting.xml}")
    
    # The xml property is readonly - you cannot set it
    # This would raise an AttributeError:
    # setting.xml = "<new>content</new>"
    
    print("✓ XML property is readonly (cannot be modified)")
    print()


def example_xml_property_comparison():
    """Comparing xml property with other node properties"""
    print("=== XML Property vs Other Properties ===")
    
    xml_string = '<person name="John" age="30"><occupation>Developer</occupation></person>'
    doc = pygixml.parse_string(xml_string)
    person = doc.first_child()
    occupation = person.child("occupation")
    occupation_text = occupation.first_child()
    
    print("Person element:")
    print(f"  name(): {person.name()}")
    print(f"  xml: {person.xml}")
    print()
    
    print("Occupation element:")
    print(f"  name(): {occupation.name()}")
    print(f"  child_value(): {occupation.child_value()}")
    print(f"  xml: {occupation.xml}")
    print()
    
    print("Occupation text node:")
    print(f"  value(): {occupation_text.value()}")
    print(f"  xml: {occupation_text.xml}")
    print()


if __name__ == "__main__":
    example_xml_property_basic()
    example_xml_property_iteration()
    example_xml_property_readonly()
    example_xml_property_comparison()
    print("🎉 All XML property examples completed successfully!")
