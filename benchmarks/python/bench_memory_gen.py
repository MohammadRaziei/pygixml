"""
bench_memory_gen.py — write the N-sweep of record-shaped XML files
used by the memory benchmark, and nothing else.

This is deliberately a separate script from bench_memory_one.py (the
actual measurement). Generating a 65MB XML string in Python inflates
*this* process's own resident memory to 200MB+ (string-building
overhead, allocator fragmentation) -- and on Linux, a process's
``ru_maxrss`` high-water mark is NOT reset by ``execve()``, so any
process later spawned (directly or via fork+exec) by an
already-inflated Python process inherits that inflated floor as its
own reported "peak," regardless of its *actual* usage. Concretely:
measuring `jsonify.stream_dump`'s memory use *from inside the same
loop that generated the corpus* silently produces numbers that track
the corpus generator's memory, not stream_dump's -- a real bug we hit
building this suite (see benchmarks/README.md).

The fix is architectural, not a flag to flip: generation and
measurement must be genuinely separate OS processes, with the
measuring process's own parent (this CMake step, or a shell) never
having touched the corpus data itself.
"""
import argparse
import json
import os

from corpus import gen_records

DEFAULT_SIZES = [5_000, 20_000, 80_000, 320_000]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("out_dir", help="directory to write N.xml files + manifest.json into")
    p.add_argument("--sizes", default=",".join(str(n) for n in DEFAULT_SIZES),
                   help="comma-separated record counts")
    args = p.parse_args()

    sizes = [int(s) for s in args.sizes.split(",") if s.strip()]
    os.makedirs(args.out_dir, exist_ok=True)

    manifest = []
    for n in sizes:
        xml = gen_records(n)
        path = os.path.join(args.out_dir, f"records_{n}.xml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(xml)
        manifest.append({"n": n, "path": path, "bytes": len(xml.encode("utf-8"))})
        # Explicitly drop the big string before the next iteration --
        # this alone doesn't fully solve the problem described above
        # (that's why generation and measurement are separate scripts
        # at all), but there's no reason to let this process's own
        # peak grow across iterations when it doesn't have to.
        del xml

    manifest_path = os.path.join(args.out_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    for entry in manifest:
        print(f"n={entry['n']:<8d} {entry['bytes']:>10,} bytes  {entry['path']}")
    print(f"manifest -> {manifest_path}")


if __name__ == "__main__":
    main()
