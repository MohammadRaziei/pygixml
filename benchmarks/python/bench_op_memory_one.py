"""
bench_op_memory_one.py — measure peak RSS for ONE (operation, library,
corpus file) combination, in THIS process, and print one JSON line to
stdout. This is the "worker" half of the pair with
bench_op_memory_driver.py: it never reads the manifest, never loops,
never generates data -- it's handed exactly one file path and does
exactly one thing, so it's safe to spawn fresh (see the ru_maxrss/
execve gotcha in benchmarks/README.md -- the same one bench_memory_one.py
exists to avoid).

Covers the same four throughput.json operations, so memory shows up
right next to speed for parse/dictify/objectify/jsonify, not just for
the separate stream_dump-vs-DOM story in memory.json.
"""
import argparse
import json
import os
import resource
import sys

REPEATS = 3  # peak RSS only grows across repeats (see module docstring
             # in bench_memory_one.py) -- a few repeats just makes sure
             # we're not measuring a one-off cold-cache fluke as "peak"


def _runner(operation, library, path, tag, depth):
    if operation == "parse":
        if library == "pygixml":
            import pygixml
            return lambda text, data: pygixml.parse_string(text)
        if library == "lxml":
            import lxml.etree as LET
            return lambda text, data: LET.fromstring(data)
        if library == "elementtree":
            import xml.etree.ElementTree as ET
            return lambda text, data: ET.fromstring(text)
    if operation == "iterparse":
        if not tag:
            raise ValueError("iterparse needs --tag (no uniformly repeated element in this file)")
        if library == "pygixml":
            import pygixml
            def _run(text, data):
                for elem in pygixml.iterfind(path, tag):
                    elem.clear()
            return _run
        if library == "lxml":
            import lxml.etree as LET
            def _run(text, data):
                for _event, elem in LET.iterparse(path, events=("end",), tag=tag):
                    elem.clear()
            return _run
        if library == "elementtree":
            import xml.etree.ElementTree as ET
            def _run(text, data):
                for _event, elem in ET.iterparse(path, events=("end",)):
                    if elem.tag == tag:
                        elem.clear()
            return _run
    if operation == "dict_convert":
        if library == "pygixml":
            from pygixml import dictify
            return lambda text, data: dictify.parse(text)
        if library == "xmltodict":
            import xmltodict
            return lambda text, data: xmltodict.parse(text)
    if operation == "dict_stream":
        if not tag:
            raise ValueError("dict_stream needs --tag (no uniformly repeated element in this file)")
        if library == "pygixml":
            from pygixml import dictify
            def _run(text, data):
                for _d in dictify.iterdict(path, tag):
                    pass
            return _run
        if library == "xmltodict":
            import xmltodict
            if not depth:
                raise ValueError("dict_stream needs --depth for xmltodict")
            return lambda text, data: xmltodict.parse(data, item_depth=depth, item_callback=lambda *a: True)
    if operation == "to_object":
        if library == "pygixml":
            from pygixml import objectify
            return lambda text, data: objectify.from_string(text)
        if library == "lxml":
            import lxml.objectify as LOBJ
            return lambda text, data: LOBJ.fromstring(data)
    if operation == "xml_to_json":
        if library == "pygixml":
            from pygixml import jsonify
            return lambda text, data: jsonify.dumps(text)
        if library == "xmltodict":
            import xmltodict
            return lambda text, data: json.dumps(xmltodict.parse(text))
        if library == "xmljson":
            import xmljson
            import lxml.etree as LET
            return lambda text, data: json.dumps(xmljson.parker.data(LET.fromstring(data)))
    raise ValueError(f"no runner for operation={operation!r} library={library!r}")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("operation")
    p.add_argument("library")
    p.add_argument("xml_path")
    p.add_argument("--tag", default=None, help="repeated element tag (iterparse/dict_stream only)")
    p.add_argument("--depth", type=int, default=None, help="xmltodict item_depth (dict_stream only)")
    args = p.parse_args()

    result = {"operation": args.operation, "library": args.library,
              "bytes": os.path.getsize(args.xml_path)}
    try:
        run = _runner(args.operation, args.library, args.xml_path, args.tag, args.depth)
        with open(args.xml_path, "r", encoding="utf-8") as f:
            text = f.read()
        data = text.encode("utf-8")
        for _ in range(REPEATS):
            run(text, data)
        result["available"] = True
        result["peak_rss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    except Exception as e:
        result["available"] = False
        result["error"] = f"{type(e).__name__}: {e}"

    print(json.dumps(result))


if __name__ == "__main__":
    main()
