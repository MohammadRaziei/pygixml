# pygixml

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Build Status](https://github.com/MohammadRaziei/pygixml/actions/workflows/python.yml/badge.svg)](https://github.com/MohammadRaziei/pygixml/actions)
[![GitHub Stars](https://img.shields.io/github/stars/MohammadRaziei/pygixml?style=social)](https://github.com/MohammadRaziei/pygixml)

A high-performance Python wrapper for [pugixml](https://pugixml.org/) using Cython, providing fast XML parsing and manipulation capabilities.



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

## Quick SWtart

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

## API Overview

### Core Classes

- **XMLDocument**: Create, parse, save XML documents
- **XMLNode**: Navigate and manipulate XML nodes  
- **XMLAttribute**: Handle XML attributes

### Key Methods

- `parse_string(xml_string)` - Parse XML from string
- `parse_file(file_path)` - Parse XML from file
- `save_file(file_path)` - Save XML to file
- `append_child(name)` - Add child node
- `child(name)` - Get child by name
- `child_value()` - Get node value
- `attribute(name)` - Get attribute

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

## License

MIT License - see [LICENSE](LICENSE) file for details.

**To use this library, you must star the project on GitHub!**

This helps support the development and shows appreciation for the work. Please star the repository before using the library:

👉 **[Star pygixml on GitHub](https://github.com/MohammadRaziei/pygixml)**

## Acknowledgments

- [pugixml](https://pugixml.org/) - Fast and lightweight C++ XML processing library
- [Cython](https://cython.org/) - C extensions for Python
- [scikit-build](https://scikit-build.readthedocs.io/) - Modern Python build system
