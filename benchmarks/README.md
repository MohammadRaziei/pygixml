# pygixml benchmarks

Self-contained and independent of the rest of this repository: this
directory installs pygixml itself fresh from GitHub
(`pip install git+https://github.com/MohammadRaziei/pygixml.git`), not
from `../src`, and manages its own virtualenv. You can copy this
`benchmarks/` directory out on its own and it will still work — same
convention as
[ctoon's benchmark suite](https://github.com/MohammadRaziei/ctoon/tree/main/benchmarks),
by the same author.

## Running it

```bash
cd benchmarks
cmake -S . -B build
cmake --build build --target pygixml_benchmark
```

That's the one target you need — it pulls in every benchmark, in the
right dependency order, and finishes by writing
**`results/report.html`**: a single, standalone HTML file (Chart.js
and every raw JSON result are embedded in it) with a "download JSON"
button per dataset. Open it in a browser; nothing else is required —
no server, no network, no sibling files.

`results/` is the **only** thing meant to be committed from this whole
build — everything else (the venv, the corpus, per-run JSON) lives
under `build/` and is disposable.

### Running one piece at a time

Every operation is its own target, independently runnable
(`cmake --build build --target <name>`):

| Target | What it does |
|---|---|
| `pygixml_bench_venv` | Create the venv; install lxml/xmltodict/xmljson/pip-size/jinja2 + pygixml itself (from git) |
| `pygixml_bench_corpus` | Generate the synthetic multi-genre corpus |
| `pygixml_bench_real_corpus` | Index the real-world corpus (see below) into the same manifest shape |
| `pygixml_bench_sizes` | Compare install footprint via [pip-size](https://github.com/MohammadRaziei/pip-size) |
| `pygixml_bench_throughput` | Speed for every conversion layer (parse/dictify/objectify/jsonify), every library, every corpus entry |
| `pygixml_bench_throughput_memory` | Peak memory for the same operations/libraries/entries, one isolated process per (entry, op, library) |
| `pygixml_bench_scaling` | Time vs. N — the O(n) vs. O(n²) story |
| `pygixml_bench_memory` | Peak RSS vs. input size, one isolated process per data point |
| `pygixml_bench_system_info` | Record the machine's OS, CPU model, core count, and RAM |
| `pygixml_bench_report` | Render everything above into `results/report.html` |

`cmake --build build --target help` lists all of these plus CMake's
own built-ins.

### Options

```bash
# use a different pygixml source (e.g. a branch, or a local checkout
# via file://) instead of the default main-branch GitHub install
cmake -S . -B build -DPYGIXML_BENCH_GITHUB_URL="git+https://github.com/YOURFORK/pygixml.git@yourbranch"

# where report.html ends up
cmake -S . -B build -DPYGIXML_BENCH_RESULTS_DIR=/somewhere/else
```

## What's benchmarked, against what

pygixml vs. [lxml](https://lxml.de/), the standard library's
`xml.etree.ElementTree`, [xmltodict](https://github.com/martinblech/xmltodict),
and [xmljson](https://github.com/sanand0/xmljson) — across pygixml's
five independent layers, not just JSON:

1. **parse** (pugixml core) — raw DOM parse, vs. lxml and ElementTree.
2. **iterparse** (yxml core) — stream every repeated element without
   ever holding the whole document, vs. lxml's and ElementTree's own
   `iterparse`. Only runs on corpus entries with one uniformly
   repeated element (see `corpus.py`'s `RECORD_TAG`).
3. **jsonify** — end-to-end XML→JSON, vs. xmltodict+`json.dumps` and
   xmljson+lxml+`json.dumps`.
4. **objectify** — lazy attribute-style access, vs. lxml's own
   `objectify` submodule.
5. **dictify**, in *both* modes — DOM mode (`dictify.parse`, matched
   fairly against `xmltodict.parse` since both use the same
   `@attr`/`#text` convention) and streaming mode (`dictify.iterdict`
   vs. xmltodict's own `item_depth`/`item_callback` streaming — it
   genuinely supports both, so neither comparison is a DOM tool facing
   a streaming-only one).

Plus memory use at scale and install
footprint. The static feature matrix (XPath, XSLT, schema validation,
streaming, CLI tools, and so on — things a speed number can't capture)
lives on the [landing page](../docs/site/index.html.in) instead of
here: it's hand-curated fact, not something worth running code to
regenerate.

### Corpus

Two sources, both ending up in the same `{genre, size, path, bytes}`
manifest shape so every benchmark script treats them identically:

- **Synthetic** (`corpus.py`) — deterministic (seeded), several
  realistic genres (RSS-style feeds, product catalogs, deep config
  trees, flat record lists) at several sizes, plus a wide N-sweep used
  specifically for the scaling/memory story. Chosen over an external
  dataset because pygixml's own documented complexity caveat (see
  `docs/source/jsonify.rst` in the main repo) depends on XML *shape*,
  not just size — a corpus that can't control shape can't tell that
  story.
- **Real-world** (Bootstrap Icons SVGs, github.com/twbs/icons — SVG is
  XML) — downloaded by CMake itself at configure time
  (`cmake/FetchRealCorpus.cmake`, plain `file(DOWNLOAD)`, no Python
  involved in the fetch), always cached in a **persistent**
  `benchmarks/corpus/` folder in the source tree (so it isn't
  re-downloaded on every clean `build/` wipe) — with a `.gitignore`
  containing `*` written into that folder, so the actual downloaded
  files are never committed, only the folder structure.

### Timing

Best (minimum) wall-clock time over 7 repeats per (library, corpus
entry, operation) cell — standard practice for micro-benchmarks, since
it's the closest a single run gets to "no other process happened to
interrupt this one." Every one of pygixml's conversion layers gets its
own operation, measured against its real direct competitor, rather
than being collapsed into a single "XML to JSON" number: raw parse,
`dictify` (vs. `xmltodict`), `objectify` (vs. `lxml.objectify`), and
`jsonify` (vs. the field). See `bench_throughput.py`'s module
docstring for exactly why each pairing is fair.

### The memory benchmark's one real gotcha

`bench_memory_gen.py`, `bench_memory_one.py`, and
`bench_memory_aggregate.py` are three separate scripts, not one, for a
concrete reason: generating a large XML string inflates *that*
process's own resident memory, and on Linux, `ru_maxrss` is **not**
reset by `execve()` — so a measurement subprocess spawned (directly or
via fork) from an already-inflated Python driver inherits that
inflation as its own reported "peak," regardless of what it actually
uses. We hit this for real building this suite: it silently made
`stream_dump` look like it used hundreds of MB instead of ~17MB flat.
The fix is architectural — generation and measurement must be
genuinely separate OS processes, with the process spawning the
*measurement* never having touched the corpus data itself. That's why
CMake spawns one fresh process per (size, approach) data point instead
of a Python loop doing it.

## Tuning

`PYGIXML_BENCH_REPEATS` (CMake cache variable, default `7`) — timed
repeats per (library, corpus entry, operation) cell in
`bench_throughput.py`; the best (minimum) of these is kept. Raise it on
a noisy machine, lower it for a faster iteration loop:

```bash
cmake -S benchmarks -B benchmarks/build -DPYGIXML_BENCH_REPEATS=15
```

## Requirements

- CMake ≥ 3.18
- Python 3 (used to create the venv; nothing needs to be pre-installed
  into your system Python)
- Internet access (competitors + pygixml from PyPI/GitHub, the real
  corpus, and Chart.js are all fetched at build time — nothing is
  vendored in this repository)

## On fairness

pygixml's memory and scaling advantage over the DOM-building
competitors isn't a fixed multiplier — it's a different complexity
class. `jsonify.stream_dump` never builds a tree, so its memory use is
O(1) in input size; every DOM-based competitor is O(n). That means any
single "pygixml uses N× less memory" figure is only true at the one
input size it was computed from, and understates the gap at every
larger size and overstates it at every smaller one. The report never
computes a ratio between an O(1) approach and an O(n) one — the O(1)
side just gets its own observed range stated plainly (e.g. "stayed
within 15.7–15.9MB across every size tested"), and the actual curves
(log-log, both axes) show the growth rate honestly instead of one
cherry-pickable number.

Where every approach genuinely *is* the same complexity class (every
library in a throughput operation does one single-pass O(n) walk; the
DOM-based approaches in the memory comparison all hold a full tree) —
there a ratio is fair, and the report computes one, but not as a ratio
of medians or of averages. It picks whichever approach wins the most
comparisons as the **reference**, then for every other approach
computes **E[target/ref]**: the ratio on *each* corpus entry
individually, averaged across entries — ratio-then-average, not
average-then-ratio. Concretely, for time:

```
E[time_x / time_ref] = mean( time_x_i / time_ref_i  for each corpus entry i )
```

not `median(time_x) / median(time_ref)` and not `mean(time_x) /
mean(time_ref)`. The difference matters because corpus entries span
several orders of magnitude in size (a 20-byte config value next to a
4MB catalog) — averaging the raw numbers first lets the largest entry
dominate the result; ratio-then-average weighs every entry's *relative*
performance equally, regardless of its absolute size. See
`_e_ratio()` in `report/generate_report.py`.

## What the report doesn't say (on purpose)

`results/report.html` is the results, not the write-up: it doesn't
explain how the corpus was built, why timing uses best-of-N, or what
went wrong along the way — that's this file. The one exception is the
machine it ran on (CPU model, core count, RAM, OS, Python version),
which appears in the report's footer via `system_info.py`, since
that's a fact about the specific numbers in that specific report, not
about the methodology in general.
