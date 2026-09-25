"""
bench_cli.py — pygixml's own command-line tool against its closest
real competitor at the shell: `xq` (installed by the `yq` PyPI
package), the closest thing the ecosystem has to a `jq`-for-XML.

Both sides do the same job end to end, as a shell command would run
it: read an XML file, write JSON, process exit and all -- not an
in-process function call. Every corpus entry is timed as
best_of(REPEATS) wall-clock seconds, subprocess startup included on
both sides (real usage pays that cost every invocation too).
"""
import json
import subprocess
import sys
import time

REPEATS = 5


def best_of(cmd, repeats=REPEATS):
    best = None
    err = None
    for _ in range(repeats):
        t0 = time.perf_counter()
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=120)
        except Exception as e:
            return None, f"{type(e).__name__}: {e}"
        dt = time.perf_counter() - t0
        if r.returncode != 0:
            err = r.stderr.decode(errors="replace")[:300] or f"exit {r.returncode}"
            continue
        if best is None or dt < best:
            best = dt
    if best is None:
        return None, err or "no successful run"
    return best, None


def run(manifest_paths, python_exe, xq_bin, repeats=REPEATS):
    entries = []
    for mp in manifest_paths:
        for e in json.load(open(mp)):
            entries.append(e)

    results = []
    for e in entries:
        path = e["path"]
        pyg_time, pyg_err = best_of([python_exe, "-m", "pygixml", "jsonify", path], repeats)
        xq_time, xq_err = best_of([xq_bin, ".", path], repeats)

        results.append({
            "genre": e.get("genre", "?"), "size": e.get("size", "?"), "bytes": e["bytes"],
            "pygixml_cli": {"available": pyg_time is not None, "seconds": pyg_time, "error": pyg_err},
            "xq": {"available": xq_time is not None, "seconds": xq_time, "error": xq_err},
        })
        print(f"{e.get('genre', '?'):8s} {e.get('size', '?'):7s} {e['bytes']:>10,}B  "
              f"pygixml={pyg_time}  xq={xq_time}", file=sys.stderr)

    return {
        "repeats": repeats,
        "metric": "best (min) wall-clock seconds over repeats, process startup included",
        "commands": {
            "pygixml_cli": "python -m pygixml jsonify <file>",
            "xq": "xq . <file>",
        },
        "results": results,
    }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifests", nargs="+", help="one or more corpus manifest.json paths (flat list of {genre,size,bytes,path})")
    p.add_argument("output", help="path to write results JSON")
    p.add_argument("--python", default=sys.executable, help="python executable with pygixml installed")
    p.add_argument("--xq", default="xq", help="path to the xq binary")
    p.add_argument("--repeats", type=int, default=REPEATS)
    args = p.parse_args()

    out = run(args.manifests, args.python, args.xq, args.repeats)
    json.dump(out, open(args.output, "w"), indent=2)
    print("bench_cli: wrote", args.output, file=sys.stderr)
