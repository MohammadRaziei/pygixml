#!/usr/bin/env python3
"""
update_benchmark_report.py — copy the standalone benchmark report into
docs/source/_static/ so performance.rst's embedded iframe has something
to show, and run it BEFORE sphinx-build (CI does this as a build step;
locally, run it after `cmake --build build --target pygixml_bench_report`
in benchmarks/).

The report itself is never committed (see .gitignore) -- same reasoning
as benchmarks/corpus/: it's generated build output, not source, and it
goes stale the moment the code it measured changes. If it isn't there
yet (a fresh checkout, a contributor who hasn't run the benchmark
suite), this writes a small honest placeholder instead of leaving a
broken iframe or failing the docs build.
"""
import shutil
import sys
from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parent
REPO_ROOT = DOCS_DIR.parent
SOURCE = REPO_ROOT / "benchmarks" / "results" / "report.html"
DEST = DOCS_DIR / "source" / "_static" / "benchmark-report.html"

PLACEHOLDER = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
body{margin:0;height:100vh;display:flex;align-items:center;justify-content:center;
background:#0b0e14;color:#8b93a7;font-family:-apple-system,'Segoe UI',sans-serif;text-align:center}
div{max-width:420px;padding:2rem}
code{background:#171c28;padding:2px 6px;border-radius:5px;color:#e6e9ef}
</style></head><body><div>
<p>The benchmark report hasn't been generated yet.</p>
<p>Run <code>cmake --build build --target pygixml_bench_report</code>
in <code>benchmarks/</code>, then re-run this script.</p>
</div></body></html>
"""


def main():
    DEST.parent.mkdir(parents=True, exist_ok=True)
    if SOURCE.exists():
        shutil.copyfile(SOURCE, DEST)
        print(f"update_benchmark_report: copied {SOURCE} -> {DEST}")
    else:
        DEST.write_text(PLACEHOLDER, encoding="utf-8")
        print(f"update_benchmark_report: {SOURCE} not found, wrote placeholder to {DEST}",
              file=sys.stderr)


if __name__ == "__main__":
    main()
