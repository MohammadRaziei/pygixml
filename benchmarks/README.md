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
| `pygixml_bench_throughput` | Parse + XML→JSON speed, every library, every corpus entry |
| `pygixml_bench_scaling` | Time vs. N — the O(n) vs. O(n²) story |
| `pygixml_bench_memory` | Peak RSS vs. input size, one isolated process per data point |
| `pygixml_bench_features` | The feature comparison matrix (static, hand-curated) |
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
actual conversion layers, not just JSON: raw DOM parse, dict
conversion (`dictify`, matched fairly against `xmltodict` since both
use the same `@attr`/`#text` convention), lazy-object access
(`objectify`, matched against lxml's own `objectify` submodule), and
end-to-end XML→JSON (`jsonify`) — plus memory use at scale, install
footprint, and a static feature matrix (XPath, XSLT, schema
validation, streaming, CLI tools, and so on — things a speed number
can't capture).

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
  XML) — downloaded by CMake itself
  (`cmake/FetchRealCorpus.cmake`, plain `file(DOWNLOAD)`, no Python
  involved in the fetch). Routed automatically: below
  `PYGIXML_BENCH_CORPUS_SIZE_THRESHOLD_BYTES` (default 2MB) it's cached
  in the build directory; at or above it, it's cached in a **persistent**
  `benchmarks/corpus/` folder in the source tree instead (so it isn't
  re-downloaded on every clean build) — with a `.gitignore` containing
  `*` written into that folder, so the actual downloaded files are
  never committed, only the folder structure.

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

## Requirements

- CMake ≥ 3.18
- Python 3 (used to create the venv; nothing needs to be pre-installed
  into your system Python)
- Internet access (competitors + pygixml from PyPI/GitHub, the real
  corpus, and Chart.js are all fetched at build time — nothing is
  vendored in this repository)
