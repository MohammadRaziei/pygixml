"""
bench_memory_one.py — measure ONE (approach, input file) memory data
point, in THIS process, and write ONE small result JSON.

Deliberately does not loop over sizes or spawn subprocesses itself --
see bench_memory_gen.py's docstring for why. CMake invokes this fresh,
once per (size, approach) combination; every invocation's parent is a
CMake/shell process that has never touched any corpus data, so there's
nothing inflated to inherit.
"""
import argparse
import json
import os
import resource
import sys

APPROACHES = (
    "pygixml_stream_dump",
    "pygixml_dom",
    "lxml_plus_xmljson",
    "xmltodict",
)


def _run_pygixml_stream_dump(xml_path, scratch_json_path):
    from pygixml import jsonify
    jsonify.stream_dump(xml_path, scratch_json_path, indent=0)


def _run_pygixml_dom(xml_path, scratch_json_path):
    from pygixml import jsonify
    with open(xml_path, "r", encoding="utf-8") as f:
        text = f.read()
    jsonify.dumps(text)


def _run_lxml_plus_xmljson(xml_path, scratch_json_path):
    import lxml.etree as ET
    import xmljson
    tree = ET.parse(xml_path)
    json.dumps(xmljson.parker.data(tree.getroot()))


def _run_xmltodict(xml_path, scratch_json_path):
    import xmltodict
    with open(xml_path, "r", encoding="utf-8") as f:
        text = f.read()
    json.dumps(xmltodict.parse(text))


_RUNNERS = {
    "pygixml_stream_dump": _run_pygixml_stream_dump,
    "pygixml_dom": _run_pygixml_dom,
    "lxml_plus_xmljson": _run_lxml_plus_xmljson,
    "xmltodict": _run_xmltodict,
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("approach", choices=APPROACHES)
    p.add_argument("xml_path")
    p.add_argument("scratch_json_path", help="scratch output path (only pygixml_stream_dump writes here)")
    p.add_argument("output", help="path to write this one data point's result JSON")
    p.add_argument("--n", type=int, default=None, help="record count, echoed into the result for convenience")
    args = p.parse_args()

    runner = _RUNNERS[args.approach]

    try:
        runner(args.xml_path, args.scratch_json_path)
    except ImportError as e:
        result = {"approach": args.approach, "n": args.n, "available": False,
                   "error": f"{type(e).__name__}: {e}"}
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"bench_memory_one: {args.approach} unavailable ({e})", file=sys.stderr)
        return

    peak_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    result = {
        "approach": args.approach,
        "n": args.n,
        "bytes": os.path.getsize(args.xml_path),
        "available": True,
        "peak_rss_mb": peak_kb / 1024.0,
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"bench_memory_one: {args.approach} n={args.n} peak={result['peak_rss_mb']:.2f}MB", file=sys.stderr)


if __name__ == "__main__":
    main()
