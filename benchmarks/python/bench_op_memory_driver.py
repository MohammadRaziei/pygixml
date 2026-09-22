"""
bench_op_memory_driver.py — orchestrate bench_op_memory_one.py across
every (corpus entry, operation, library) combination and combine the
results into throughput_memory.json.

This driver is a single CMake step (not one target per data point)
specifically BECAUSE it never touches the corpus data itself: it reads
only the manifest's metadata (genre, size, path, byte count) and hands
each file's *path* to a freshly spawned child via subprocess.run --
the same "spawning process must stay unspoiled" rule documented in
benchmarks/README.md for bench_memory_one.py, just satisfied a
different way (one lightweight orchestrator spawning children, instead
of CMake spawning each child directly). Both are fork+exec from a
process that never allocated a large XML string; that's the part that
actually matters for ru_maxrss, not which program did the spawning.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

WORKER = Path(__file__).with_name("bench_op_memory_one.py")

# Mirrors bench_throughput.py's OP_META/library pairing exactly, so
# the same operations and competitors show up in both places.
OP_LIBRARIES = {
    "parse": ["pygixml", "lxml", "elementtree"],
    "iterparse": ["pygixml", "lxml", "elementtree"],
    "dict_convert": ["pygixml", "xmltodict"],
    "dict_stream": ["pygixml", "xmltodict"],
    "to_object": ["pygixml", "lxml"],
    "xml_to_json": ["pygixml", "xmltodict", "xmljson"],
}
# These two need a uniformly repeated element to stream over -- skipped
# entirely for corpus entries without one (e.g. "config"), same as
# bench_throughput.py.
STREAMING_OPS = {"iterparse", "dict_stream"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifests", nargs="+",
                    help="one or more JSON manifests from corpus.py / real_corpus_manifest.py, merged together")
    p.add_argument("output", help="path to write throughput_memory.json")
    args = p.parse_args()

    manifest = []
    for m_path in args.manifests:
        with open(m_path, "r", encoding="utf-8") as f:
            manifest.extend(json.load(f))  # metadata only -- paths and byte counts, never file content

    result = {}
    total = sum(
        len(libraries) * sum(1 for e in manifest if not (op in STREAMING_OPS and not e.get("record_tag")))
        for op, libraries in OP_LIBRARIES.items()
    )
    done = 0

    for op, libraries in OP_LIBRARIES.items():
        op_rows = []
        for entry in manifest:
            if op in STREAMING_OPS and not entry.get("record_tag"):
                continue  # no uniformly repeated element in this file -- not applicable
            row = {"genre": entry["genre"], "size": entry["size"], "bytes": entry["bytes"], "libraries": {}}
            for lib in libraries:
                cmd = [sys.executable, str(WORKER), op, lib, entry["path"]]
                if op in STREAMING_OPS:
                    cmd += ["--tag", entry["record_tag"]]
                    if entry.get("record_depth"):
                        cmd += ["--depth", str(entry["record_depth"])]
                proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
                point = json.loads(proc.stdout)
                row["libraries"][lib] = point
                done += 1
            op_rows.append(row)
        result[op] = op_rows
        print(f"bench_op_memory_driver: {op} done ({done}/{total})", file=sys.stderr)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"bench_op_memory_driver: wrote {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
