"""
bench_throughput.py — parse and conversion throughput, across every
genre/size in the corpus, for every library that's installed.

pygixml is not "a JSON library" -- it's a set of independent
conversion layers on top of two C/C++ cores (pugixml's DOM, an inlined
yxml streaming parser). Each layer gets its own fair, apples-to-apples
operation below instead of being collapsed into a single "xml_to_json"
number, so dictify/objectify/streaming aren't invisible just because
they don't happen to produce JSON.

Six operations, run independently (a library can be fast at one and
slow at another):

  parse           Build a tree from the XML string and discard it
                   (pugixml core). Only libraries with a real DOM
                   concept participate: pygixml, lxml, ElementTree.

  iterparse       Stream every <record_tag> element and discard it,
                   never holding the whole document (yxml core, via
                   pygixml.iterfind). Matched against lxml's and
                   ElementTree's own iterparse -- both real streaming
                   APIs, not improvised. Only runs on corpus entries
                   with a uniformly repeated element (see corpus.py's
                   RECORD_TAG); a deep, low-repetition tree like
                   "config" genuinely has no streaming target.

  dict_convert    XML string in, plain dict out.
                    - pygixml.dictify.parse   (matches xmltodict's own
                                                convention -- @-prefixed
                                                attrs, #text for mixed
                                                content -- by design, so
                                                the two are directly
                                                comparable, not just
                                                "both produce a dict")
                    - xmltodict.parse          (its whole purpose)

  dict_stream     Same dict conversion, but streamed one record at a
                   time instead of materializing the whole document as
                   one dict (pygixml.dictify.iterdict vs xmltodict's
                   own item_depth/item_callback streaming mode --
                   xmltodict genuinely supports this, not a fallback).
                   Same record-tag restriction as iterparse.

  to_object       XML string in, a lazy attribute-style object out
                   (root.child.grandchild, not a materialized dict/tree).
                    - pygixml.objectify.from_string
                    - lxml.objectify.fromstring (lxml ships a real
                                                  objectify submodule --
                                                  this is a genuine,
                                                  not improvised, match)

  xml_to_json     The end-to-end operation most people actually want: XML
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

Each (library, genre, size) cell is repeated REPEATS times (configurable
via --repeats / PYGIXML_BENCH_REPEATS, default 7) and the
best (min) wall-clock time is kept -- standard practice for
micro-benchmarks, since it's the closest single run gets to "no other
process happened to interrupt this one."
"""
import gc
import json
import time

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable

DEFAULT_REPEATS = 7


def _best_time(fn, repeats):
    best = None
    for _ in range(repeats):
        gc.collect()
        t0 = time.perf_counter()
        fn()
        dt = time.perf_counter() - t0
        if best is None or dt < best:
            best = dt
    return best


def _try(label, fn, repeats):
    try:
        dt = _best_time(fn, repeats)
        return {"available": True, "seconds": dt}
    except Exception as e:
        return {"available": False, "error": f"{type(e).__name__}: {e}"}


def run(manifest, repeats=DEFAULT_REPEATS):
    import pygixml
    from pygixml import jsonify, dictify, objectify

    have_lxml = have_et = have_xmltodict = have_xmljson = True
    try:
        import lxml.etree as LET
    except ImportError:
        have_lxml = False
    try:
        import lxml.objectify as LOBJ
    except ImportError:
        LOBJ = None
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

    def _consume_pygixml_iterfind(path, tag):
        for elem in pygixml.iterfind(path, tag):
            elem.clear()

    def _consume_lxml_iterparse(path, tag):
        for _event, elem in LET.iterparse(path, events=("end",), tag=tag):
            elem.clear()

    def _consume_et_iterparse(path, tag):
        for _event, elem in ET.iterparse(path, events=("end",)):
            if elem.tag == tag:
                elem.clear()

    def _consume_pygixml_iterdict(path, tag):
        for _d in dictify.iterdict(path, tag):
            pass

    def _consume_xmltodict_stream(xml_bytes, depth):
        xmltodict.parse(xml_bytes, item_depth=depth, item_callback=lambda *a: True)

    results = []

    for entry in tqdm(manifest, desc="bench_throughput", unit="file"):
        with open(entry["path"], "r", encoding="utf-8") as f:
            xml_text = f.read()
        xml_bytes = xml_text.encode("utf-8")
        record_tag = entry.get("record_tag")
        record_depth = entry.get("record_depth")
        row = {"genre": entry["genre"], "size": entry["size"],
               "bytes": entry["bytes"], "libraries": {}}

        # ---- parse ----
        parse = {}
        parse["pygixml"] = _try("parse", lambda: pygixml.parse_string(xml_text), repeats)
        if have_lxml:
            parse["lxml"] = _try("parse", lambda: LET.fromstring(xml_bytes), repeats)
        if have_et:
            parse["elementtree"] = _try("parse", lambda: ET.fromstring(xml_text), repeats)
        row["parse"] = parse

        # ---- iterparse (streaming, needs a uniformly repeated tag) ----
        iterp = {}
        if record_tag:
            iterp["pygixml"] = _try(
                "iterparse", lambda: _consume_pygixml_iterfind(entry["path"], record_tag), repeats)
            if have_lxml:
                iterp["lxml"] = _try(
                    "iterparse", lambda: _consume_lxml_iterparse(entry["path"], record_tag), repeats)
            if have_et:
                iterp["elementtree"] = _try(
                    "iterparse", lambda: _consume_et_iterparse(entry["path"], record_tag), repeats)
        row["iterparse"] = iterp

        # ---- dict_convert ----
        # Same convention on both sides (@attr, #text) -- a genuinely
        # fair like-for-like, not "both happen to produce a dict".
        d2d = {}
        d2d["pygixml"] = _try("dict_convert", lambda: dictify.parse(xml_text), repeats)
        if have_xmltodict:
            d2d["xmltodict"] = _try("dict_convert", lambda: xmltodict.parse(xml_text), repeats)
        row["dict_convert"] = d2d

        # ---- dict_stream (streaming dict conversion, needs a record tag) ----
        d2ds = {}
        if record_tag:
            d2ds["pygixml"] = _try(
                "dict_stream", lambda: _consume_pygixml_iterdict(entry["path"], record_tag), repeats)
            if have_xmltodict:
                d2ds["xmltodict"] = _try(
                    "dict_stream", lambda: _consume_xmltodict_stream(xml_bytes, record_depth), repeats)
        row["dict_stream"] = d2ds

        # ---- to_object ----
        # Lazy attribute-style access, not a materialized dict/tree --
        # its own distinct approach, benchmarked against lxml's own
        # objectify submodule (a real feature match, not an improvised one).
        o2o = {}
        o2o["pygixml"] = _try("to_object", lambda: objectify.from_string(xml_text), repeats)
        if have_lxml and LOBJ is not None:
            o2o["lxml"] = _try("to_object", lambda: LOBJ.fromstring(xml_bytes), repeats)
        row["to_object"] = o2o

        # ---- xml_to_json ----
        x2j = {}
        x2j["pygixml"] = _try("xml_to_json", lambda: jsonify.dumps(xml_text), repeats)
        if have_xmltodict:
            x2j["xmltodict"] = _try(
                "xml_to_json",
                lambda: json.dumps(xmltodict.parse(xml_text)),
                repeats,
            )
        if have_xmljson and have_lxml:
            x2j["xmljson"] = _try(
                "xml_to_json",
                lambda: json.dumps(xmljson.parker.data(LET.fromstring(xml_bytes))),
                repeats,
            )
        row["xml_to_json"] = x2j

        results.append(row)

    return {
        "operation_notes": {
            "parse": "build a tree from the XML string, discard it (pugixml core)",
            "iterparse": "stream every record element and discard it (yxml core); needs a uniformly repeated tag",
            "dict_convert": "XML string in, plain dict out (same @attr/#text convention both sides)",
            "dict_stream": "same dict conversion, streamed one record at a time; needs a uniformly repeated tag",
            "to_object": "XML string in, lazy attribute-style object out",
            "xml_to_json": "XML string in, JSON string out, end to end",
        },
        "repeats": repeats,
        "metric": "best (min) wall-clock seconds over repeats",
        "results": results,
    }


if __name__ == "__main__":
    import argparse
    import json as _json
    import sys

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifests", nargs="+",
                    help="one or more JSON manifests from corpus.py / real_corpus_manifest.py "
                         "(each a list of {genre,size,path,bytes}); merged together")
    p.add_argument("output", help="path to write results JSON")
    p.add_argument("--repeats", type=int, default=DEFAULT_REPEATS,
                    help=f"timed repeats per (library, corpus entry, operation) cell; "
                         f"best (min) of these is kept (default: {DEFAULT_REPEATS})")
    args = p.parse_args()

    manifest = []
    for m_path in args.manifests:
        with open(m_path, "r", encoding="utf-8") as f:
            manifest.extend(_json.load(f))

    result = run(manifest, repeats=args.repeats)

    with open(args.output, "w", encoding="utf-8") as f:
        _json.dump(result, f, indent=2)

    ops = ["parse", "iterparse", "dict_convert", "dict_stream", "to_object", "xml_to_json"]
    n_libs = len({lib for row in result["results"] for op in ops for lib in row[op]})
    print(f"bench_throughput: {len(result['results'])} corpus entries, "
          f"{n_libs} libraries, {len(ops)} operations -> {args.output}", file=sys.stderr)
