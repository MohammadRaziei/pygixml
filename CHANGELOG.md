# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [0.13.0] - 2026-05-31

### Added

#### `pygixml.jsonify` — direct XML → JSON serialization
- New module `jsonify` (compiled into `pygixml_cy.so` via `jsonify.pxi`).
- C++ inline serializer (`xml_node_to_json`) that traverses the pugixml
  node tree and writes directly into a `std::string` buffer — **no Python
  dict, list, or intermediate str is allocated during traversal**.  Only
  one Python `str` object is created at the very end.
- `jsonify.dumps(xml, ...)` — parse XML string and serialize directly to
  JSON string.
- `jsonify.dumps_file(path, ...)` — parse XML file and serialize directly
  to JSON string.
- `jsonify.dumps_node(elem, ...)` — serialize an already-parsed
  `ObjectifiedElement` subtree to JSON without re-parsing.
- Follows the same conventions as `dictify.parse`:
  - Attributes prefixed with `attr_prefix` (default `"@"`).
  - Text content in mixed nodes stored under `cdata_key` (default `"#text"`).
  - Repeated siblings collapsed into a JSON array automatically.
  - Empty / whitespace-only elements become JSON `null`.
- `force_list` and `force_all` support.
- `pretty` and `indent` options for formatted output.
- C++ `json_escape()` handles all JSON string escaping including control
  characters, `\n`, `\r`, `\t`, `\"`, `\\`.
- Output is consistent with `dictify.parse` + `json.dumps` — the
  `TestConsistencyWithDictify` test class verifies this.

### Changed
- `pygixml/__init__.py` exports `jsonify` module and `jsonify_dumps`,
  `jsonify_dumps_file`, `jsonify_dumps_node`.
- `pygixml_cy.pyx` include order: `objectify.pxi` → `namespace.pxi` →
  `dictify.pxi` → `jsonify.pxi`.

### Testing
- Added `tests/test_jsonify.py` — 9 test classes, ~40 tests covering:
  basic structure, valid JSON output, options, `force_list`, pretty printing,
  `dumps_file`, `dumps_node`, consistency with dictify, and edge cases.


## [0.12.0] - 2026-05-31

### Added

#### Namespace support for `pygixml.objectify`
- New `namespace.pxi` compiled into `pygixml_cy.so` (include after
  `objectify.pxi`).
- `NamespacedElement` — `cdef class` extending `ObjectifiedElement` with a
  `_ns_map` C-level field storing `{prefix: uri}`.
- **Auto-detection** — `objectify_from_string` and `objectify_from_file` now
  automatically extract all `xmlns` declarations from the document (via
  `_extract_ns_map_recursive`) and return a `NamespacedElement` when any are
  found.  Plain XML without namespaces continues to return a plain
  `ObjectifiedElement` — fully backward compatible.
- **Three lookup styles** supported simultaneously:
  - Clark notation: `root.find("{http://ns.com}item")`
  - Prefix notation: `root.find("ns:item")`
  - Dotted access: `root.ns_item` (underscore→colon mapping via
    `_ns_candidate_names`)
- `NamespacedElement.ns_map` property — exposes the active namespace map for
  inspection and debugging.
- `namespaces` parameter on `objectify_from_string` and `objectify_from_file`
  — allows callers to supply or override prefix→URI mappings.
- `auto_ns=False` parameter — opt out of automatic namespace extraction and
  get a plain `ObjectifiedElement`.
- `ns_map` is inherited by every child, `find()`, and `findall()` result
  automatically — no manual propagation needed.
- `_extract_ns_map(xml_node)` — C-level helper extracting `xmlns` attributes
  from a single node.
- `_extract_ns_map_recursive(xml_node)` — C-level helper walking the full
  subtree.
- `_ns_candidate_names(str, dict)` — C-level helper expanding a Python
  identifier into Clark / prefix / hyphen candidates.
- `_ns_collect_siblings` and `_ns_find_all` — namespace-aware variants of
  the sibling collection and search helpers.

### Changed
- `objectify_from_string` and `objectify_from_file` signatures extended with
  `namespaces=None` and `auto_ns=True` — fully backward compatible.
- `objectify.py` shim exports `NamespacedElement`.
- `pygixml/__init__.py` exports `NamespacedElement`.

### Testing
- Added `tests/test_namespace.py` — 7 test classes, ~40 tests covering:
  auto-detection, dotted access, Clark notation, prefix notation, `findall`,
  ns_map inheritance, real-world Atom feed, and backward compatibility.


## [0.11.0] - 2026-05-31

### Added

#### `pygixml.objectify` — lxml.objectify-style interface
- New module `objectify` (compiled into `pygixml_cy.so` via `objectify.pxi`)
  providing an lxml.objectify-inspired API for navigating XML with plain Python
  attribute access.
- `objectify.from_string(xml)` and `objectify.from_file(path)` entry points
  returning an `ObjectifiedElement` wrapping the document root.
- `ObjectifiedElement` — `cdef class` storing the pugixml `xml_node` struct
  directly at the C level (zero Python wrapper allocation per access).
- `NodeSequence` — `cdef class` returned when multiple direct siblings share
  a tag; supports indexing (including negative), iteration, and `len()`.
- **Dotted navigation** — `root.child_tag` finds `<child_tag>` or falls back
  to `<child-tag>` (underscore→hyphen mapping).
- **Automatic type inference** for attribute values and leaf-node text:
  `"true"`/`"false"` → `bool`, integer strings → `int`, decimal/scientific
  strings → `float`, everything else → `str`.
- **Text access** — `str(elem)` returns raw text (always `str`); calling
  `elem()` returns type-inferred text content.
- **Conflict resolution** — child elements take priority over same-named
  attributes in both read and write operations.
- `elem.get(name, default=None)` — safe attribute read that never raises;
  mirrors `dict.get()`.
- `elem.find(tag, recursive=True)` — returns the first matching descendant
  element or `None`; hyphen mapping applies.
- `elem.findall(tag, recursive=True)` — returns all matching descendants in
  document order; hyphen mapping applies.
- **Write support** via `__setattr__`:
  - Assigns to an existing child element's text content (via `node_pcdata`).
  - Updates an existing attribute value in-place.
  - Creates a new child element when neither exists.
- **Delete support** via `__delattr__` — removes child elements or attributes
  by name; raises `AttributeError` when not found.
- `elem.tag` — XML tag name property.
- `elem.attrib` — all attributes as a `{name: typed_value}` dict; walks the
  C-level attribute linked list directly.
- `elem.text_content` — raw text content property, always `str`.
- `elem.xml` — serialised XML of the node and its subtree.
- Document lifetime safety — `_doc_ref` slot keeps the owning `XMLDocument`
  alive for the lifetime of any `ObjectifiedElement` wrapper.

#### `pygixml.dictify` — xmltodict-compatible interface
- New module `dictify` (compiled into `pygixml_cy.so` via `dictify.pxi`)
  providing an API compatible with the `xmltodict` library.
- `dictify.parse(xml, attr_prefix, cdata_key, force_list)` — parses an XML
  string into a nested dict following xmltodict conventions:
  - Attributes prefixed with `"@"` (configurable via `attr_prefix`).
  - Text content in mixed nodes stored under `"#text"` (configurable via
    `cdata_key`).
  - Repeated sibling elements automatically collapsed into a list.
  - Empty and whitespace-only elements become `None`.
  - `force_list` — set of tag names (or `True`) always wrapped in a list.
- `dictify.parse_file(path, ...)` — same semantics, reads from a file.
- `dictify.unparse(input_dict, pretty, indent, encoding, ...)` — converts a
  dict back to an XML string; round-trip compatible with `dictify.parse`.

#### Internal helpers (C-level, not public API)
- `_node_is_null(xml_node)` — inline null check via `type() == node_null`.
- `_attr_is_null(xml_attribute)` — inline null check via `name().empty()`
  with correct `std::string` copy to avoid `const char*` comparison issues.
- `_obj_candidate_names(str)` — generates exact + hyphen-form name candidates.
- `_obj_collect_siblings(xml_node, bytes, doc_ref)` — collects same-tag
  direct siblings using `std::string` comparison for correctness.
- `_find_first(xml_node, list, bint)` — breadth-first then recursive search.
- `_find_all(xml_node, list, bint, list, doc_ref)` — collects all matches in
  document order.
- `_node_to_obj(xml_node, ...)` — recursive dict builder for `dictify`.

### Changed
- `pygixml/__init__.py` — exports `objectify` and `dictify` modules, and
  exposes `ObjectifiedElement`, `NodeSequence`, `objectify_from_string`,
  `objectify_from_file`, `dictify_parse`, `dictify_parse_file`,
  `dictify_unparse` at the package level.

### Testing
- Added `tests/test_objectify.py` — 18 test classes, ~210 tests covering:
  entry points, dotted navigation, hyphen mapping, attribute access, type
  inference, text access, sequence handling, conflict resolution, element
  properties, iteration, equality, GC safety, edge cases, `get()`, `find()`,
  `findall()`, `__setattr__`, and `__delattr__`.
- Added `tests/test_dictify.py` — 9 test classes, ~40 tests covering:
  basic structure, attributes, mixed content, repeated siblings, `force_list`,
  CDATA, edge cases, `parse_file`, and `unparse` with roundtrip verification.
- All **277 tests** passing.

### Documentation
- Added `docs/source/objectify.rst` — full Sphinx reference for the objectify
  module including type inference table, identifier mapping rules, priority
  rules, write support, and performance notes.
- Added `docs/source/dictify.rst` — full Sphinx reference for the dictify
  module including conversion rules table, `force_list` guide, round-trip
  documentation, and comparison with objectify.
- Updated `docs/source/index.rst` — objectify and dictify added to features
  list, core classes table, and toctree.
- Updated `docs/source/api.rst` — added objectify and dictify automodule
  sections.
- Updated `README.md` — added objectify and dictify sections with full API
  tables and examples.


## [0.10.1] - 2026-04-14

### Added
- `XMLNode.remove_child()` method for removing direct child elements from the XML tree.

### Testing
- Added unit tests for `XMLNode.remove_child()`.


## [0.10.0] - 2026-04-11

### Added
- `XMLNode.children()` method for iterating direct child elements. Supports `recursive=True` for depth-first traversal of all descendants.
- `XMLNode.from_mem_id_unsafe()` for O(1) node reconstruction from a `mem_id` identifier. Includes explicit documentation and warnings about segfault risks if used on stale identifiers.
- Comprehensive `.. note::` blocks in Cython docstrings explicitly highlighting pygixml-specific features not natively available in pugixml.

### Changed
- `XMLNode.value` setter now intelligently handles element nodes: automatically creates a new text/CDATA child or replaces the existing one, enabling symmetric `get`/`set` behavior (`element.value = "text"` now works as expected).
- `XMLNode.value` getter now returns the first text child's value for element nodes, rather than always returning `None`.
- `Optimize.cmake` completely rewritten for cross-platform support. Now correctly applies GCC/Clang flags on Unix, `/O2 /GL` on MSVC, and safely disables `-march=native` in CI/Apple environments.
- Minimum Python version lowered from 3.9 to **3.6** to broaden ecosystem compatibility.
- `.pyi` stub generation via `stubgen-pyx` is now conditional: only runs on Python >= 3.9 where the package is available. Builds succeed on 3.6–3.8 without type stubs.

## [0.9.2] - 2026-04-10

### Added
- `ParseFlags` `IntFlag` enum exposing all 18 pugixml parse options (e.g., `MINIMAL`, `COMMENTS`, `CDATA`, `ESCAPES`) for type-safe parsing configuration.

### Testing
- Expanded `tests/test_xml_text.py` with assertions for element `value` getter/setter behavior.
- All **93 tests** passing across the supported Python version range.

### Performance
- Benchmarks stabilized at 50 iterations per configuration.
- 5 000 element parsing consistently **8.4×–9.2× faster** than `xml.etree.ElementTree` and **~5× faster** than `lxml`.
- Memory footprint remains at ~0.67 MB for 5 000 elements (~7× less than ElementTree).

## [0.9.1] - 2026-04-09

### Documentation
- Complete rewrite of `quickstart.rst`, `xpath.rst`, `advanced.rst`, and `installation.rst` for clearer onboarding.
- Added `xml_basics.rst` primer covering XML structure, well-formedness, XPath, and real-world applications with academic references.
- Updated `performance.rst` and `README.md` with stable 50-iteration benchmark results across 6 XML sizes.
- Added explicit clarification of **zero runtime dependencies** across all documentation and marketing materials.


## [0.9.0] - 2026-04-08

### Added
- Exposed all 18 pugixml parse flags as module-level integer constants (e.g., `PARSE_MINIMAL`, `PARSE_FULL`, `PARSE_DEFAULT`) allowing users to configure parsing behavior for speed vs. strictness.
