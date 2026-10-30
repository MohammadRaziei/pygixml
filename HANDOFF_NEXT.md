# Handoff, session 2 (pygixml HTML / diff branch, PR #50)

Read this first; `Handoff.md` (older) still has the build layout and the HTML/diff design notes.

## State
- Repo MohammadRaziei/pygixml, PR #50 "feat(pygixml): add HTML<->XML conversion, tree diff, structural embedding". This session's changes exist only in the zip: commit and push them.
- CI (cibuildwheel) failed once: segfault in `test_xml_to_html_rejects_bad_nodes` on musllinux cp310 (cause and fix below). CI was not re-run. Only the ubuntu job log was ever seen: macOS, Windows/MSVC, clang never.
- Final local state: **864 passed, 1 skipped** (glibc, g++, Python 3.12), also with `MALLOC_PERTURB_=165`. ASan/UBSan was NOT re-run on any of the new C++. Sphinx builds (sphinx + furo); only "duplicate object description" warnings.

## Build / test commands that worked
- `pip install --break-system-packages --no-build-isolation .` (needs scikit-build-core cython cmake ninja pytest stubgen-pyx pathspec; xmltodict is optional, tests use `importorskip`).
- Run tests from a COPY outside the source tree so the installed build is imported: `cp -r tests /tmp/t/ && cd /tmp/t && python -m pytest tests -q -p no:cacheprovider`. Poison check: prefix `MALLOC_PERTURB_=165`.
- Docs: `pip install sphinx furo; sphinx-build -b html -q docs/source out`.
- Perf A/B: unzip the original upload, `pip install --target /tmp/origpkg .`, run the same script with `PYTHONPATH=/tmp/origpkg`.

## Done this session
1. **patch bug** (found with an independent canonicalizer on thousands of random pairs): `diff()` produced scripts `patch()` refused when text was split by a comment/CDATA/PI. Fix: `merge_text_runs` in `diff.pxi`, called first in `patch`. Tests `test_patch_merges_*` + fuzz in `tests/test_diff.py`.
2. **CI segfault**: the test did `parse_string("<x/>").root.child(..)`; `XMLNode` does not keep its document alive, so the temporary doc was freed first (use-after-free). Fixed in the test only. Same trap bit my own tests twice (`dumps_node(parse_string(x).root)`).
3. **Name mapping**: replaced the old readable `_colon_`/`_at_` scheme (it was ambiguous) by SQL/XML ISO/IEC 9075-14 (`_xHHHH_`, like PostgreSQL / .NET `XmlConvert.EncodeName`). `enc_name`/`dec_name` C++ in `html.pxi`. `_x` becomes `_x005F_x` (one-to-one); `fully_escaped` (default) also escapes every `:` and the first letter of a name starting with "xml" (so `xmlns` -> `_x0078_mlns`); 6 hex digits above U+FFFF (NOT checked against the standard text); the decoder accepts 4..8 hex digits and lower-case. API: `encode_name(name, fully_escaped=True, escape_case=False)`, `decode_name`, `XMLNameCodec`. Tests: `tests/test_names.py`.
4. **case**: `case="lower"|"keep"|"escape"` on `html_to_xml` / `parse_html`, `escape_case` on `encode_name`/`XMLNameCodec`, `FormatDocument.from_html(case=)`, `pygixml convert --case` (html input only). The tokenizer passes raw names; all logic (void tags, implied end tags, raw text, end-tag matching) uses the lower-cased name; `Builder::shown` keeps the written names so an end tag repeats its start tag's spelling. Default stays "lower". Tests: `tests/test_html_case.py` (fuzz: three modes give the same document up to name case).
5. **Docs**: README section "HTML, diff and patch", feature bullets; `html.rst` (names, case), `diff.rst`, `dictify.rst`, `jsonify.rst` (new `text-runs` section), `core/stream-parser.rst`, CHANGELOG (partly stale, see TODO 1).
6. **Text runs across all XML->dict/JSON engines** (largest change; it changes RELEASED behaviour for mixed content).
   - Finding: against an ElementTree reference on random mixed-content docs the engines disagreed even with default options (DOM readers wrong in 28 %, `stream_dump` in 7 %). Causes: DOM used pugixml `child_value()` = first text NODE (`a<![CDATA[b]]>c` -> `'a'`); the streamers took the first run but a blank first run (indentation) used up the slot, so text after the first child was dropped; `StreamElement` (iterdict/iterjsonl) ignored tail text and a PI flush overwrote text (`x<?p d?>y` -> `'y'`).
   - Unified rule, now in every engine: a **run** = text/CDATA next to each other (comments and PIs do not split it); only a child element ends it; blank runs are ignored; `#text` = first non-blank run, or with `cdata_separator=<str>` all runs joined by it (xmltodict's meaning).
   - Changed: `dictify._node_to_obj` (one pass; `cdata_separator`, and `strip_whitespace` for `dictify.parse`/`parse_file` only, default False); jsonify DOM C++ `element_text()` and `node_to_json(sep_on, tsep)`; both streaming C++ engines (`flush_text_field`, `PJLevel::joined`, with the separator the text is written when the level closes); `StreamElement._text_value`, leaf fast path, `_flush_text` appends; `cdata_separator` on every `dumps*`, `stream_dump`, `stream_jsonl`, `iterjsonl`, `iterdict`, `to_dict`, `to_json`.
   - `FormatDocument.from_html` sets `cdata_separator=""` and `strip_whitespace=True`, so `pygixml convert page.html --to json` keeps tail text and trims it.
   - Verified: `tests/test_text_runs.py` (reference = ElementTree; whole-document engines and record engines, 4 separator options) plus 25,920 extra randomized comparisons: 0 mismatches. Perf vs the original upload: `dictify.parse`, `dumps_str`, `stream_dump`, `stream_jsonl` within noise; `iterjsonl` about +4 %, `iterdict` about +3.5 % (run-to-run noise about 5 %).

## Known limitations (found, not fixed)
- DOM readers never see whitespace-only PLAIN text (pugixml drops it at parse time); inside a run next to CDATA/comment the streamers keep a space the DOM loses. The test generator avoids that placement.
- What is "blank" differs beyond ASCII (pre-existing, released): `dictify`/`iterdict` use `str.isspace()` (text of only `&#160;` -> null); the C++ JSON writers only space/tab/CR/LF (-> `"\u00a0"`). Matters for HTML `&nbsp;`.
- With `cdata_separator` the streaming writers hold an element's text until it closes.
- `strip_whitespace` exists only in `dictify.parse`/`parse_file`. `objectify`, `iterparse`, `PullParser` text semantics were NOT checked (objectify uses `child_value()` in places).
- Default lower-casing means `@Click` and `@click` are one attribute unless `case="keep"/"escape"`.
- `xmlns` / `xml:lang` become `_x0078_mlns` etc. (standard: names starting with "xml" are reserved; it also stops lxml seeing a real namespace declaration).
- Python's expat has the XML 1.0 4th-edition name tables (rejects U+2040, U+FFFD, > U+FFFF); libxml2 and pugixml accept them. Tests only use expat for characters both editions allow.
- `XMLNode` does not keep its document alive: `parse_string(x).root.child(..)` is a use-after-free (documented only in a code comment in jsonify).
- The comment in `dictify._node_to_obj` "xmltodict does not strip" is wrong (xmltodict strips by default).

## TODO, in priority order
1. ~~**CHANGELOG [Unreleased] is stale**~~ DONE in session 3 (rewritten, Changed/Fixed added). Was: for `cdata_separator`: it still says the default keeps "the first text run as before" and agrees with jsonify. Rewrite: run rule, option on all engines, `strip_whitespace` (dictify only), and the behaviour changes of released modules (text next to CDATA/comment/PI, blank-first-run in streamers, tail-only text in iterdict, PI overwrite bug).
2. Decide whether the mixed-content behaviour change in released `dictify`/`jsonify` is acceptable (else make runs opt-in); decide the NBSP / non-ASCII blank rule.
3. Docstrings for the new parameters are missing in `jsonify.pxi` (`dumps_str/file/obj/node`, `stream_dump`, `stream_jsonl`, `iterjsonl`), `stream.pxi` (`to_dict`, `to_json`), `dictify.iterdict`. The .rst pages are done.
4. Re-run CI on every platform; run ASan/UBSan on the new C++ (`html.pxi`, `diff.pxi`, `jsonify.pxi`); watch MSVC/clang (lambdas, `std::snprintf`, shadowed names).
5. Make `XMLNode` keep its document alive (or add a docstring/README warning).
6. No dedicated test pins that `from_html` strips whitespace by default (only the `case`/tail-text tests touch it).
7. diff/patch backlog: atomic `patch` (work on a copy / rollback); actions to/from JSON and a `pygixml diff a.html b.html` command; tag-rename detection; benchmarks for html/diff in `benchmarks/`; LCS is O(n*m) with a greedy fallback (Myers would be better); the 112 KB entity table (shrink or keep); fragment paths start with `/root[1]`; Sphinx duplicate-object warnings (`:no-index:` on one side); verify the 6-digit non-BMP escape against the standard.

## Gotchas
- `html.pxi`: `bool` is shadowed by the C++ type in Cython; use `True if x else False`. Cython `cdef` functions cannot take keyword arguments that skip optional ones (pass `doc_ref` positionally in `_do_jsonify`).
- `jsonify.pxi`: the first `cdef extern from *` block is a NON-raw string (write no backslashes in new C++ there); the second is `r"""`. In `node_to_json` a local lambda `sep` already exists (the text-separator parameter is `tsep`). `_check_sep` is defined in `dictify.pxi` and used by jsonify and stream.
- Tests that build random XML must keep whitespace-only plain text between two elements (see the limitation above).
- User preferences: zip the project and send it; keep the pugixml submodule contents in the zip; no other submodules; C/C++ inside `.pxi/.pyx` `cdef extern from *` blocks; "ponytail" style (simplest thing, short explanations, `ponytail:` comments for deliberate simplifications). The user writes Persian; answer in Persian.

## Changed files vs the original upload
src: `html.pxi diff.pxi dictify.pxi jsonify.pxi stream.pxi`, `pygixml/__init__.py convertcmd.py formats.py`. tests: `test_dictify.py test_diff.py test_html.py` changed, `test_names.py test_html_case.py test_text_runs.py` new. docs: `dictify.rst diff.rst html.rst jsonify.rst core/stream-parser.rst`. Also `README.md CHANGELOG.md Handoff.md`.


## Session 3 (after 0.14.0 was published)

- DONE: XMLNode/XMLAttribute/XPathNode/XPathNodeSet keep their XMLDocument (`_owner`); `node.to_html()` follows the document's `_from_html`. Tests: 867 passed.
- Not verified: the new lifetime test was not run against the old code (it may pass by luck without the fix); ASan/UBSan still not run; CI on macOS/MSVC/clang for these changes not seen.
- Still open: reset()/load_string() on a document invalidates existing nodes (pugixml frees them); NBSP whitespace rule differs between dictify and the JSON writers; objectify/iterparse/PullParser not checked against the run rule.
