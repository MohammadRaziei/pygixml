"""
bench_sizes.py — real install footprint (download size, including
dependencies) for pygixml vs. the competitors this suite benchmarks,
using `pip-size` (github.com/MohammadRaziei/pip-size) -- it resolves
the real wheel for the current platform/Python from PyPI's index and
sums sizes without actually downloading/installing anything.

ElementTree needs no entry: it's in the Python standard library, 0
extra bytes, on every Python install already -- which is itself a
fair, reportable data point (the "free" option), not something
pip-size can meaningfully quantify.
"""
import argparse
import json
import subprocess
import sys

PACKAGES = ["pygixml", "lxml", "xmltodict", "xmljson"]


def _pip_size(package):
    try:
        out = subprocess.run(
            ["pip-size", package, "--json", "--quiet"],
            capture_output=True, text=True, timeout=60, check=True,
        )
        data = json.loads(out.stdout)
        return {"available": True, **data}
    except FileNotFoundError:
        return {"available": False, "error": "pip-size is not installed"}
    except subprocess.CalledProcessError as e:
        return {"available": False, "error": e.stderr.strip()[-500:]}
    except json.JSONDecodeError as e:
        return {"available": False, "error": f"couldn't parse pip-size output: {e}"}


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
