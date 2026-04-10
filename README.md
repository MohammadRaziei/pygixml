# pygixml

<img src="https://github.com/MohammadRaziei/pygixml/raw/master/docs/images/pygixml.svg" width="450" />


[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![PyPI version](https://img.shields.io/pypi/v/pygixml.svg?color=blue)](https://pypi.org/project/pygixml/)
[![License: MIT](https://img.shields.io/badge/License-MIT-orange.svg)](https://opensource.org/licenses/MIT)
[![Build Status](https://github.com/MohammadRaziei/pygixml/actions/workflows/wheels.yml/badge.svg)](https://github.com/MohammadRaziei/pygixml/actions)
[![Documentation Status](https://github.com/MohammadRaziei/pygixml/actions/workflows/cmake.yml/badge.svg)](https://mohammadraziei.github.io/pygixml/)
[![GitHub Stars](https://img.shields.io/github/stars/MohammadRaziei/pygixml?style=social)](https://github.com/MohammadRaziei/pygixml)

A high-performance XML parser for Python based on Cython and
[pugixml](https://pugixml.org/).  Fast parsing, full XPath 1.0 support, and a
clean Pythonic API for reading, writing, and transforming XML.

📚 **[View Full Documentation](https://mohammadraziei.github.io/pygixml/)**

---

## Why pygixml?

**Speed, memory, and size.**  pygixml brings pugixml's battle-tested C++
parser directly to Python — with numbers that speak for themselves.

### Parsing Performance (5 000 elements, 50 iterations)

| Library         | Avg Time | Speedup vs ElementTree |
|-----------------|----------|------------------------|
| **pygixml**     | 0.0010 s | **8.4× faster**        |
| **lxml**        | 0.0044 s | 1.8× faster            |
| **ElementTree** | 0.0080 s | 1.0× (baseline)        |

### Memory Usage (5 000 elements, peak)

| Library         | Peak Memory | vs ElementTree |
|-----------------|-------------|----------------|
| **pygixml**     | **0.67 MB** | **7.2× less**  |
| **lxml**        | 0.67 MB     | 7.2× less      |
| **ElementTree** | 4.84 MB     | 1.0×           |

### Package Size

| Library     | Installed Size | vs lxml   |
|-------------|----------------|-----------|
| **pygixml** | **0.43 MB**    | **12.7× smaller** |
| lxml        | 5.48 MB        | 1.0×      |

*All numbers from `benchmarks/full_benchmark.py`.  See the
[Performance](https://mohammadraziei.github.io/pygixml/performance) page for
the full comparison across 6 XML sizes.*

### Features

* **Blazing-fast parsing** — up to 10× faster than ElementTree
* **Low memory** — 7× less than ElementTree, on par with lxml
* **Tiny footprint** — 0.43 MB installed (12.7× smaller than lxml)
* **Full XPath 1.0** — complete query engine with all standard functions
* **Pythonic API** — intuitive properties and methods, not a direct C++ mirror
* **Cross-platform** — Windows, Linux, macOS
* **Text extraction** — recursive text gathering with configurable joins
* **XML serialization** — output with custom indentation
* **Node iteration** — depth-first traversal of the entire document

---

## Installation

```bash
# From PyPI
pip install pygixml

# Or from GitHub
pip install git+https://github.com/MohammadRaziei/pygixml.git
```

---

## Quick Start

```python
import pygixml

# Parse XML from string
xml = """
<library>
    <book id="1" category="fiction">
        <title>The Great Gatsby</title>
        <author>F. Scott Fitzgerald</author>
        <year>1925</year>
    </book>
    <book id="2" category="fiction">
        <title>1984</title>
        <author>George Orwell</author>
        <year>1949</year>
    </book>
</library>
"""

doc = pygixml.parse_string(xml)
root = doc.root                           # <library>

# Access children and attributes
book = root.child("book")
print(book.name)                          # book
print(book.attribute("id").value)         # 1
print(book.child("title").text())         # The Great Gatsby

# XPath queries
fiction = root.select_nodes("book[@category='fiction']")
print(f"Found {len(fiction)} fiction books")

# Create & save
doc = pygixml.XMLDocument()
root = doc.append_child("catalog")
root.append_child("item").set_value("Hello")
doc.save_file("output.xml")
```

### Properties vs Methods

A quick reference so you don't get tripped up:

| **Properties** (no `()`)                | **Methods** (need `()`)              |
|-----------------------------------------|--------------------------------------|
| `node.name`, `node.value`, `node.type`  | `node.child(name)`                   |
| `node.parent`, `node.next_sibling`      | `node.first_child()`                 |
| `node.xml`, `node.xpath`                | `node.append_child(name)`            |
| `attr.name`, `attr.value`               | `node.set_value(v)`                  |
| `doc.root`                              | `node.select_nodes(query)`           |
|                                         | `node.first_attribute()`             |
|                                         | `node.text()`                        |

---

## Advanced Features

### Text Content Extraction

```python
import pygixml

xml = """
<root>
    <simple>Hello World</simple>
    <nested>
        <child>Child Text</child>
        More text
    </nested>
    <mixed>Text <b>with</b> mixed <i>content</i></mixed>
</root>
"""

doc = pygixml.parse_string(xml)
root = doc.root

# Direct text content of a child element
print(root.child("simple").text())                # Hello World

# Recursive text content (all descendant text joined)
nested = root.child("nested")
print(nested.text())                              # Child Text\nMore text
print(nested.text(join=" | "))                    # Child Text | More text

# Direct text only (non-recursive — immediate text children)
mixed = root.child("mixed")
print(mixed.text(recursive=False))                # Text
```

### XML Serialization

```python
import pygixml

doc = pygixml.XMLDocument()
root = doc.append_child("root")
root.append_child("item").set_value("content")

# Convenience property
print(root.xml)
# <root>
#   <item>content</item>
# </root>

# Custom indentation
print(root.to_string("    "))
```

### Document Iteration

```python
import pygixml

doc = pygixml.parse_string("<root><a/><b/></root>")

# Depth-first traversal of every node
for node in doc:
    print(f"{node.type:12s} {node.name}")
# document
# element       root
# element       a
# element       b
```

### Node Identity

```python
import pygixml

doc = pygixml.parse_string("<root><a/><b/></root>")
root = doc.root

a = root.child("a")
a2 = root.child("a")
print(a == a2)          # True — same underlying node
print(a.mem_id)         # Memory address for debugging
```

### Modifying XML

```python
import pygixml

doc = pygixml.parse_string("<person><name>John</name></person>")
root = doc.root

# Change text content
root.child("name").set_value("Jane")

# Rename an element
root.child("name").name = "full_name"

# Add children
root.append_child("age").set_value("30")

print(root.xml)
# <person>
#   <full_name>Jane</full_name>
#   <age>30</age>
# </person>
```

---

## XPath Support

Full XPath 1.0 via pugixml's engine:

```python
import pygixml

xml = """
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

doc = pygixml.parse_string(xml)
root = doc.root

# Select nodes
books = root.select_nodes("book")
print(f"Found {len(books)} books")

# Predicates
fiction = root.select_nodes("book[@category='fiction']")
print(f"Found {len(fiction)} fiction books")

# Single node
book = root.select_node("book[@id='2']")
if book:
    print(book.node.child("title").text())    # 1984

# Pre-compiled XPathQuery for repeated use
query = pygixml.XPathQuery("book[year > 1930]")
recent = query.evaluate_node_set(root)
print(f"Found {len(recent)} books published after 1930")

# Scalar evaluations
avg = pygixml.XPathQuery("sum(book/price) div count(book)").evaluate_number(root)
print(f"Average price: ${avg:.2f}")           # Average price: $11.99

has_orwell = pygixml.XPathQuery("book[author='George Orwell']").evaluate_boolean(root)
print(f"Has Orwell books: {has_orwell}")       # Has Orwell books: True
```

### Supported XPath

| Category           | Examples                                                        |
|--------------------|-----------------------------------------------------------------|
| Node selection     | `//book`, `/library/book`, `book[1]`                            |
| Attributes         | `book[@id]`, `book[@category='fiction']`                        |
| Boolean ops        | `and`, `or`, `not()`                                            |
| Comparisons        | `=`, `!=`, `<`, `>`, `<=`, `>=`                                 |
| Math               | `+`, `-`, `*`, `div`, `mod`                                     |
| Functions          | `position()`, `last()`, `count()`, `sum()`, `string()`, `number()` |
| Axes               | `child::`, `attribute::`, `descendant::`, `ancestor::`          |
| Wildcards          | `*`, `@*`, `node()`                                             |

---

## Core API

| Class            | Purpose                                              |
|------------------|------------------------------------------------------|
| `XMLDocument`    | Document-level operations: load, save, append-child   |
| `XMLNode`        | Navigate, read, and modify individual nodes           |
| `XMLAttribute`   | Attribute name and value access                       |
| `XPathQuery`     | Pre-compiled XPath queries for repeated evaluation    |
| `XPathNode`      | Single XPath result (wraps a node or attribute)       |
| `XPathNodeSet`   | Collection of XPath results                           |

Module-level functions: `parse_string(xml)`, `parse_file(path)`.

---

## Important: Element Nodes vs Text Nodes

In pugixml (and therefore pygixml), **element nodes do not store text as a
value**.  They contain child **text nodes** instead.

```python
# ❌  Setting value on an element node does nothing useful:
element.value = "some text"

# ✅  To SET text, append a text node (empty name) and set its value:
text_node = element.append_child("")
text_node.value = "some text"

# ✅  To GET text, use .text():
print(element.text())                     # "some text"

# ✅  Or read the text node directly:
print(element.first_child().value)        # "some text"
```

For most use-cases, `element.text()` is all you need.

---

## Benchmarks

Run the full benchmark suite on your machine:

```bash
# Full suite: parsing (6 sizes), memory (3 sizes), package size
python benchmarks/full_benchmark.py

# Legacy parsing-only benchmark
python benchmarks/benchmark_parsing.py
```

Compares pygixml against **lxml** and **xml.etree.ElementTree**.
Results are printed as tables and saved to
`benchmarks/results/benchmark_full.json`.

---

## Documentation

📖 Full docs: [https://mohammadraziei.github.io/pygixml/](https://mohammadraziei.github.io/pygixml/)

* Complete API reference
* Installation guides for all platforms
* Performance benchmarks and optimization tips
* XPath 1.0 usage guide with examples
* Real-world usage scenarios

---

## License

MIT License — see [LICENSE](LICENSE).

Enjoy pygixml?  Star the repository to support the development:
👉 **[Star pygixml on GitHub](https://github.com/MohammadRaziei/pygixml)**

---

## Acknowledgments

* [pugixml](https://pugixml.org/) — Fast and lightweight C++ XML library
* [Cython](https://cython.org/) — C extensions for Python
* [scikit-build](https://scikit-build.readthedocs.io/) — Modern Python build system
