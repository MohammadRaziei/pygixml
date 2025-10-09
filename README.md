# pygixml

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Build Status](https://github.com/MohammadRaziei/pygixml/actions/workflows/python.yml/badge.svg)](https://github.com/MohammadRaziei/pygixml/actions)
[![Documentation Status](https://github.com/MohammadRaziei/pygixml/actions/workflows/docs.yaml/badge.svg)](https://mohammadraziei.github.io/pygixml/)
[![GitHub Stars](https://img.shields.io/github/stars/MohammadRaziei/pygixml?style=social)](https://github.com/MohammadRaziei/pygixml)

A high-performance Python wrapper for [pugixml](https://pugixml.org/) using Cython, providing fast XML parsing and manipulation capabilities.

📚 **[View Full Documentation](https://mohammadraziei.github.io/pygixml/)**



## 🚀 Performance

pygixml delivers exceptional performance compared to other XML libraries:

### Performance Comparison (5000 XML elements)

| Library | Parsing Time | Speedup vs ElementTree |
|---------|--------------|------------------------|
| **pygixml** | 0.00077s | **15.9x faster** |
| **lxml** | 0.00407s | 3.0x faster |
| **ElementTree** | 0.01220s | 1.0x (baseline) |

![Performance Comparison](https://github.com/MohammadRaziei/pygixml/raw/master/benchmarks/results/performance_comparison.svg)

### Key Performance Highlights

- **15.9x faster** than Python's ElementTree for XML parsing
- **5.3x faster** than lxml for XML parsing  
- **Memory efficient** - uses pugixml's optimized C++ memory management
- **Scalable performance** - maintains speed advantage across different XML sizes

## Installation

### From Pypi repositoey
```bash
pip install pygixml
```

### From Source
```bash
git clone --recurse-submodules https://github.com/MohammadRaziei/pygixml.git
pip install ./pygixml
```

### Development Installation
```bash
pip install ./pygixml[test]
```

## Quick Start

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
</library>
"""

doc = pygixml.parse_string(xml_string)
root = doc.first_child()

# Access elements
book = root.first_child()
title = book.child("title")
print(f"Title: {title.child_value()}")  # Output: Title: The Great Gatsby

# Create new XML
doc = pygixml.XMLDocument()
root = doc.append_child("catalog")
product = root.append_child("product")
product.append_child("name").set_value("Laptop")
product.append_child("price").set_value("999.99")

# Save to file
doc.save_file("output.xml")
```

## XPath Support

pygixml provides full XPath 1.0 support through pugixml's powerful XPath engine:

```python
import pygixml

xml_string = """
<library>
    <book id="1" category="fiction">
        <title>The Great Gatsby</title>
        <author>F. Scott Fitzgerald</author>
        <year>1925</year>
        <price>12.99</price>
    </book>
    <book id="2" category="fiction">
        <title>1984</title>
        <author>George Orwell</author>
        <year>1949</year>
        <price>10.99</price>
    </book>
</library>
"""

doc = pygixml.parse_string(xml_string)
root = doc.first_child()

# Select all books
books = root.select_nodes("book")
print(f"Found {len(books)} books")

# Select fiction books
fiction_books = root.select_nodes("book[@category='fiction']")
print(f"Found {len(fiction_books)} fiction books")

# Select specific book by ID
book_2 = root.select_node("book[@id='2']")
if book_2:
    title = book_2.node().child("title").child_value()
    print(f"Book ID 2: {title}")

# Use XPathQuery for repeated queries
query = pygixml.XPathQuery("book[year > 1930]")
recent_books = query.evaluate_node_set(root)
print(f"Found {len(recent_books)} books published after 1930")

# XPath boolean evaluation
has_orwell = pygixml.XPathQuery("book[author='George Orwell']").evaluate_boolean(root)
print(f"Has George Orwell books: {has_orwell}")

# XPath number evaluation
avg_price = pygixml.XPathQuery("sum(book/price) div count(book)").evaluate_number(root)
print(f"Average price: ${avg_price:.2f}")
```

### Supported XPath Features

- **Node selection**: `//book`, `/library/book`, `book[1]`
- **Attribute selection**: `book[@id]`, `book[@category='fiction']`
- **Boolean operations**: `and`, `or`, `not()`
- **Comparison operators**: `=`, `!=`, `<`, `>`, `<=`, `>=`
- **Mathematical operations**: `+`, `-`, `*`, `div`, `mod`
- **Functions**: `position()`, `last()`, `count()`, `sum()`, `string()`, `number()`
- **Axes**: `child::`, `attribute::`, `descendant::`, `ancestor::`
- **Wildcards**: `*`, `@*`, `node()`


## API Overview

### Core Classes

- **XMLDocument**: Create, parse, save XML documents
- **XMLNode**: Navigate and manipulate XML nodes  
- **XMLAttribute**: Handle XML attributes
- **XPathQuery**: Compile and execute XPath queries
- **XPathNode**: Result of XPath queries (wraps nodes and attributes)
- **XPathNodeSet**: Collection of XPath results

### Key Methods

#### XMLDocument/XMLNode Methods
- `parse_string(xml_string)` - Parse XML from string
- `parse_file(file_path)` - Parse XML from file
- `save_file(file_path)` - Save XML to file
- `append_child(name)` - Add child node
- `child(name)` - Get child by name
- `child_value()` - Get node value
- `attribute(name)` - Get attribute

#### XPath Methods
- `select_nodes(query)` - Select multiple nodes using XPath
- `select_node(query)` - Select single node using XPath
- `XPathQuery(query)` - Create reusable XPath query object
- `evaluate_node_set(context)` - Evaluate query and return node set
- `evaluate_node(context)` - Evaluate query and return first node
- `evaluate_boolean(context)` - Evaluate query and return boolean
- `evaluate_number(context)` - Evaluate query and return number
- `evaluate_string(context)` - Evaluate query and return string

## Benchmarks

Run performance comparisons:

```bash
# Run complete benchmark suite
python benchmarks/clean_visualization.py

# View results
cat benchmarks/results/benchmark_results.csv
```

The benchmark suite compares pygixml against:
- **lxml** - Industry-standard C-based parser
- **xml.etree.ElementTree** - Python standard library

**Benchmark Files:**
- `benchmarks/clean_visualization.py` - Main benchmark runner
- `benchmarks/benchmark_parsing.py` - Core benchmark logic
- `benchmarks/results/` - Generated CSV data and SVG charts

## Documentation

📖 **Full documentation** is available at: [https://mohammadraziei.github.io/pygixml/](https://mohammadraziei.github.io/pygixml/)

The documentation includes:
- Complete API reference with examples
- Installation guides for all platforms
- Performance benchmarks and optimization tips
- XPath 1.0 usage guide with comprehensive examples
- Real-world usage scenarios

## License

MIT License - see [LICENSE](LICENSE) file for details.

**To use this library, you must star the project on GitHub!**

This helps support the development and shows appreciation for the work. Please star the repository before using the library:

👉 **[Star pygixml on GitHub](https://github.com/MohammadRaziei/pygixml)**

## Acknowledgments

- [pugixml](https://pugixml.org/) - Fast and lightweight C++ XML processing library
- [Cython](https://cython.org/) - C extensions for Python
- [scikit-build](https://scikit-build.readthedocs.io/) - Modern Python build system
