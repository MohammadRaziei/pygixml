# Handoff: pygixml HTML + tree diff work

> خلاصه (فارسی): روی پروژه‌ی pygixml چهار قابلیت اضافه شد: تبدیل HTML↔XML، دیف درختی (`diff`)، embedding ساختاری (`signature`/`similarity`) و `patch`. همه در C++ داخل فایل‌های `.pxi` نوشته شده، هنوز commit نشده و فقط داخل `pygixml-html.zip` است. آخرین اجرای کامل تست‌ها: ۷۳۸ پاس، ۱ skip.

Everything below was produced in one long working session. Where something was **not**
verified it says so. Nothing here has been committed to git: the deliverable is
`pygixml-html.zip` (a project tree with the submodule contents included).

## 1. The rules the user set (follow these)

- Reply in **Persian**; code, docs and comments are English.
- Whenever output is requested: **zip the project and present it**, no confirmation first.
- **Keep submodule contents in the zip** (pugixml). Leave out only the submodule's own `.git` file
  (it points into the parent's `.git/modules`, which is not in the zip).
- **No new git submodules** besides pugixml. If C/C++ is needed, write it **inside the Cython files**
  (`.pxi` / `.pyx`) as verbatim blocks, not as separate headers or new dependencies.
  (A `diff-match-patch` submodule was added and then removed on this instruction.)
- **"ponytail" style** (github.com/DietrichGebert/ponytail): simplest working solution, reuse what exists,
  no unrequested boilerplate, mark deliberate simplifications with a `ponytail:` comment naming the
  upgrade path. Still do full validation, error handling and security.
- Be honest about what was and wasn't verified; the user pushed back more than once on unverified claims.

## 2. What exists now

The repo is `github.com/MohammadRaziei/pygixml` (URL was a guess that worked), version 0.13.0,
Python bindings for pugixml written in Cython, built with scikit-build-core + CMake.

### Public API added (all exported from `pygixml`)

| Area | API |
|---|---|
| HTML to XML | `html_to_xml(html, root="root") -> str`, `parse_html(html, root="root", options=None) -> XMLDocument`, `PygiXMLHTMLError` |
| XML to HTML | `xml_to_html(node_or_doc, pretty, indent, doctype, unwrap) -> str`, `XMLNode.to_html()`, `XMLDocument.to_html()` |
| Tree diff | `diff(a, b, **options) -> list[action]`, `patch(doc, actions, **norm_options)`, `is_equal(a, b, **norm_options)` |
| Actions | `Insert`, `InsertText`, `Delete`, `Move`, `UpdateText`, `SetAttrib`, `DeleteAttrib` (namedtuples) |
| Embedding | `signature(node, method="pqgram"\|"paths", p, q, content)`, `similarity(a, b, ...)` |
| Errors | `PygiXMLDiffError` (diff, patch, is_equal, signature, similarity), `PygiXMLHTMLError` (HTML) |
| CLI | `pygixml convert x.html --to json|html|...`; html and xml can be written as html (`-p` pretty). `FormatDocument.from_html/to_html` |

### Files (new = N, modified = M)

```
src/html.pxi            N  HTML<->XML. C++ in verbatim blocks (generated entity table + tokenizer/tree fixer/serializer), Cython glue
src/embedding.pxi       N  C++: flat normalised tree with subtree hashes + pq-gram/paths; shared helpers; PygiXMLDiffError
src/diff.pxi            N  C++: matcher, Chawathe edit script, word text-diff, patch; Cython glue; action namedtuples
src/pygixml_cy.pyx      M  include html.pxi, embedding.pxi, diff.pxi (after jsonify.pxi); to_html on XMLNode/XMLDocument
src/pygixml/__init__.py M  exports
src/pygixml/formats.py  M  INPUT_FORMATS/OUTPUT_FORMATS, from_html/to_html
src/pygixml/convertcmd.py M html in/out; html/xml -> html goes straight from the tree (not via dict)
scripts/gen_html_entities.py N regenerates the entity table block inside src/html.pxi
tests/test_html.py      N  ~80 tests incl. CLI
tests/test_diff.py      N  diff/patch/embedding tests, independent reference patcher, fuzz
docs/source/modules/html.rst, diff.rst  N; docs/source/index.rst M; CHANGELOG.md M (under [Unreleased])
```

`src/CMakeLists.txt` and `.gitmodules` are **unchanged** versus the user's repo.

## 3. Build and test (what worked here)

```bash
git submodule update --init                       # pugixml; the clone had it empty
pip install scikit-build-core cython cmake ninja pytest stubgen-pyx pathspec
pip install --no-build-isolation .                # ~1-2 min; add --break-system-packages on this image
# dev loop without reinstalling pure-Python edits: copy the built .so next to the sources
cp <site-packages>/pygixml/pygixml_cy*.so src/pygixml/ && rm -f src/pygixml/pygixml_cy.pyi
PYTHONPATH=src python3 -m pytest tests -q -p no:cacheprovider
```

- Last full run: **738 passed, 1 skipped**, also from a clean unzip + fresh build.
- The `.so` and the generated `pygixml_cy.pyi` are untracked build artifacts: do not commit or zip them.
- Any change to a `.pxi`/`.pyx` needs a rebuild; Python-only changes do not.

## 4. Design, in brief

### HTML <-> XML (`html.pxi`)
- One C++ call per function. Tokenizer is HTML5-style (no `html.parser`), tree fixer handles void tags,
  implied end tags (`<p>`, `<li>`, `<td>`, `<option>`...), stray end tags, root wrapping for fragments.
  It is **not** the HTML5 tree-construction algorithm: no implied html/head/body, no table repair,
  names are lower-cased (SVG `viewBox` becomes `viewbox`).
- Names XML rejects are mapped with the **SQL/XML rules** (ISO/IEC 9075-14 9.1, same as PostgreSQL
  `map_sql_identifier_to_xml_name` and .NET `XmlConvert.EncodeName`): `o:p` -> `o_x003A_p`, `@click` ->
  `_x0040_click`; `_x` -> `_x005F_x` makes it one-to-one; "fully escaped" (default) also escapes every `:` and
  the first letter of a name starting with `xml` (`xmlns` -> `_x0078_mlns`). Replaced an earlier readable scheme
  (`_colon_`, `_at_`, ...) that was ambiguous (`x_colon:` and `__at_` did not round-trip). C++ `enc_name`/`dec_name`
  in `html.pxi`; Python `encode_name` / `decode_name` / `XMLNameCodec` are thin wrappers (tests: `tests/test_names.py`).
  The decoder also takes lower-case hex and 5/8-digit forms (PostgreSQL, .NET). Non-BMP escapes use 6 digits; I did not
  check that against the standard text.
- `case` on `html_to_xml`/`parse_html` (`"lower"` default, `"keep"`, `"escape"`): the tokenizer passes raw names to
  `Builder`; logic (void tags, implied end tags, raw text, end-tag matching) always uses the lower-cased name,
  `show_name()` decides what is written, and `Builder::shown` keeps the written name so an end tag repeats the start
  tag's spelling. `"escape"` is the SQL/XML mapping with `A-Z` escaped (`encode_name(..., escape_case=True)`), so names
  stay lower-case and `decode_name` restores them. Duplicate attributes: by written name (so `@Click`/`@click` are two in
  keep/escape, one in lower). `FormatDocument.from_html(text, case=...)` and `pygixml convert --case` (html input only, else an argparse error) take it too. Tests: `tests/test_html_case.py`
  (a fuzz shows the three modes give the same document up to name case).
- Tests use expat only for characters both XML 1.0 editions allow: expat has the 4th-edition name tables and rejects
  U+2040, U+FFFD and chars above U+FFFF that the current spec, libxml2 and pugixml accept.
- Spec behaviours chosen on purpose: all 2231 named entities incl. legacy no-`;` ones (and `?a=1&copy=2` stays
  literal in attributes), `<title>`/`<textarea>` are RCDATA, `\r\n`->`\n`, newline after `<pre>` dropped
  and re-added on output, a tag cut off by EOF is dropped, newlines in attribute values survive (char refs).
- `parse_html` defaults to `ParseFlags.DEFAULT | WS_PCDATA | COMMENTS` (inline whitespace and comments are content).
- Output serializer: `<br>` for void tags, `<div></div>` never `<div/>`, raw script/style, `pretty` never
  re-indents inline content/`<pre>`; both directions are iterative (20,000 nested divs is fine).

### Diff (`diff.pxi`, algorithm choice follows Cobena et al.'s comparative study)
1. Build a flat normalised tree for each side: ignore blank text (+ trim/collapse whitespace), comments,
   chosen attributes (`ignore_attrs`, trailing `*` = prefix), `class` as a set, attribute order irrelevant.
   Each node has a 64-bit subtree hash.
2. **Matching**, top-down per matched parent pair: (a) `keys` (default `("id",)`), (b) identical subtree hash via LCS
   over hash sequences (DP table up to a size cap, greedy monotone above it), (c) the leftovers between anchors by
   similarity: pq-gram Dice (content included) for elements, char-bigram Dice for text; a node that is the only
   one of its tag in the gap is treated as an update. Optional cross-parent **moves**: identical hash first,
   then similarity >= `move_threshold`.
3. **Edit script**: Chawathe's algorithm on a mutable working copy of the old tree (BFS over the new tree,
   insert/update/move, LIS child alignment, then deletes). A wholly new subtree is **one** `Insert`.
4. The script is **verified in C++ before returning** (working tree hash == new tree hash; mismatch raises
   `PygiXMLDiffError`, which would be a bug).
- Action semantics: paths look like `/ul[1]/li[2]/text()[1]` (index counts same-tag siblings; `text()`, `comment()`),
  refer to the tree **as it is when that action runs**, in the **normalised view**. `Move(path, parent, position)`:
  detach, then `parent` is read with the node detached, insert at `position` among visible children.
  `UpdateText.diff` is a word-level diff (tokens: words, whitespace runs, punctuation, single CJK chars) when `text_diff=True`.
- `patch` applies actions to a real document through the same view; every action validates what it expects
  (path exists, old text, old attribute value) and raises if the document is not the one the script was made for.
  Works on `XMLDocument`, not on a single element. Not atomic (may leave a partly patched document).

### Embedding (`embedding.pxi`)
pq-grams (Augsten/Bohlen/Gamper, TODS 2010) and bag-of-paths; structure only unless `content=True`; Dice similarity.
Used inside diff for similarity, and public as `signature`/`similarity`.

## 5. Verification that was done (reproducible)

- Independent reference patcher in `tests/test_diff.py` (documented path/position semantics only) reproduces the target
  on ~15,000 random tree pairs; the library's own `patch` does the same on live documents.
- C++ core fuzzed under **ASan + UBSan** (16,000 pairs x 4 option sets, diff then patch on live pugixml documents): 0 reports,
  0 internal-verification failures. How: extract the `r"""..."""` blocks from the three `.pxi` files in order into one
  `.hpp` (`re.findall(r'r"""\n(.*?)\n    """', text, re.S)`), compile a small harness with
  `-fsanitize=address,undefined -DPUGIXML_HEADER_ONLY -Isrc/third_party/pugixml/src`.
- HTML fuzz: 40,000 random inputs gave 0 not-well-formed outputs (checked with `ElementTree`); plain and pretty round trips stable;
  the real 487 KB GitHub page matched the earlier pure-Python implementation byte for byte before it was replaced.
- Invariant tested: `diff(a, b) == []` exactly when `is_equal(a, b)`.

### Benchmarks (one Linux machine, single thread, indicative only)
- `html_to_xml` 487 KB page: 48.6 ms (old pure Python) -> 5.1 ms (C++). `xml_to_html`: 13.8 -> 2.5 ms.
- diff, catalog of 1,600 items (263 KB), 2% edited: **15 ms, 32 actions** vs xmldiff 3.0 at 5.8 s / 916 ops (2.2 s / 498 with `uniqueattrs`).
- diff, real 487 KB page with 2 subtrees removed + 3 attributes added: **67 ms, 5 actions** vs xmldiff default 13.6 s / 816 ops
  (xmldiff not tuned; granularity differs, but 816 vs 5 is more than granularity).
- 100,000 flat items (16 MB), 2% edited: about 2.2 s (a single recorded run).
- An earlier "228 actions on a few edits" number was wrong: a regex had removed 55 KB of HTML. Always use controlled DOM edits for such tests.

## 6. Pitfalls already hit (save yourself the time)

- **Cython verbatim blocks** are processed like normal strings: use `cdef extern from *: r""" ... """`
  (raw), otherwise `\n`, `\303` etc. are mangled. The C++ must not contain `"""`. Declarations go after the block, indented.
- `XMLDocument._doc` is a **pointer**: pass `d._doc[0]` to a `xml_document&` parameter.
- `cimport string` before using it in declarations; iterate vectors of structs via a **non-const** reference in Cython.
- C++14 evaluation order: `auto& ch = t.children[p]; ch.push_back(t.add(...))` dangles (add() reallocates). This bug hid in
  `tree.hpp` and only showed as wrong output; ASan found the cause. Never hold a reference across `add()`.
- `'\0'` as an "end of input" sentinel truncates documents at a real NUL byte: check indices instead.
- pugixml needs `parse_fragment` to load a lone comment/text fragment (used by `patch` for `Insert`).
- A node being moved is "hidden" while its new parent's path is resolved, so a move into itself fails with "path not found".
- Names with `:` break namespace-aware parsers (ElementTree/lxml): hence the name mapping.

## 7. Known limitations and things NOT done

- **Not compiled or tested on MSVC or clang**, only g++ on Linux. First CI run (PR #50, cibuildwheel) failed on musllinux cp310 with a
  segfault in `test_xml_to_html_rejects_bad_nodes`: the test did `parse_string("<x/>").root.child(...)`, and an `XMLNode` does not keep its
  document alive, so the temporary document was freed first (use-after-free; glibc and musl cp38/cp39 got away with it). Fixed in the test
  (the document is held in a variable). Reproduce this class of bug locally with `MALLOC_PERTURB_=165 pytest tests`; the whole suite passes that way.
  The other CI jobs/platforms (macOS, Windows/MSVC, the remaining wheels) were not seen.
- **Sphinx docs**: built once (sphinx + furo, `sphinx-build -b html docs/source out`): OK, the API entries render. The only warnings
  seen are `duplicate object description` for names listed both in `html.rst`/`diff.rst` and on the API page (`diff`, `html_to_xml`,
  `PygiXMLHTMLError`, `encode_name`, ...); not fixed (`:no-index:` on one side would).
- **Nothing is committed.** Version not bumped (changes sit under `[Unreleased]` in CHANGELOG).
- `html.pxi` is ~112 KB because the full 2231-entity table is inlined. The user was offered a 252-entity HTML4-only
  alternative (~4 KB, loses `&nbsp`-style legacy behaviour and rare names) and did not answer.
- Diff limits (marked `ponytail:` in `src/diff.pxi`): LCS table + greedy fallback (Myers/Wu O(ND) is the upgrade);
  no element **rename** (different tag = delete + insert); a subtree both moved to another parent and edited is found only
  above `move_threshold`; text diff is word-level, not character-level; output is a good script, not provably minimal,
  and its exact form may change between versions.
- `patch`: document only; not atomic. Before applying, it merges every run of adjacent text/CDATA nodes (also across ignored comments,
  `<?pi?>`, doctype) into the first node, because the normalised view that diff() paths refer to treats such a run as one text node
  (an earlier version did not, so `<p>x<!--c-->y</p>` -> `<p>x<!--c-->z</p>` made diff() output a script patch() refused). Only those runs
  are touched: the ignored comment stays, but now sits after the merged text. Tests: `test_patch_merges_*` and
  `test_fuzz_patch_text_split_by_invisible_nodes` in `tests/test_diff.py`; they fail (10 tests) without the merge.
- Actions have **no textual serialization**. They are namedtuples and round-trip through JSON by hand
  (`[type(x).__name__, x._asdict()]` and `getattr(pygixml, name)(**fields)`), but there is no unified/git-style format,
  no `actions_to_json`/`from_json`. The user asked what actions are and whether it is like `git diff` (it is tree-based, not line-based);
  I offered a readable text rendering and JSON helpers and have not built them.
- HTML paths for fragments start with `/root[1]` because `parse_html` wraps multi-node input in `<root>`.
- `benchmarks/` in the repo has nothing for HTML or diff; the numbers above are from ad-hoc scripts.
- No `strict=True` mode for HTML (report stray end tags / unclosed tags with line numbers); it was offered, not built.

## 8. Suggested next steps (in order)

1. Run the build + full tests on Windows (MSVC) and macOS (clang); fix any C++ portability issues (most likely spots:
   `std::to_string`/`snprintf` includes, `uint16_t` table math, signed/unsigned comparisons).
2. Fix the duplicate-object Sphinx warnings (README section on HTML/diff/patch is done).
3. Commit in sensible pieces (HTML, embedding+diff, patch, CLI) and decide the version bump.
4. Decide with the user: `actions_to_json`/`from_json` and a readable text format; the entity-table size question.
5. Optional: Myers/Wu for huge sibling lists, `strict` HTML mode, add HTML/diff cases to `benchmarks/`.

## 9. How the user steered the work

They reviewed ideas critically and redirected twice: "an algorithm that diffs two HTMLs can diff XML too"
(so HTML needs no special diff, only a normalisation layer), and "no extra submodules, C code goes inside the Cython files".
They also asked to minimise Python/C++ boundary crossings (hence one C++ call per public function) and
to have the diff use the embedding for similarity.

## Text split by child elements (dictify / jsonify)

- By design all of these keep only the **first text run** of an element as `#text`: `dictify.parse` (via `child_value()`),
  the in-memory `jsonify` serializer, and both streaming writers in `jsonify.pxi` (`text_flushed`, so a stream can emit
  `#text` at once and keep constant memory). `<p>Hi<br/>x</p>` -> `'Hi'`; xmltodict gives `'Hix'`. Tests pin this and check
  `dictify.parse == json.loads(jsonify.dumps_str(...))` on mixed content.
- `dictify.parse(..., cdata_separator=None)` / `parse_file`: a str joins all text runs (xmltodict's option; text+CDATA next to
  each other are one run, so `a<![CDATA[b]]>c` is `'abc'` for any separator). Default unchanged (same speed: 7.5 MB, ~220 ms).
  `FormatDocument.from_html` sets `""` (so `pygixml convert page.html --to json` keeps tail text). `jsonify` and `iterdict`
  do not have the option; with it on, dictify and jsonify differ on mixed content by design.
- Not done: whitespace. dictify keeps text as is (`' hi '`), xmltodict strips by default (`'hi'`); the comment in
  `_node_to_obj` says "xmltodict does not strip", which is only true with `strip_whitespace=False`.
- html_to_xml speed is about 75 MB/s on a 3 MB generated page in all three `case` modes (no measurement of the code before `case`).
