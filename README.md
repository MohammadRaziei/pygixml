# pygixml: Python Giant XML

<img src="https://github.com/MohammadRaziei/pygixml/raw/master/docs/images/pygixml.svg" width="450" />


[![Python Versions](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![PyPI version](https://img.shields.io/pypi/v/pygixml.svg?color=blue)](https://pypi.org/project/pygixml/)
[![License: MIT](https://img.shields.io/badge/License-MIT-orange.svg)](https://opensource.org/licenses/MIT)
[![Build Status](https://github.com/MohammadRaziei/pygixml/actions/workflows/wheels.yml/badge.svg)](https://github.com/MohammadRaziei/pygixml/actions)
[![Documentation Status](https://github.com/MohammadRaziei/pygixml/actions/workflows/cmake.yml/badge.svg)](https://mohammadraziei.github.io/pygixml/)
[![GitHub Stars](https://img.shields.io/github/stars/MohammadRaziei/pygixml?style=social)](https://github.com/MohammadRaziei/pygixml)

**pygixml** (*Python Giant XML*) is a Cython framework built on two
specialized C++ engines: [pugixml](https://pugixml.org/) for its
in-memory DOM parser (XPath, `objectify`, `dictify`), and an inlined
[yxml](https://dev.yorhel.nl/yxml) push parser for true constant-memory
streaming. Between the two, pygixml covers everything
[lxml](https://lxml.de/) and [xmltodict](https://github.com/martinblech/xmltodict)
do: dotted `objectify` navigation, XPath 1.0, and an
xmltodict-compatible `dictify`, plus a streaming layer neither of them
has, which is what makes pygixml the package of choice for **big XML**
and big-data pipelines.

📚 **[View Full Documentation](https://mohammadraziei.github.io/pygixml/)**

---

## Why pygixml?

**Speed, memory, and size.** pygixml brings pugixml's battle-tested C++
parser directly to Python.

Every parsing/conversion layer pygixml ships (raw DOM, `dictify`,
`objectify`, `jsonify`) is measured against lxml, ElementTree,
xmltodict, and xmljson in a full, reproducible benchmark suite (see
[`benchmarks/`](benchmarks/)), not summarized here as a handful of
numbers that inevitably go stale the moment the code changes. The
live, interactive report (refreshed on a schedule, not hand-edited)
is on the
**[benchmarks page](https://mohammadraziei.github.io/pygixml/benchmarks/)**.

Two things worth knowing going in, because they're structural (true
regardless of which exact numbers the report shows this week), not a
one-time measurement:

* **`jsonify.stream_dump` holds memory flat as input grows.** Every
  DOM-based approach (pygixml's own DOM path included, lxml,
  xmltodict) allocates roughly in proportion to the input, so its
  memory use grows with file size. `stream_dump` never builds a tree
  at all, so it doesn't: this is a different complexity class (O(1)
  vs O(n)), not a fixed "X times less" you'd see at only one input
  size. It costs something in return: see the report's own memory
  panel for the honest trade-off, not just the part that flatters it.
* **Package size**: pygixml installs in well under a megabyte, without
  vendoring a build of libxml2/libxslt the way lxml does.

### Built for big XML

Those benchmark numbers are for documents that fit comfortably in
memory. For the documents that don't (multi-gigabyte exports, logs,
data dumps), pygixml's streaming layer is the part lxml and xmltodict
simply don't have:

* **`pygixml.iterfind` / `dictify.iterdict` / `jsonify.iterjsonl`**:
  yxml-based incremental parsing in **constant memory**: one element
  (or one dict, or one JSON line) in flight at a time, regardless of
  whether the source document is 10 KB or 10 GB.
* **`jsonify.stream_dump(xml_path, json_path)`** (the headline
  feature) converts a giant XML file into a single, valid, giant JSON
  file, **entirely in C++, in constant memory, with an
  xmltodict-compatible output shape** (same `@attr` / `#text` /
  repeated-siblings-as-array conventions as `dictify.parse`). No DOM
  tree is ever built, no intermediate Python dict/list/str is ever
  allocated, and the file never has to fit in RAM: only an in-place
  seek-and-patch trick on the *output* file is used to close JSON
  arrays correctly as repeated siblings are discovered. As far as we
  know, this is the only Python package that can do this without
  buffering the document, the output, or both, and without crashing
  the process once the file gets genuinely large.

  The memory guarantee is unconditional (measured: ~17MB peak,
  completely flat from 5K to 320K records, see the memory panel of the
  [benchmarks page](https://mohammadraziei.github.io/pygixml/benchmarks/)). The **time** is linear in the input size for every shape, including
  two or more different tags interleaving at the same level
  (`<a>1</a><b>1</b><a>2</a><b>2</b>...`): such siblings are moved
  into place once, in one pass, when their parent closes.
* **`jsonify.stream_jsonl(xml_path, jsonl_path, tag)`**: the
  file-to-file counterpart of `iterjsonl` (filters by `tag`, unlike
  `stream_dump` which always converts the whole document): streams
  straight to a `.jsonl` file, one matched element per line, same
  constant-memory, all-C++ guarantee.

```python
from pygixml import jsonify

# A multi-GB XML file in, a multi-GB JSON file out: peak memory stays flat.
jsonify.stream_dump("huge_export.xml", "huge_export.json")

# Or, one record per line:
jsonify.stream_jsonl("huge_export.xml", "huge_export.jsonl", "record")
```

### What is where

| Capability | API | Section |
|------------|-----|---------|
| In-memory DOM, XPath 1.0 | `parse_string`, `parse_file`, `XMLDocument`, `XMLNode`, `XPathQuery` | [Quick Start](#quick-start), [XPath Support](#xpath-support) |
| Dotted navigation | `objectify` | [objectify](#objectify-dotted-navigation) |
| XML to dict (xmltodict-compatible) | `dictify` | [dictify](#dictify-xml-to-dict) |
| XML to JSON, JSON Lines, constant memory | `jsonify` (`dumps*`, `stream_dump`, `stream_jsonl`) | [Built for big XML](#built-for-big-xml) |
| Streaming parse | `iterparse`, `iterfind`, `dictify.iterdict`, `jsonify.iterjsonl`, `PullParser` | [Built for big XML](#built-for-big-xml) |
| HTML to XML and back | `parse_html`, `html_to_xml`, `xml_to_html`, `encode_name`, `decode_name` | [HTML to XML and back](#html-to-xml-and-back) |
| Tree diff, patch, equality | `diff`, `patch`, `is_equal` | [Diff, patch and structural similarity](#diff-patch-and-structural-similarity) |
| Structural embeddings | `signature`, `similarity` | [Diff, patch and structural similarity](#diff-patch-and-structural-similarity) |
| Command line | `pygixml cat`, `query`, `jsonify`, `stream`, `convert`, `diff`, `similarity` | [Command Line Tools](#command-line-tools) |

### Features

* **Fast parsing**: pugixml's C++ DOM parser, consistently at or near
  the front across the benchmark suite (see the
  [benchmarks page](https://mohammadraziei.github.io/pygixml/benchmarks/))
* **Constant-memory streaming**: `jsonify.stream_dump` holds flat
  regardless of input size; nothing else compared here does
* **Small footprint**: well under a megabyte installed, no bundled
  libxml2/libxslt
* **Full XPath 1.0**: complete query engine with all standard functions
* **Pythonic API**: intuitive properties and methods, not a direct C++ mirror
* **`objectify`**: lxml.objectify-style dotted navigation
* **`dictify`**: xmltodict-compatible XML → dict conversion
* **`jsonify`**: direct XML → JSON, in memory or streamed straight to
  disk in constant memory (`stream_dump`, `stream_jsonl`)
* **HTML ↔ XML**: `parse_html` / `html_to_xml` turn real-world HTML into
  well-formed XML you can query with XPath, `xml_to_html` goes back; names
  XML can't hold are mapped reversibly (`encode_name` / `decode_name`)
* **Tree `diff` / `patch`**: an edit script between two XML or HTML
  documents (insert, delete, move, update text with an optional word-level
  diff, set/delete attribute), `patch` to apply it in place, `is_equal` for a
  one-pass "did anything change?": see
  [Diff, patch and structural similarity](#diff-patch-and-structural-similarity)
* **Structural embeddings**: `signature` (a pq-gram or path bag as a sparse
  `{hash: count}` vector) and `similarity` (Dice, 0..1) for near-duplicate and
  template detection, or as a cheap pre-filter before `diff`
* **Streaming (`iterfind`, `iterdict`, `iterjsonl`)**: constant-memory,
  yxml-based incremental parsing for documents too big to load whole
* **CLI tools**: `pygixml cat` (pretty-print/colorize), `pygixml
  query` (XPath/dotted query), `pygixml jsonify` (convert to JSON),
  `pygixml convert` (XML/JSON/YAML/TOON, any direction), `pygixml
  stream` (filter giant files in bounded memory), `pygixml diff` and
  `pygixml similarity` (compare two XML/HTML files): see
  [Command Line Tools](#command-line-tools)
* **Cross-platform**: Windows, Linux, macOS
* **Text extraction**: recursive text gathering with configurable joins
* **XML serialization**: output with custom indentation
* **Node iteration**: depth-first traversal of the entire document

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

## objectify: dotted navigation

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

# Dotted navigation: underscores map to hyphens automatically
print(root.user_profile.first_name)        # ObjectifiedElement(<first_name>)
print(str(root.user_profile.first_name))   # 'Mohammad'

# Automatic type inference for attributes
print(root.version)                        # 1.2   (float)
print(root.user_profile.id)               # 101   (int)
print(root.user_profile.verified)         # True  (bool)

# Text content
print(str(root.user_profile.first_name))  # 'Mohammad'   always str
print(root.user_profile.balance())        # 450.75        type-inferred

# Repeated siblings: indexing and iteration
print(root.entry[0])                      # ObjectifiedElement
print([str(e) for e in root.entry])       # ['Value A', 'Value B']

# Safe attribute access: never raises
print(root.get('version'))                # 1.2
print(root.get('missing', 'default'))     # 'default'

# Search descendants
print(root.find('balance'))               # ObjectifiedElement(<balance>)
print(root.find('balance', recursive=False))  # None  (not a direct child)
print(root.findall('entry'))              # [ObjectifiedElement, ...]

# Write support: modify in place
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

## dictify: XML to dict

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
    attr_prefix='',       # no prefix: attrs and children in same namespace
    cdata_key='text',     # key for text content (default '#text')
    force_list={'entry'}, # always a list, even with one element
    cdata_separator='',   # join text split by child elements (default: first run)
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
| `cdata_separator` | `None` | Text split by child elements (`Hi<br/>x`): `None` keeps the first non-blank run, a string joins all runs (`""` gives `"Hix"`) |
| `strip_whitespace` | `False` | Strip text at both ends (`parse` / `parse_file` only) |

| Function | Description |
|---|---|
| `dictify.parse(xml, **opts)` | Parse XML string → dict |
| `dictify.parse_file(path, **opts)` | Parse XML file → dict |
| `dictify.unparse(d, pretty, indent, ...)` | dict → XML string |

---

---

## HTML to XML and back

```python
import pygixml

# HTML -> well-formed XML, and back
pygixml.html_to_xml("<ul><li>a<li>b<br></ul>")
# '<ul><li>a</li><li>b<br/></li></ul>'
doc = pygixml.parse_html("<ul><li>a<li>b<br></ul>")      # a normal XMLDocument
pygixml.xml_to_html(doc, unwrap="root")
# '<ul><li>a</li><li>b<br></li></ul>'

# Names XML can't hold (o:p, @click, [prop] ...) are mapped reversibly with the
# SQL/XML rules; `case` picks lower-case (default), "keep" or "escape"
pygixml.html_to_xml("<o:p @Click=1>x</o:p>", case="keep")
# '<o_x003A_p _x0040_Click="1">x</o_x003A_p>'
pygixml.decode_name("_x0040_Click")                       # '@Click'
```

A document from `parse_html` remembers it came from HTML, so `to_html()`
restores the original names; a document from `parse_string` keeps its names as
they are. Because it is an ordinary `XMLDocument`, XPath, `dictify`, `jsonify`,
`objectify` and `diff` work on it too.

> [!NOTE]
> `parse_html` is a tolerant normaliser, not an HTML5 tree-builder. It always
> returns well-formed XML and keeps the text, but it does not reshape the tree
> the way a browser does: no implied `<html>` / `<body>` / `<tbody>`, no
> reordering of misnested formatting tags, no foster parenting of table text.
> If you need exactly the browser's DOM, use html5lib or selectolax.

> [!NOTE]
> Text next to CDATA or comments is one run, and `dictify` / `jsonify` read it
> the same way in every engine: `<p>a<![CDATA[b]]>c</p>` gives `'abc'`. This
> changed in 0.14.0 (it used to give `'a'`), see the [changelog](CHANGELOG.md).

See the HTML page of the documentation for the options.

---

## Diff, patch and structural similarity

Compare two *ordered trees* (XML, or HTML parsed with `parse_html`), apply the
difference, or measure how alike their structure is. Everything runs in C++
inside the extension, one call per function, with no extra dependency.

```python
import pygixml

a = pygixml.parse_html("<ul class='m'><li>Home<li>About us<li>Blog</ul>")
b = pygixml.parse_html("<ul class='m'><li>Home<li>About<li>Blog<li>Contact</ul>")

for action in pygixml.diff(a, b, text_diff=True):
    print(action)
# Insert(parent='/ul[1]', position=3, xml='<li>Contact</li>')
# UpdateText(path='/ul[1]/li[2]/text()[1]', text='About', old='About us',
#            diff=[(0, 'About'), (-1, ' us')])

pygixml.is_equal(a, b)           # False
pygixml.patch(a, pygixml.diff(a, b))     # applies the script to `a`, in place
pygixml.is_equal(a, b)           # True
```

### `diff`: an edit script

`diff(a, b)` returns a list, empty when the trees are equivalent, of these
actions, in the order they must be applied:

| Action | Meaning |
|--------|---------|
| `Insert(parent, position, xml)` | add a node (a wholly new subtree is **one** action) |
| `InsertText(parent, position, text)` | add a text node |
| `Delete(path)` | remove a node with everything under it |
| `Move(path, parent, position)` | move a subtree to another place |
| `UpdateText(path, text, old, diff)` | change a text or comment node; `diff` is a word-level diff when `text_diff=True` |
| `SetAttrib(path, name, value, old)` | set an attribute (`old` is `None` when it is new) |
| `DeleteAttrib(path, name, old)` | remove an attribute |

Paths look like `/ul[1]/li[2]/text()[1]` and refer to the tree as it is when
that action runs. The script is verified inside the call: applying it to `a`
must give `b`, otherwise `PygiXMLDiffError` is raised.

What counts as "the same" is a normalisation step, not a different algorithm:

| Option | Default | Effect |
|--------|---------|--------|
| `ignore_whitespace` | `True` | drop blank text, trim and collapse runs of whitespace |
| `ignore_comments` | `True` | comments are not compared |
| `ignore_attrs` | `()` | attribute names to ignore; `"data-*"` is a prefix |
| `class_as_set` | `True` | `class="b a a"` equals `class="a b"` |
| `keys` | `("id",)` | attributes that identify an element wherever it sits |
| `moves` | `True` | pair unmatched subtrees across parents (`Move`) |
| `text_diff` | `False` | attach a word-level diff (also CJK and Persian) to `UpdateText` |

Attribute order never matters, and elements are never renamed (a different tag
is a delete plus an insert).

```python
x = pygixml.parse_string("<r><i id='1'>a</i><i id='2'>b</i><i id='3'>c</i></r>")
y = pygixml.parse_string("<r><i id='3'>c</i><i id='1'>a2</i><i id='2'>b</i></r>")
pygixml.diff(x, y)
# [Move(path='/r[1]/i[3]', parent='/r[1]', position=0),
#  UpdateText(path='/r[1]/i[2]/text()[1]', text='a2', old='a', diff=None)]
```

### `patch` and `is_equal`

* `patch(doc, actions)` applies a script to a document **in place**. Every
  action checks what it expects (the path exists, the old text, the old
  attribute value), so a script is refused with `PygiXMLDiffError` when the
  document is not the one it was made for. Pass the same normalisation options
  you gave `diff`. It may leave the document partly patched: patch a copy if
  you need all-or-nothing.
* `is_equal(a, b, **options)` answers "did anything change?" in one pass by
  comparing subtree hashes, so it is the cheap check in front of a `diff`.

### Structural embeddings: `signature` and `similarity`

`signature(node)` turns the *structure* of a tree into a sparse vector,
`{hash: count}`, in time linear in the size of the tree. `similarity(a, b)` is
the Dice coefficient of two such vectors, from `0` (nothing shared) to `1` (same
structure), computed in one C++ call without building the dicts.

```python
pygixml.similarity(a, b)                      # 0.889: structure only
pygixml.similarity(a, b, content=True)        # 0.711: text counts too
pygixml.similarity(a, b, method="paths")      # 0.889: cruder and cheaper

sig = pygixml.signature(a)                    # {330417701356879974: 1, ...}
```

* `method="pqgram"` (default): pq-grams, windows of `p` ancestors and `q`
  consecutive children around every node (Augsten, Bohlen, Gamper, 2010). Their
  distance approximates the tree edit distance.
* `method="paths"`: the bag of root-to-node tag paths. Cruder, good for telling
  page templates apart.
* Text is one constant label unless `content=True`, so by default two pages
  built from the same template are as similar as can be, whatever they say.

Typical uses: near-duplicate and template detection across many pages, and a
cheap pre-filter before an expensive `diff`.

The matching algorithm (Chawathe et al., 1996), the limits and measured speeds
are in the [diff documentation](https://mohammadraziei.github.io/pygixml/docs/modules/diff.html).

---

## Command Line Tools

pygixml installs one CLI entry point, `pygixml`, with seven
subcommands: no Python code required for one-off queries,
conversions, comparing two files, or filtering giant files from a shell pipeline. Every
subcommand also works as `python -m pygixml <subcommand>`.

| Subcommand | Loads | Use it for |
|---|---|---|
| `pygixml cat` | full DOM | pretty-print (and colorize) an XML file for the terminal: the XML analog of `bat`/`jq -C` |
| `pygixml query` | full DOM | ad-hoc XPath / dotted queries: a `jq`/`xq`-style tool for XML you can fit in memory |
| `pygixml jsonify` (`json` alias) | DOM *or* streamed | converting a whole file to JSON, `.json` in / out |
| `pygixml stream` | one record at a time | filtering matches out of a file **too big to load**, bounded memory |
| `pygixml convert` | full DOM | converting between XML, JSON, YAML, TOON and HTML, any direction (`--case` for HTML names) |
| `pygixml diff` | two full DOMs | the edit script between two XML or HTML files, like `diff` for trees |
| `pygixml similarity` | two full DOMs | one number, 0..1, for how alike two files are structurally |

### `pygixml cat`: pretty-print and colorize

```bash
pygixml cat data.xml                    # pretty + colorized (auto: only
                                         # on a real terminal, and only
                                         # if colorama is installed)
cat data.xml | pygixml cat -            # from stdin
pygixml cat data.xml --color always     # force color even when piped
pygixml cat data.xml --color never      # force plain, no color
pygixml cat data.xml --indent 4         # 4-space indent instead of 2
pygixml cat data.xml -o pretty.xml      # write to a file (never colorized
                                         # by 'auto': a file isn't a tty)

python -m pygixml cat data.xml
```

Colorizing is fully optional: install it with `pip install
pygixml[all]` (pulls in `colorama`, along with YAML/TOON support for
`pygixml convert`). Without it, `cat`
still works exactly the same, just without color: plain, pretty-printed
XML, same as `--color never`.

### `pygixml query`

```bash
# XPath (starts with / or //)
pygixml query data.xml "//user-profile[@id='101']/first_name"

# dotted, objectify-style (starts with .): first segment names the root
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

### `pygixml jsonify`: convert a whole file

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

### `pygixml stream`: filter a giant file

Reads the file once via `iterparse`, tag by tag, holding at most one
matched element's subtree in memory: the right tool once a file is
too large for `pygixml query`/`pygixml jsonify`'s DOM mode.

```bash
# every <order>, one JSON object per line (JSONL)
pygixml stream orders.xml --tag order

# simple filters: numeric or string, on a child path or an @attribute
pygixml stream orders.xml --tag order --where "total>100"
pygixml stream orders.xml --tag order --where "@status=shipped"

# multiple --where are AND'ed together
pygixml stream orders.xml --tag order \
    --where "@status=shipped" --where "customer=acme"

# a real JSON array instead of JSONL: still one pass, still bounded memory
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

### `pygixml convert`: XML, JSON, YAML, TOON, any direction

```bash
pygixml convert data.xml -o data.json         # format guessed from extensions
pygixml convert data.xml -o data.yaml
pygixml convert data.json -o data.xml -p      # pretty XML
pygixml convert data.yaml --to toon           # stdout needs --to explicitly
cat data.xml | pygixml convert - --from xml --to json   # stdin needs --from too

python -m pygixml convert data.xml -o data.yaml
```

Built on :class:`pygixml.formats.FormatDocument`, a small class
wrapping a plain dict (the same `@attr`/`#text`/list shape
`dictify.parse` produces), with `to_json`/`to_xml`/`to_yaml`/`to_toon`
and matching `from_*` classmethods. JSON and XML always work (stdlib
`json` + this package's own `dictify`); YAML needs `PyYAML` and TOON
needs [`ctoon`](https://pypi.org/project/ctoon/) (also written by the
author of pygixml). Both are optional, and asking for one you don't
have gives a clear `pip install ...` error instead of crashing:

```bash
pip install pygixml[all]   # colorama (for `cat`) + PyYAML + ctoon
```

Like `cat`/`query`, this loads the whole document: for XML too big to
fit in memory, convert with `pygixml jsonify --stream` instead.

### `pygixml diff` and `pygixml similarity`: compare two files

```bash
pygixml diff old.html new.html
# insert   /ul[1] @3  <li>Contact</li>
# update   /ul[1]/li[2]/text()[1]  "About us" -> "About"

pygixml diff old.html new.html --text-diff     # About[- us-]: a word-level diff
pygixml diff a.xml b.xml --ignore-attrs 'data-*' --key id
pygixml diff a.xml b.xml --json | jq '.[] | select(.action == "Delete")'
pygixml diff a.html b.html -q || echo "changed"   # no output, exit 1 when they differ

pygixml similarity page1.html page2.html          # 0.889: structure only
pygixml similarity a.html b.html --content --method paths
```

A and B are XML or HTML files (the format comes from the extension, or
`--from xml|html`; `-` reads stdin for one of them). `diff` prints one line per
action (`insert`, `delete`, `move`, `update`, `set`, `unset`), or the same
actions as a JSON list with `--json`. The normalisation options of the Python
[`diff`](#diff-patch-and-structural-similarity) are flags: `--ignore-attrs`,
`--keep-whitespace`, `--keep-comments`, `--no-class-set`, `--key`, `--no-moves`.

Exit codes of `diff`: `0` when done, `1` for "they differ" only with
`--exit-code` or `-q`, `2` for trouble (unreadable file, input that does not
parse, bad option). `similarity` prints the score with three decimals.
Both load the two documents in memory.

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
| `pygixml cat`, `query`, `jsonify`, `convert`, `stream`, `diff`, `similarity` | CLI tools: see [Command Line Tools](#command-line-tools) |

Module-level functions: `parse_string(xml)`, `parse_file(path)`, `parse_html(html)`,
`html_to_xml(html)`, `xml_to_html(doc)`, and `diff` / `patch` / `is_equal` /
`similarity` / `signature` (see [HTML to XML and back](#html-to-xml-and-back) and [Diff, patch and structural similarity](#diff-patch-and-structural-similarity)).

---

## Benchmarks

```bash
cmake -S benchmarks -B benchmarks/build
cmake --build benchmarks/build --target pygixml_bench_report
```

Compares pygixml's parse/`dictify`/`objectify`/`jsonify` against
**lxml**, **ElementTree**, **xmltodict**, and **xmljson**: speed,
memory at scale, and install size; `parse_html` against **lxml.html**,
**BeautifulSoup**, **html5lib** and **selectolax** (speed and peak memory);
and the command-line tools against **xq**. Writes the raw numbers to
`benchmarks/results/*.json`; the docs build (`sphinx_docs`) renders
the interactive page from it. See
[`benchmarks/README.md`](benchmarks/README.md) for the full
methodology, or the live copy on the
[benchmarks page](https://mohammadraziei.github.io/pygixml/benchmarks/).

---

## Documentation

📖 Full docs: [https://mohammadraziei.github.io/pygixml/](https://mohammadraziei.github.io/pygixml/)


---

## Security

pygixml is not affected by the common XML attacks (XXE, Billion Laughs,
external DTD retrieval) that `lxml`/`defusedxml` guard against, because
its two embedded parsers, [pugixml](https://pugixml.org/) (DOM API) and
[yxml](https://dev.yorhel.nl/yxml) (streaming API), never implement
custom entity resolution or external DTD fetching in the first place, so
there's no "safe mode" to configure. See
[#8](https://github.com/MohammadRaziei/pygixml/issues/8) for the full
technical breakdown.

---

## License

MIT License: see [LICENSE](LICENSE).

Enjoy pygixml?  Star the repository ⭐
👉 **[Star pygixml on GitHub](https://github.com/MohammadRaziei/pygixml)**

---

## Acknowledgments

* [pugixml](https://pugixml.org/): Fast and lightweight C++ XML library
* [yxml](https://dev.yorhel.nl/yxml): Tiny, dependency-free streaming XML parser, powering pygixml's constant-memory streaming layer
* [Cython](https://cython.org/): C extensions for Python
* [scikit-build](https://scikit-build.readthedocs.io/): Modern Python build system