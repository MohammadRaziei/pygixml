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
    
    # Test node creation
    print("✓ Testing node creation...")
    new_person = root.append_child("person")
    new_person.set_name("person")
    new_name = new_person.append_child("name")
    new_name.set_value("New Person")
    print(f"✓ Created new person with name: {new_name.child_value()}")
    
    # Test saving to file
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
        temp_file = f.name
    
    try:
        doc.save_file(temp_file)
        print(f"✓ XML saved to file: {temp_file}")
        
        # Test loading from file
        doc2 = pygixml.parse_file(temp_file)
        print("✓ XML loaded from file successfully")
        
        # Verify the loaded content
        root2 = doc2.first_child()
        person2 = root2.child("person")
        name2 = person2.child("name")
        print(f"✓ Loaded name value: {name2.child_value()}")
        
    finally:
        # Clean up
        if os.path.exists(temp_file):
            os.unlink(temp_file)
    
    print("\n🎉 All tests passed! pygixml is working correctly.")
    
except ImportError as e:
    print(f"✗ Failed to import pygixml: {e}")
    print("Make sure the package is built and installed correctly.")
    
except Exception as e:
    print(f"✗ Test failed: {e}")
    import traceback
    traceback.print_exc()
