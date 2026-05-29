# pygixml

<img src="https://github.com/MohammadRaziei/pygixml/raw/master/docs/images/pygixml.svg" width="450" />


[![Python Versions](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
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
| **pygixml**     | 0.0009 s | **9.2× faster**        |
| **lxml**        | 0.0041 s | 2.0× faster            |
| **ElementTree** | 0.0083 s | 1.0× (baseline)        |

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

* **Blazing-fast parsing** — up to 14× faster than ElementTree
* **Low memory** — 7× less than ElementTree, on par with lxml
* **Tiny footprint** — 0.43 MB installed (12.7× smaller than lxml)
* **Full XPath 1.0** — complete query engine with all standard functions
* **Pythonic API** — intuitive properties and methods, not a direct C++ mirror
* **`objectify`** — lxml.objectify-style dotted navigation
* **`dictify`** — xmltodict-compatible XML → dict conversion
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

## objectify — dotted navigation

`pygixml.objectify` provides an [lxml.objectify](https://lxml.de/objectify.html)-inspired
interface for navigating XML with plain Python attribute access.

```python
from pygixml import objectify

xml = """
<database name="users_db" version="1.2">
    <user-profile id="101" verified="true">
        <first_name>Mohammad</first_name>
        <balance>450.75</balance>
    </user-profile>
    <entry>Value A</entry>
    <entry>Value B</entry>
</database>
"""

root = objectify.from_string(xml)

# Dotted navigation — underscores map to hyphens automatically
print(root.user_profile.first_name)        # ObjectifiedElement(<first_name>)
print(str(root.user_profile.first_name))   # 'Mohammad'

# Automatic type inference for attributes
print(root.version)                        # 1.2   (float)
print(root.user_profile.id)               # 101   (int)
print(root.user_profile.verified)         # True  (bool)

# Text content
print(str(root.user_profile.first_name))  # 'Mohammad'   always str
print(root.user_profile.balance())        # 450.75        type-inferred

# Repeated siblings — indexing and iteration
print(root.entry[0])                      # ObjectifiedElement
print([str(e) for e in root.entry])       # ['Value A', 'Value B']

# Safe attribute access — never raises
print(root.get('version'))                # 1.2
print(root.get('missing', 'default'))     # 'default'

# Search descendants
print(root.find('balance'))               # ObjectifiedElement(<balance>)
print(root.find('balance', recursive=False))  # None  (not a direct child)
print(root.findall('entry'))              # [ObjectifiedElement, ...]
```

### objectify API

| Feature | Behaviour |
|---|---|
| `root.child_tag` | First `<child_tag>` element; falls back to `<child-tag>` |
| `root.attr_name` | Attribute value (type-inferred) when no child matches |
| `root.tag[n]` | Index into repeated siblings |
| `for e in root.tag` | Iterate repeated siblings |
| `str(elem)` | Raw text content, always `str` |
| `elem()` | Type-inferred text content |
| `elem.get(name, default)` | Safe attribute read, never raises |
| `elem.find(tag)` | First matching descendant, or `None` |
| `elem.findall(tag)` | All matching descendants |
| `elem.tag` | XML tag name string |
| `elem.attrib` | `{name: typed_value}` dict of all attributes |
| `elem.xml` | Serialised XML of the subtree |
| Child beats attribute | When both share a name, child wins |

---

## dictify — XML to dict

`pygixml.dictify` converts XML to a nested dict, compatible with the
[xmltodict](https://github.com/martinblech/xmltodict) library.

```python
from pygixml import dictify

xml = """
<database name="users_db" version="1.2">
    <user-profile id="101" verified="true">
        <first_name>Mohammad</first_name>
        <balance>450.75</balance>
    </user-profile>
    <entry>Value A</entry>
    <entry>Value B</entry>
</database>
"""

# Parse XML → dict
d = dictify.parse(xml)
# {
#   'database': {
#     '@name': 'users_db',
#     '@version': '1.2',
#     'user-profile': {
#       '@id': '101', '@verified': 'true',
#       'first_name': 'Mohammad', 'balance': '450.75'
#     },
#     'entry': ['Value A', 'Value B']
#   }
# }

# Repeated siblings → list automatically
print(d['database']['entry'])             # ['Value A', 'Value B']

# Attributes prefixed with '@'
print(d['database']['@name'])             # 'users_db'

# Custom options
d = dictify.parse(xml,
    attr_prefix='',       # no prefix — attrs and children in same namespace
    cdata_key='text',     # key for text content (default '#text')
    force_list={'entry'}, # always a list, even with one element
)

# Parse from file
d = dictify.parse_file('data.xml')

# Convert back to XML
xml_out = dictify.unparse(d, pretty=True, indent='\t')
print(xml_out)
```

### dictify API

| Parameter | Default | Description |
|---|---|---|
| `attr_prefix` | `"@"` | Prefix added to attribute keys |
| `cdata_key` | `"#text"` | Key for text content in mixed nodes |
| `force_list` | `None` | Tag names always wrapped in a list; pass `True` for all |

| Function | Description |
|---|---|
| `dictify.parse(xml, **opts)` | Parse XML string → dict |
| `dictify.parse_file(path, **opts)` | Parse XML file → dict |
| `dictify.unparse(d, pretty, indent, ...)` | dict → XML string |

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

print(root.child("simple").text())                # Hello World
print(root.child("nested").text(join=" | "))      # Child Text | More text
print(root.child("mixed").text(recursive=False))  # Text
```

### XML Serialization

```python
import pygixml

doc = pygixml.XMLDocument()
root = doc.append_child("root")
root.append_child("item").set_value("content")

print(root.xml)
# <root>
#   <item>content</item>
# </root>

print(root.to_string("    "))  # 4-space indent
```

### Document Iteration

```python
import pygixml

doc = pygixml.parse_string("<root><a/><b/></root>")

for node in doc:
    print(f"{node.type:12s} {node.name}")
# document
# element       root
# element       a
# element       b
```

### Modifying XML

```python
import pygixml

doc = pygixml.parse_string("<person><name>John</name></person>")
root = doc.root

root.child("name").set_value("Jane")
root.child("name").name = "full_name"
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

# Pre-compiled query for repeated use
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

| Class / Module   | Purpose                                                    |
|------------------|------------------------------------------------------------|
| `XMLDocument`    | Document-level operations: load, save, append-child        |
| `XMLNode`        | Navigate, read, and modify individual nodes                |
| `XMLAttribute`   | Attribute name and value access                            |
| `XPathQuery`     | Pre-compiled XPath queries for repeated evaluation         |
| `XPathNode`      | Single XPath result (wraps a node or attribute)            |
| `XPathNodeSet`   | Collection of XPath results                                |
| `objectify`      | lxml.objectify-style dotted navigation                     |
| `dictify`        | xmltodict-compatible XML → dict conversion                 |

Module-level functions: `parse_string(xml)`, `parse_file(path)`.

---

## Benchmarks

Run the full benchmark suite on your machine:

```bash
python benchmarks/full_benchmark.py
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

Enjoy pygixml?  Star the repository ⭐
👉 **[Star pygixml on GitHub](https://github.com/MohammadRaziei/pygixml)**

---

## Acknowledgments

* [pugixml](https://pugixml.org/) — Fast and lightweight C++ XML library
* [Cython](https://cython.org/) — C extensions for Python
* [scikit-build](https://scikit-build.readthedocs.io/) — Modern Python build system
