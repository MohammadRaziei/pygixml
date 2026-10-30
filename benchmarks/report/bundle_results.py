"""
bundle_results.py: merge the per-benchmark JSON files (throughput.json,
scaling.json, memory.json, ...) into the single benchmarks/results/benchmarks.json.

That JSON is the only artifact of the benchmark suite meant to be
committed. It holds raw numbers only -- the HTML page is rendered from it
by the documentation build (`cmake --build build --target sphinx_docs`,
see docs/site/benchmarks/render_benchmarks.py).
"""
import json
import os
import sys

NAMES = ("throughput", "throughput_memory", "scaling", "memory", "sizes", "cli", "system_info")


def main(results_dir, output):
    bundle = {}
    for name in NAMES:
        path = os.path.join(results_dir, name + ".json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                bundle[name] = json.load(f)
        else:
            bundle[name] = None
    os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"bundle_results: wrote {output} ({os.path.getsize(output) / 1024:.0f}KB)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: bundle_results.py <results_dir> <benchmarks.json>")
    main(sys.argv[1], sys.argv[2])
