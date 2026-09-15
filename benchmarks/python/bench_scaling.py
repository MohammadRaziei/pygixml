"""
bench_scaling.py — time vs input size (N), not just one fixed size.

Two things this is trying to show, honestly, including the case that
doesn't flatter pygixml:

  1. For the shape almost all real giant XML actually has -- one
     repeated tag per level (<orders><order>...</order>...</orders>)
     -- pygixml.jsonify.stream_dump is linear in N, and so is
     everything else here (parsing is fundamentally at least O(n) for
     all of them). The interesting differentiator at this shape is
     the *constant factor*, which bench_throughput.py already covers
     at fixed sizes -- this script instead confirms the *slope*
     doesn't change, i.e. nobody's showing hidden superlinear cost.

  2. For the interleaved-siblings shape specifically (two different
     repeated tags interleaved at the same level), pygixml's own
     stream_dump documented complexity caveat (see
     docs/source/jsonify.rst) predicts time approaching O(n^2). This
     script draws that curve for real, at the sizes this repo's own
     test suite already confirmed it at, so the report can show it
     rather than just cite it.

DOM-competitors (lxml/xmltodict/xmljson) are included at moderate N
only -- large enough to see the trend, small enough that this script
finishes in reasonable time; unlike pygixml.jsonify.dumps, none of
them have a documented superlinear risk, so there's no need to push
them to the sizes that would demonstrate one.
"""
import gc
import json
import time

from corpus import gen_records, gen_interleaved

RECORD_NS = [500, 2000, 8000, 32000, 128000]
INTERLEAVED_NS = [500, 2000, 8000, 32000, 128000]
DOM_COMPETITOR_NS = [500, 2000, 8000, 32000]  # kept smaller -- see docstring


def _time_once(fn):
    gc.collect()
    t0 = time.perf_counter()
    fn()
    return time.perf_counter() - t0


def run(tmp_dir):
    import os
    import pygixml
    from pygixml import jsonify

    have_lxml = have_xmltodict = have_xmljson = True
    try:
        import lxml.etree as LET
    except ImportError:
        have_lxml = False
    try:
        import xmltodict
    except ImportError:
        have_xmltodict = False
    try:
        import xmljson
    except ImportError:
        have_xmljson = False

    xml_path = os.path.join(tmp_dir, "scaling_input.xml")
    json_path = os.path.join(tmp_dir, "scaling_output.json")

    def stream_dump_curve(gen_fn, ns):
        points = []
        for n in ns:
            xml = gen_fn(n)
            with open(xml_path, "w", encoding="utf-8") as f:
                f.write(xml)
            t = _time_once(lambda: jsonify.stream_dump(xml_path, json_path, indent=0))
            points.append({"n": n, "bytes": len(xml.encode("utf-8")), "seconds": t})
        return points

    result = {
        "pygixml_stream_dump": {
            "records_shape": stream_dump_curve(gen_records, RECORD_NS),
            "interleaved_shape": stream_dump_curve(gen_interleaved, INTERLEAVED_NS),
        },
        "dom_competitors_records_shape": {},
    }

    # DOM competitors, records shape only (the realistic one), moderate N
    for name, available, fn in [
        ("pygixml_dom", True, lambda xml: jsonify.dumps(xml)),
        ("lxml_plus_xmljson", have_lxml and have_xmljson,
         (lambda xml: json.dumps(__import__("xmljson").parker.data(
             __import__("lxml.etree", fromlist=["etree"]).fromstring(xml.encode("utf-8")))))
         if have_lxml and have_xmljson else None),
        ("xmltodict", have_xmltodict,
         (lambda xml: json.dumps(__import__("xmltodict").parse(xml)))
         if have_xmltodict else None),
    ]:
        if not available:
            result["dom_competitors_records_shape"][name] = {"available": False}
            continue
        points = []
        for n in DOM_COMPETITOR_NS:
            xml = gen_records(n)
            t = _time_once(lambda: fn(xml))
            points.append({"n": n, "bytes": len(xml.encode("utf-8")), "seconds": t})
        result["dom_competitors_records_shape"][name] = {"available": True, "points": points}

    return result


if __name__ == "__main__":
    import argparse
    import json as _json
    import os as _os
    import sys
    import tempfile

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", help="path to write results JSON")
    p.add_argument("--tmp-dir", default=None, help="scratch dir for generated XML/JSON (default: a temp dir)")
    args = p.parse_args()

    tmp_dir = args.tmp_dir or tempfile.mkdtemp(prefix="pygixml_bench_scaling_")
    _os.makedirs(tmp_dir, exist_ok=True)

    result = run(tmp_dir)

    with open(args.output, "w", encoding="utf-8") as f:
        _json.dump(result, f, indent=2)

    print(f"bench_scaling: wrote {args.output}", file=sys.stderr)
