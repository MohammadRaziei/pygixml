"""
bench_throughput.py — parse and XML→JSON throughput, across every
genre/size in the corpus, for every library that's installed.

Two operations, run independently (a library can be fast at one and
slow at the other):

  parse        Build a tree from the XML string and discard it. Only
               libraries with a real DOM concept participate: pygixml,
               lxml, ElementTree. (xmltodict/xmljson don't expose a
               separate "parse to a tree" step distinct from
               "parse straight to dict" -- they're XML-to-dict
               converters, not DOM libraries.)

  xml_to_json  The end-to-end operation most people actually want: XML
               *string* in, JSON *string* out, however the library
               gets there internally. Every library that can do this
               at all participates:
                 - pygixml.jsonify.dumps           (direct XML->JSON,
                                                     no dict step)
                 - xmltodict.parse + json.dumps     (its whole purpose)
                 - xmljson.parker + lxml + json.dumps
                 - ElementTree has no built-in dict/JSON conversion,
                   so it's excluded from this operation entirely --
                   that's a real, reportable gap, not an oversight.

Each (library, genre, size) cell is repeated REPEATS times and the
best (min) wall-clock time is kept -- standard practice for
micro-benchmarks, since it's the closest single run gets to "no other
process happened to interrupt this one."
"""
import gc
import json
import time

REPEATS = 7


def _best_time(fn, repeats=REPEATS):
    best = None
    for _ in range(repeats):
        gc.collect()
        t0 = time.perf_counter()
        fn()
        dt = time.perf_counter() - t0
        if best is None or dt < best:
            best = dt
    return best


def _try(label, fn):
    try:
        dt = _best_time(fn)
        return {"available": True, "seconds": dt}
    except Exception as e:
        return {"available": False, "error": f"{type(e).__name__}: {e}"}


def run(manifest):
    import pygixml
    from pygixml import jsonify

    have_lxml = have_et = have_xmltodict = have_xmljson = True
    try:
        import lxml.etree as LET
    except ImportError:
        have_lxml = False
    try:
        import xml.etree.ElementTree as ET
    except ImportError:
        have_et = False
    try:
        import xmltodict
    except ImportError:
        have_xmltodict = False
    try:
        import xmljson
        import lxml.etree as _LET2  # xmljson needs an ET-compatible tree
    except ImportError:
        have_xmljson = False

    results = []

    for entry in manifest:
        with open(entry["path"], "r", encoding="utf-8") as f:
            xml_text = f.read()
        xml_bytes = xml_text.encode("utf-8")
        row = {"genre": entry["genre"], "size": entry["size"],
               "bytes": entry["bytes"], "libraries": {}}

        # ---- parse ----
        parse = {}
        parse["pygixml"] = _try("parse", lambda: pygixml.parse_string(xml_text))
        if have_lxml:
            parse["lxml"] = _try("parse", lambda: LET.fromstring(xml_bytes))
        if have_et:
            parse["elementtree"] = _try("parse", lambda: ET.fromstring(xml_text))
        row["parse"] = parse

        # ---- xml_to_json ----
        x2j = {}
        x2j["pygixml"] = _try("xml_to_json", lambda: jsonify.dumps(xml_text))
        if have_xmltodict:
            x2j["xmltodict"] = _try(
                "xml_to_json",
                lambda: json.dumps(xmltodict.parse(xml_text)),
            )
        if have_xmljson and have_lxml:
            x2j["xmljson"] = _try(
                "xml_to_json",
                lambda: json.dumps(xmljson.parker.data(LET.fromstring(xml_bytes))),
            )
        row["xml_to_json"] = x2j

        results.append(row)

    return {
        "operation_notes": {
            "parse": "build a tree from the XML string, discard it",
            "xml_to_json": "XML string in, JSON string out, end to end",
        },
        "repeats": REPEATS,
        "metric": "best (min) wall-clock seconds over repeats",
        "results": results,
    }


if __name__ == "__main__":
    import argparse
    import json as _json
    import sys

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest", help="JSON manifest from corpus.py (list of {genre,size,path,bytes})")
    p.add_argument("output", help="path to write results JSON")
    args = p.parse_args()

    with open(args.manifest, "r", encoding="utf-8") as f:
        manifest = _json.load(f)

    result = run(manifest)

    with open(args.output, "w", encoding="utf-8") as f:
        _json.dump(result, f, indent=2)

    n_libs = len({lib for row in result["results"] for lib in row["parse"]} |
                 {lib for row in result["results"] for lib in row["xml_to_json"]})
    print(f"bench_throughput: {len(result['results'])} corpus entries, "
          f"{n_libs} libraries -> {args.output}", file=sys.stderr)
