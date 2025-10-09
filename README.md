# pygixml

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Build Status](https://github.com/yourusername/pygixml/actions/workflows/python.yml/badge.svg)](https://github.com/yourusername/pygixml/actions)
[![PyPI version](https://badge.fury.io/py/pygixml.svg)](https://pypi.org/project/pygixml/)

A high-performance Python wrapper for [pugixml](https://pugixml.org/) using Cython, providing fast XML parsing and manipulation capabilities.

## Features

- 🚀 **High Performance**: Direct C++ bindings through Cython for maximum speed
- 📝 **Full pugixml API**: Complete access to pugixml's powerful XML processing capabilities
- 🐍 **Pythonic Interface**: Clean, intuitive Python API
- 🔧 **Modern Build System**: Built with CMake and scikit-build
- 📦 **Cross-Platform**: Works on Windows, Linux, and macOS
- 🧪 **Comprehensive Testing**: Extensive test suite with CI/CD pipeline

## Installation

### From PyPI (Coming Soon)
```bash
pip install pygixml
```

### From Source
```bash
git clone https://github.com/yourusername/pygixml.git
cd pygixml
git submodule update --init --recursive
pip install -e .
```

### Development Installation
```bash
git clone https://github.com/yourusername/pygixml.git
cd pygixml
git submodule update --init --recursive
pip install -e .[test]
```

## Quick Start

### Basic Usage

```python
import pygixml

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

# Iterate through books
book = root.first_child()
while book:
    title = book.child("title")
    author = book.child("author")
    year = book.child("year")
    
    print(f"Title: {title.child_value()}")
    print(f"Author: {author.child_value()}")
    print(f"Year: {year.child_value()}")
    print("---")
    
    book = book.next_sibling()
```

### Creating XML Documents

```python
import pygixml

# Create a new XML document
doc = pygixml.XMLDocument()
root = doc.append_child("catalog")

# Add products
product1 = root.append_child("product")
product1.append_child("name").set_value("Laptop")
product1.append_child("price").set_value("999.99")

product2 = root.append_child("product")
product2.append_child("name").set_value("Mouse")
product2.append_child("price").set_value("29.99")

# Save to file
doc.save_file("catalog.xml")
```

### Working with Attributes

```python
import pygixml

xml_string = '<person name="John" age="30" city="New York"/>'
doc = pygixml.parse_string(xml_string)
person = doc.first_child()

# Access attributes
name_attr = person.attribute("name")
age_attr = person.attribute("age")

print(f"Name: {name_attr.value()}")
print(f"Age: {age_attr.value()}")

# Modify attributes
name_attr.set_value("Jane")
age_attr.set_value("25")
```

## API Reference

### XMLDocument Class

- `XMLDocument()` - Create a new XML document
- `load_string(xml_string)` - Parse XML from string
- `load_file(file_path)` - Parse XML from file
- `save_file(file_path, indent="  ")` - Save XML to file
- `append_child(name)` - Append a child node
- `first_child()` - Get first child node
- `child(name)` - Get child node by name
- `reset()` - Reset the document

### XMLNode Class

- `name()` - Get node name
- `value()` - Get node value
- `set_name(name)` - Set node name
- `set_value(value)` - Set node value
- `first_child()` - Get first child node
- `child(name)` - Get child node by name
- `next_sibling()` - Get next sibling node
- `previous_sibling()` - Get previous sibling node
- `parent()` - Get parent node
- `append_child(name)` - Append a child node
- `child_value(name=None)` - Get child value

### XMLAttribute Class

- `name()` - Get attribute name
- `value()` - Get attribute value
- `set_name(name)` - Set attribute name
- `set_value(value)` - Set attribute value

### Convenience Functions

- `parse_string(xml_string)` - Parse XML string and return XMLDocument
- `parse_file(file_path)` - Parse XML file and return XMLDocument

## Performance

pygixml provides near-native performance by using direct C++ bindings through Cython. The wrapper adds minimal overhead while providing a clean Python interface.

### Benchmark Example

```python
import pygixml
import time

# Create a large XML structure
doc = pygixml.XMLDocument()
root = doc.append_child("data")

start = time.time()
for i in range(1000):
    item = root.append_child(f"item_{i}")
    item.append_child("value").set_value(str(i))

end = time.time()
print(f"Created 1000 nodes in {end - start:.4f} seconds")
```

## Development

### Building from Source

1. Clone the repository:
```bash
git clone https://github.com/yourusername/pygixml.git
cd pygixml
```

2. Initialize submodules:
```bash
git submodule update --init --recursive
```

3. Install in development mode:
```bash
pip install -e .[test]
```

### Running Tests

```bash
# Run all tests
pytest

# Run only fast tests (exclude slow performance tests)
pytest -m "not slow"

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_basic.py
```

### Code Structure

```
pygixml/
├── src/
│   ├── pygixml/
│   │   ├── pygixml.pyx      # Cython wrapper implementation
│   │   └── __init__.py      # Python package initialization
│   └── third_party/
│       └── pugixml/         # pugixml C++ library (submodule)
├── tests/
│   ├── test_basic.py        # Basic functionality tests
│   └── test_advanced.py     # Advanced scenarios and edge cases
├── examples/
│   └── basic_usage.py       # Usage examples
├── CMakeLists.txt           # CMake build configuration
├── pyproject.toml          # Python packaging configuration
└── README.md               # This file
```

## CI/CD Pipeline

The project includes a comprehensive GitHub Actions workflow that:

- ✅ Builds source distributions (sdist)
- ✅ Builds wheels for multiple platforms
- ✅ Runs tests on multiple OSes and Python versions
- ✅ Automatically publishes to PyPI on tag releases
- ✅ Handles submodules correctly

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [pugixml](https://pugixml.org/) - The fast and lightweight C++ XML processing library
- [Cython](https://cython.org/) - For making C++ integration with Python seamless
- [scikit-build](https://scikit-build.readthedocs.io/) - For the modern Python build system

## Support

If you encounter any issues or have questions:

1. Check the [examples](examples/) directory
2. Look at the [test cases](tests/) for usage patterns
3. Open an [issue](https://github.com/yourusername/pygixml/issues) on GitHub

## Changelog

### v0.1.0 (Current)
- Initial release
- Complete pugixml wrapper implementation
- Basic XML parsing and manipulation
- Comprehensive test suite
- CI/CD pipeline
