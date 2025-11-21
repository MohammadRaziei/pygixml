#!/usr/bin/env python3
"""
Example demonstrating the XMLNode type property usage

This example shows how to use the type property to identify different types
of XML nodes in a document.
"""

import pygixml


def main():
    print("XML Node Type Property Example")
    print("=" * 40)
    
    # Parse an XML document with various node types
    xml_content = '''
    <?xml version="1.0" encoding="UTF-8"?>
    <root>
        <item id="1">Text content</item>
        <item id="2">
            <nested>Nested content</nested>
        </item>
        <!-- This is a comment -->
        <empty_item/>
        <text_only>Only text here</text_only>
    </root>
    '''
    
    doc = pygixml.parse_string(xml_content)
    
    print("Document structure with node types:")
    print("-" * 40)
    
    # Iterate through all nodes and display their types
    for node in doc:
        display_node_info(node, 0)
    
    print("\nNode type summary:")
    print("-" * 40)
    
    # Count different node types
    type_counts = {}
    for node in doc:
        node_type = node.type
        type_counts[node_type] = type_counts.get(node_type, 0) + 1
    
    for node_type, count in type_counts.items():
        print(f"{node_type}: {count} nodes")
    
    print("\nPractical usage examples:")
    print("-" * 40)
    
    # Example 1: Find all element nodes
    print("All element nodes:")
    for node in doc:
        if node.type == "element":
            print(f"  - {node.name}")
    
    # Example 2: Find text nodes
    print("\nAll text content:")
    for node in doc:
        if node.type in ["pcdata", "cdata"] and node.value:
            print(f"  - '{node.value}'")
    
    # Example 3: Check if a node is an element before accessing attributes
    root = doc.root
    if root.type == "element":
        print(f"\nRoot element attributes:")
        attr = root.first_attribute()
        while attr:
            print(f"  - {attr.name} = {attr.value}")
            attr = attr.next_attribute()


def display_node_info(node, indent_level):
    """Recursively display node information with proper indentation"""
    indent = "  " * indent_level
    
    if node.type == "element":
        print(f"{indent}Element: {node.name}")
        # Show attributes for element nodes
        attr = node.first_attribute()
        while attr:
            print(f"{indent}  Attribute: {attr.name} = {attr.value}")
            attr = attr.next_attribute
        
        # Recursively process children
        child = node.first_child()
        while child:
            display_node_info(child, indent_level + 1)
            child = child.next_sibling
    
    elif node.type in ["pcdata", "cdata"]:
        if node.value and node.value.strip():
            print(f"{indent}Text: '{node.value.strip()}'")
    
    elif node.type == "comment":
        print(f"{indent}Comment: '{node.value}'")
    
    else:
        print(f"{indent}{node.type.capitalize()}: {node.name or '(no name)'}")


if __name__ == "__main__":
    main()
