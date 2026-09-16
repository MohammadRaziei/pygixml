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

PACKAGES = ["pygixml", "lxml", "xmltodict", "xmljson"]


async def _resolve(package):
    from packaging.requirements import Requirement
    from pip_size import DependencyResolver, Printer
    from pip_size.core import PyPIClient

    req = Requirement(package)
    async with PyPIClient() as client:
        resolver = DependencyResolver(client=client, quiet=True)
        pkg = await resolver.resolve(req)

    if pkg is None:
        return {"available": False, "error": "pip-size could not resolve this package on PyPI"}

    return {
        "available": True,
        "name": pkg.name,
        "version": pkg.version,
        "size": Printer.format_size(pkg.size),
        "total_size": Printer.format_size(pkg.total_size()),
        "filename": pkg.filename,
    }


def _pip_size(package):
    try:
        return asyncio.run(_resolve(package))
    except ImportError:
        return {"available": False, "error": "pip-size is not installed"}
    except Exception as e:
        return {"available": False, "error": f"{type(e).__name__}: {e}"}


def run():
    result = {pkg: _pip_size(pkg) for pkg in PACKAGES}
    result["elementtree"] = {
        "available": True, "name": "elementtree", "version": "stdlib",
        "size": "0 B", "total_size": "0 B",
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
            print(f"{pkg:12s} {data.get('total_size', '?'):>10s}", file=sys.stderr)
        else:
            print(f"{pkg:12s} unavailable: {data.get('error')}", file=sys.stderr)
