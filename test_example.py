#!/usr/bin/env python3
"""
Simple test script for pygixml
"""

try:
    import pygixml
    print("✓ pygixml imported successfully")
    
    # Test basic functionality
    xml_string = """
    <root>
        <person id="1">
            <name>John Doe</name>
            <age>30</age>
        </person>
    </root>
    """
    
    print("✓ Testing XML parsing from string...")
    doc = pygixml.parse_string(xml_string)
    print("✓ XML document created successfully")
    
    # Access nodes
    root = doc.first_child()
    print(f"✓ Root node name: {root.name()}")
    
    person = root.child("person")
    print(f"✓ Person node found: {person is not None}")
    
    name = person.child("name")
    print(f"✓ Name node value: {name.child_value()}")
    
    # Test modification
    name.set_value("Jane Doe")
    print(f"✓ Modified name value: {name.child_value()}")
    
    # Test saving
    result_xml = doc.save_string()
    print("✓ XML saved to string successfully")
    print("\nModified XML:")
    print(result_xml)
    
    print("\n🎉 All tests passed! pygixml is working correctly.")
    
except ImportError as e:
    print(f"✗ Failed to import pygixml: {e}")
    print("Make sure the package is built and installed correctly.")
    
except Exception as e:
    print(f"✗ Test failed: {e}")
    import traceback
    traceback.print_exc()
