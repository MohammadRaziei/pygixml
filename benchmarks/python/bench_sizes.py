"""
bench_sizes.py — real install footprint (download size, including
dependencies) for pygixml vs. the competitors this suite benchmarks,
using pip-size's own Python API directly
(github.com/MohammadRaziei/pip-size) -- no subprocess, no CLI
argument parsing, no stdout capture. pip-size itself has no pip/network
"install" step either: it resolves the real wheel for the current
platform/Python straight from PyPI's JSON API and sums sizes without
downloading or installing anything -- this script just talks to its
`DependencyResolver` / `PackageInfo` objects in-process instead of
shelling out to the `pip-size` console script that wraps them.

ElementTree needs no entry: it's in the Python standard library, 0
extra bytes, on every Python install already -- which is itself a
fair, reportable data point (the "free" option), not something
pip-size can meaningfully quantify.
"""
import argparse
import asyncio
import json
import sys

# name -> (pip spec to resolve, one-line capability summary shown next to it
# in the report). Anything with a CLI entry point relevant to the later CLI
# section is noted here too, so the size section and the CLI section use
# the same wording for the same tool.
PACKAGES = {
    "pygixml":   ("pygixml",   "dom, streaming iterparse, objectify, dictify, jsonify, cli"),
    "lxml":      ("lxml",      "dom, streaming iterparse, objectify"),
    "xmltodict": ("xmltodict", "dom → dict (+ streaming callback mode)"),
    "xmljson":   ("xmljson",   "lxml/ElementTree tree → dict adapter"),
    "yq":        ("yq",        "cli — jq-style query/convert (installs the `xq` XML binary used below)"),
    "untangle":  ("untangle",  "dom → lazy attribute-style object (read-only)"),
}


async def _resolve(spec):
    from packaging.requirements import Requirement
    from pip_size import DependencyResolver, Printer
    from pip_size.core import PyPIClient

    req = Requirement(spec)
    async with PyPIClient() as client:
        resolver = DependencyResolver(client=client, quiet=True)
        pkg = await resolver.resolve(req)

    if pkg is None:
        return {"available": False, "error": "pip-size could not resolve this package on PyPI"}

    def _flatten(p):
        out = [{"name": p.name, "version": p.version, "size": Printer.format_size(p.size)}]
        for d in p.dependencies:
            out.extend(_flatten(d))
        return out

    deps = _flatten(pkg)[1:]  # everything but the package itself
    return {
        "available": True,
        "name": pkg.name,
        "version": pkg.version,
        "size": Printer.format_size(pkg.size),
        "total_size": Printer.format_size(pkg.total_size()),
        "filename": pkg.filename,
        "dependencies": deps,  # transitive, flattened -- what total_size() actually sums
    }


def _pip_size(spec):
    try:
        return asyncio.run(_resolve(spec))
    except ImportError:
        return {"available": False, "error": "pip-size is not installed"}
    except Exception as e:
        return {"available": False, "error": f"{type(e).__name__}: {e}"}


def run():
    result = {}
    for key, (spec, capability) in PACKAGES.items():
        data = _pip_size(spec)
        data["capability"] = capability
        result[key] = data
    result["elementtree"] = {
        "available": True, "name": "elementtree", "version": "stdlib",
        "size": "0 B", "total_size": "0 B", "dependencies": [],
        "capability": "dom, streaming iterparse (Python standard library)",
        "note": "Python standard library -- always present, nothing to install",
    }
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", help="path to write results JSON")
    args = p.parse_args()

    result = run()

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    for pkg, data in result.items():
        if data.get("available"):
            ndeps = len(data.get("dependencies", []))
            print(f"{pkg:12s} {data.get('total_size', '?'):>10s}  ({ndeps} dependenc{'y' if ndeps==1 else 'ies'})", file=sys.stderr)
        else:
            print(f"{pkg:12s} unavailable: {data.get('error')}", file=sys.stderr)
