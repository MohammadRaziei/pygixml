#!/usr/bin/env python3
"""
update_benchmark_report.py — copy the standalone benchmark report into
docs/source/_static/ so performance.rst's embedded iframe has something
to show.

IMPORTANT: this is NOT part of the regular docs build (cmake.yml's
build_docs job, which runs on every PR on shared/noisy CI runners --
exactly where you don't want a performance benchmark running), and
there is deliberately no CI workflow that runs it automatically either
-- a real benchmark run has no business happening on a shared runner
on a schedule. This is a manual, local-only step, and it's one CMake
target, not two separate commands -- this script is what that target
runs, you never invoke it directly:

      cmake -S benchmarks -B benchmarks/build
      cmake --build benchmarks/build --target pygixml_benchmark_report

  That alone runs the entire benchmark suite (throughput, memory,
  scaling, sizes, cli -- everything, as a real file-level CMake
  dependency, not just "usually run first") and copies the result into
  docs/source/_static/benchmark-report.html for you. Then commit that
  file yourself, same as any other source change.

  (pygixml_benchmark, without _report, is the same suite without the
  docs copy -- useful if you only want benchmarks/results/report.html
  and don't touch this repo's docs/ at all.)

Either way, the file this script produces is committed to git (it is
NOT gitignored) -- the regular PR/deploy docs build just uses whatever
was last committed, so it never runs a benchmark, never depends on the
runner it happens to land on, and docs builds stay fast and
reproducible. The trade-off, stated plainly: the embedded numbers are
exactly as fresh as the last time someone ran the steps above and
committed the result -- not live-per-commit. See performance.rst for
how that's disclosed to readers.
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
    elif not DEST.exists():
        # Only write the placeholder if nothing is committed yet (a
        # fresh clone where no one has run the steps above yet) --
        # never clobber an already-committed real report just because
        # this particular checkout hasn't run the benchmark locally.
        DEST.write_text(PLACEHOLDER, encoding="utf-8")
        print(f"update_benchmark_report: {SOURCE} not found and nothing committed yet, "
              f"wrote placeholder to {DEST}", file=sys.stderr)
    else:
        print(f"update_benchmark_report: {SOURCE} not found; leaving the already-committed "
              f"{DEST} as-is", file=sys.stderr)


if __name__ == "__main__":
    main()
