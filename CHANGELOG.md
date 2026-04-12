# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
