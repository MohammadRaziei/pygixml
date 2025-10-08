# pygixml

Python wrapper for pugixml using Cython - A fast and efficient XML parser and manipulator for Python.

## Features

- Fast XML parsing and manipulation using pugixml
- Pythonic API for XML document handling
- Support for loading from strings and files
- Support for saving to strings and files
- Node and attribute manipulation
- Built with Cython for optimal performance

## Installation

```bash
pip install .
```

## Usage

```python
import pygixml

# Parse XML from string
xml_string = """
<root>
    <person id="1">
        <name>John Doe</name>
        <age>30</age>
    </person>
</root>
"""

doc = pygixml.parse_string(xml_string)

# Access nodes
root = doc.first_child()
person = root.child("person")
name = person.child("name")

print(f"Person name: {name.child_value()}")  # Output: Person name: John Doe

# Modify XML
name.set_value("Jane Doe")
person.append_child("city").set_value("New York")

# Save to string
print(doc.save_string())
```

## Development

### Building from source

```bash
# Install build dependencies
pip install -e .[dev]

# Build the package
pip install .
```

### Requirements

- Python 3.8+
- Cython
- CMake 3.15+
- C++ compiler with C++11 support

## License

MIT License
