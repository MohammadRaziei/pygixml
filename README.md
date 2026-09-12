# pygixml — Python Giant XML

<img src="https://github.com/MohammadRaziei/pygixml/raw/master/docs/images/pygixml.svg" width="450" />


[![Python Versions](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![PyPI version](https://img.shields.io/pypi/v/pygixml.svg?color=blue)](https://pypi.org/project/pygixml/)
[![License: MIT](https://img.shields.io/badge/License-MIT-orange.svg)](https://opensource.org/licenses/MIT)
[![Build Status](https://github.com/MohammadRaziei/pygixml/actions/workflows/wheels.yml/badge.svg)](https://github.com/MohammadRaziei/pygixml/actions)
[![Documentation Status](https://github.com/MohammadRaziei/pygixml/actions/workflows/cmake.yml/badge.svg)](https://mohammadraziei.github.io/pygixml/)
[![GitHub Stars](https://img.shields.io/github/stars/MohammadRaziei/pygixml?style=social)](https://github.com/MohammadRaziei/pygixml)

**pygixml** — *Python Giant XML* — is a Cython framework built on two
specialized C++ engines: [pugixml](https://pugixml.org/) for its
in-memory DOM parser (XPath, `objectify`, `dictify`), and an inlined
[yxml](https://dev.yorhel.nl/yxml) push parser for true constant-memory
streaming. Between the two, pygixml covers everything
[lxml](https://lxml.de/) and [xmltodict](https://github.com/martinblech/xmltodict)
do — dotted `objectify` navigation, XPath 1.0, and an
xmltodict-compatible `dictify` — plus a streaming layer neither of them
has, which is what makes pygixml the package of choice for **big XML**
and big-data pipelines.

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

### Built for big XML

Those benchmark numbers are for documents that fit comfortably in
memory. For the documents that don't — multi-gigabyte exports, logs,
data dumps — pygixml's streaming layer is the part lxml and xmltodict
simply don't have:

* **`pygixml.iterfind` / `dictify.iterdict` / `jsonify.iterjsonl`** —
  yxml-based incremental parsing in **constant memory**: one element
  (or one dict, or one JSON line) in flight at a time, regardless of
  whether the source document is 10 KB or 10 GB.
* **`jsonify.stream_dump(xml_path, json_path)`** — the headline
  feature: converts a giant XML file into a single, valid, giant JSON
  file, **entirely in C++, in constant memory, with an
  xmltodict-compatible output shape** (same `@attr` / `#text` /
  repeated-siblings-as-array conventions as `dictify.parse`). No DOM
  tree is ever built, no intermediate Python dict/list/str is ever
  allocated, and the file never has to fit in RAM — only an in-place
  seek-and-patch trick on the *output* file is used to close JSON
  arrays correctly as repeated siblings are discovered. As far as we
  know, this is the only Python package that can do this without
  buffering the document, the output, or both, and without crashing
  the process once the file gets genuinely large.

  The memory guarantee is unconditional (verified: ~17MB peak,
  completely flat from 5K to 640K records — see
  `benchmarks/adhoc/bench_record_shaped.py`). The **time** guarantee
  is O(n) for the shape almost all real giant XML actually has — one
  repeated tag per nesting level (`<orders><order>...</order>...`).
  It degrades towards O(n²) only in an adversarial shape: two or more
  *different* tags repeating and interleaving at the *same* level for
  many iterations (e.g. `<a>1</a><b>1</b><a>2</a><b>2</b>...` with no
  wrapping element around each pair). If that's genuinely your data
  shape, `jsonify.stream_jsonl` (below) sidesteps the problem entirely
  by not trying to preserve a single JSON document at all.
* **`jsonify.stream_jsonl(xml_path, jsonl_path, tag)`** — the
  file-to-file counterpart of `iterjsonl` (filters by `tag`, unlike
  `stream_dump` which always converts the whole document): streams
  straight to a `.jsonl` file, one matched element per line, same
  constant-memory, all-C++ guarantee.

```python
from pygixml import jsonify

# A multi-GB XML file in, a multi-GB JSON file out -- peak memory stays flat.
jsonify.stream_dump("huge_export.xml", "huge_export.json")

# Or, one record per line:
jsonify.stream_jsonl("huge_export.xml", "huge_export.jsonl", "record")
```

### Features

* **Blazing-fast parsing** — up to 14× faster than ElementTree
* **Low memory** — 7× less than ElementTree, on par with lxml
* **Tiny footprint** — 0.43 MB installed (12.7× smaller than lxml)
* **Full XPath 1.0** — complete query engine with all standard functions
* **Pythonic API** — intuitive properties and methods, not a direct C++ mirror
* **`objectify`** — lxml.objectify-style dotted navigation
* **`dictify`** — xmltodict-compatible XML → dict conversion
* **`jsonify`** — direct XML → JSON, in memory or streamed straight to
  disk in constant memory (`stream_dump`, `stream_jsonl`)
* **Streaming (`iterfind`, `iterdict`, `iterjsonl`)** — constant-memory,
  yxml-based incremental parsing for documents too big to load whole
* **CLI tools** — `pygixml cat` (pretty-print/colorize), `pygixml
  query` (XPath/dotted query), `pygixml jsonify` (convert to JSON),
  `pygixml convert` (XML/JSON/YAML/TOON, any direction), `pygixml
  stream` (filter giant files in bounded memory) — see
  [Command Line Tools](#command-line-tools)
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

# Write support — modify in place
root.user_profile.first_name = "Ali"      # update child element text
root.version = 2.0                        # update attribute
root.timeout = 30                         # create new child element

# Delete
del root.timeout                          # remove child element
del root.version                          # remove attribute
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
| `elem.name = value` | Update child text or attribute; create child if absent |
| `del elem.name` | Remove child element or attribute |
| `elem.tag` | XML tag name string |
| `elem.attrib` | `{name: typed_value}` dict of all attributes |
| `elem.xml` | Serialised XML of the subtree |
| Child beats attribute | When both share a name, child wins (read and write) |

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

---

## Command Line Tools

pygixml installs one CLI entry point, `pygixml`, with three
subcommands — no Python code required for one-off queries,
conversions, or filtering giant files from a shell pipeline. Every
subcommand also works as `python -m pygixml <subcommand>`.

| Subcommand | Loads | Use it for |
|---|---|---|
| `pygixml cat` | full DOM | pretty-print (and colorize) an XML file for the terminal — the XML analog of `bat`/`jq -C` |
| `pygixml query` | full DOM | ad-hoc XPath / dotted queries — a `jq`/`xq`-style tool for XML you can fit in memory |
| `pygixml jsonify` (`json` alias) | DOM *or* streamed | converting a whole file to JSON, `.json` in / out |
| `pygixml stream` | one record at a time | filtering matches out of a file **too big to load**, bounded memory |
| `pygixml convert` | full DOM | converting between XML, JSON, YAML, and TOON, any direction |

### `pygixml cat` — pretty-print and colorize

```bash
pygixml cat data.xml                    # pretty + colorized (auto: only
                                         # on a real terminal, and only
                                         # if colorama is installed)
cat data.xml | pygixml cat -            # from stdin
pygixml cat data.xml --color always     # force color even when piped
pygixml cat data.xml --color never      # force plain, no color
pygixml cat data.xml --indent 4         # 4-space indent instead of 2
pygixml cat data.xml -o pretty.xml      # write to a file (never colorized
                                         # by 'auto' -- a file isn't a tty)

python -m pygixml cat data.xml
```

Colorizing is fully optional — install it with `pip install
pygixml[all]` (pulls in `colorama`, along with YAML/TOON support for
`pygixml convert`). Without it, `cat`
still works exactly the same, just without color: plain, pretty-printed
XML, same as `--color never`.

### `pygixml query`

```bash
# XPath (starts with / or //)
pygixml query data.xml "//user-profile[@id='101']/first_name"

# dotted, objectify-style (starts with .) — first segment names the root
pygixml query data.xml ".database.user_profile.first_name"
pygixml query data.xml ".database.user_profile.@id"      # attribute
pygixml query data.xml ".database.entry[1]"              # index
pygixml query data.xml ".database.entry[*]"              # all siblings
pygixml query data.xml ".database.user_profile.text()"   # text content

# output formats
pygixml query data.xml ".database" --format xml
pygixml query data.xml ".database" --format json --pretty

# just the count, exit code like grep (0 = match, 1 = no match)
pygixml query data.xml ".database.entry[*]" --count

# multiple files, stdin, NUL-separated for xargs -0
pygixml query *.xml ".config.host"
cat data.xml | pygixml query - ".config.host"
pygixml query data.xml ".database.entry[*]" --null | xargs -0 -n1 echo

# python -m form works identically
python -m pygixml query data.xml ".database.user_profile.first_name"
```

### `pygixml jsonify` — convert a whole file

```bash
pygixml jsonify data.xml                        # compact JSON to stdout
pygixml jsonify data.xml -p                     # pretty (2-space indent)
pygixml jsonify data.xml -o data.json           # write to a file
pygixml jsonify data.xml --force-list item      # always make <item> a list
cat data.xml | pygixml jsonify -                # read from stdin

python -m pygixml jsonify data.xml -o data.json
pygixml json data.xml                           # `json` is a short alias
```

Automatically switches to `jsonify.stream_dump` (constant memory) for
files over 64MB; `--stream` / `--no-stream` force one mode or the
other regardless of size.

### `pygixml stream` — filter a giant file

Reads the file once via `iterparse`, tag by tag, holding at most one
matched element's subtree in memory — the right tool once a file is
too large for `pygixml query`/`pygixml jsonify`'s DOM mode.

```bash
# every <order>, one JSON object per line (JSONL)
pygixml stream orders.xml --tag order

# simple filters — numeric or string, on a child path or an @attribute
pygixml stream orders.xml --tag order --where "total>100"
pygixml stream orders.xml --tag order --where "@status=shipped"

# multiple --where are AND'ed together
pygixml stream orders.xml --tag order \
    --where "@status=shipped" --where "customer=acme"

# a real JSON array instead of JSONL — still one pass, still bounded memory
pygixml stream orders.xml --tag order --where "total>100" --format array -p

# just count, or stop after N
pygixml stream orders.xml --tag order --where "@status=shipped" --count
pygixml stream orders.xml --tag order --limit 10

cat orders.xml | pygixml stream - --tag order
python -m pygixml stream orders.xml --tag order
```

`--where` supports `=`, `!=`, `>`, `<`, `>=`, `<=`; the left-hand side
is either `@attr` or a child path like `customer` / `items/item/sku`
(same syntax as `StreamElement.findtext`).

---

---

### `pygixml convert` — XML, JSON, YAML, TOON, any direction

```bash
pygixml convert data.xml -o data.json         # format guessed from extensions
pygixml convert data.xml -o data.yaml
pygixml convert data.json -o data.xml -p      # pretty XML
pygixml convert data.yaml --to toon           # stdout needs --to explicitly
cat data.xml | pygixml convert - --from xml --to json   # stdin needs --from too

python -m pygixml convert data.xml -o data.yaml
```

Built on :class:`pygixml.formats.FormatDocument` -- a small class
wrapping a plain dict (the same `@attr`/`#text`/list shape
`dictify.parse` produces), with `to_json`/`to_xml`/`to_yaml`/`to_toon`
and matching `from_*` classmethods. JSON and XML always work (stdlib
`json` + this package's own `dictify`); YAML needs `PyYAML` and TOON
needs [`ctoon`](https://pypi.org/project/ctoon/) (also written by the
author of pygixml) -- both are optional, and asking for one you don't
have gives a clear `pip install ...` error instead of crashing:

```bash
pip install pygixml[all]   # colorama (for `cat`) + PyYAML + ctoon
```

Like `cat`/`query`, this loads the whole document — for XML too big to
fit in memory, convert with `pygixml jsonify --stream` instead.

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
| `jsonify`        | Direct XML → JSON: in-memory `dumps*`, or constant-memory `stream_dump`/`stream_jsonl` |
| `iterfind` / `iterparse` | yxml-based constant-memory streaming parser, `ElementTree`-style |
| `pygixml cat`, `pygixml query`, `pygixml jsonify`, `pygixml convert`, `pygixml stream` | CLI tools — see [Command Line Tools](#command-line-tools) |

Module-level functions: `parse_string(xml)`, `parse_file(path)`.

---

## Benchmarks

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


---

## Security

pygixml is not affected by the common XML attacks (XXE, Billion Laughs,
external DTD retrieval) that `lxml`/`defusedxml` guard against, because
its two embedded parsers — [pugixml](https://pugixml.org/) (DOM API) and
[yxml](https://dev.yorhel.nl/yxml) (streaming API) — never implement
custom entity resolution or external DTD fetching in the first place, so
there's no "safe mode" to configure. See
[#8](https://github.com/MohammadRaziei/pygixml/issues/8) for the full
technical breakdown.

---

## License

MIT License — see [LICENSE](LICENSE).

Enjoy pygixml?  Star the repository ⭐
👉 **[Star pygixml on GitHub](https://github.com/MohammadRaziei/pygixml)**

---

## Acknowledgments

* [pugixml](https://pugixml.org/) — Fast and lightweight C++ XML library
* [yxml](https://dev.yorhel.nl/yxml) — Tiny, dependency-free streaming XML parser, powering pygixml's constant-memory streaming layer
* [Cython](https://cython.org/) — C extensions for Python
* [scikit-build](https://scikit-build.readthedocs.io/) — Modern Python build system