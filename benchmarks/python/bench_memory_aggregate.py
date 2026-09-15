"""
bench_memory_aggregate.py — combine the per-data-point result JSONs
written by many separate bench_memory_one.py invocations into the
single memory.json the report generator reads.

Kept as its own tiny script (rather than folded into
bench_memory_one.py) because it's a genuinely different kind of step:
every other script here in the memory-benchmark cluster runs a giant
XML file through something and self-reports; this one just reads a
directory of small JSON files and reshapes them. No reason to give it
memory-sensitive semantics it doesn't need.
"""
import argparse
import glob
import json
import os


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("points_dir", help="directory of *.json files written by bench_memory_one.py")
    p.add_argument("output", help="path to write the combined memory.json")
    args = p.parse_args()

    by_approach = {}
    for path in sorted(glob.glob(os.path.join(args.points_dir, "*.json"))):
        with open(path, "r", encoding="utf-8") as f:
            point = json.load(f)
        approach = point["approach"]
        by_approach.setdefault(approach, []).append(point)

    result = {}
    for approach, points in by_approach.items():
        points.sort(key=lambda p: p.get("n") or 0)
        if not points or not points[0]["available"]:
            result[approach] = {"available": False,
                                 "error": points[0].get("error") if points else "no data points"}
        else:
            result[approach] = {"available": True, "points": points}

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"bench_memory_aggregate: combined {len(by_approach)} approaches -> {args.output}")


if __name__ == "__main__":
    main()
