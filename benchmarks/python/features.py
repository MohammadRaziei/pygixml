"""
features.py — a static, hand-curated feature comparison matrix.

Not measured by running anything (some of these -- XSLT, schema
validation -- aren't meaningfully "benchmarkable" against something
that doesn't have the feature at all); this is a factual capability
table, kept in its own script/target so it's reviewable and editable
on its own, separately from anything that runs code.

Every claim here should be independently verifiable from each
project's own documentation. If pygixml ever gains one of the "No"s
below, update this file -- it's meant to be a living comparison, not a
one-time snapshot.
"""
import argparse
import json

LIBRARIES = ["pygixml", "lxml", "elementtree", "xmltodict", "xmljson"]

# value: "yes" | "no" | "partial"
FEATURES = [
    {
        "feature": "XPath queries",
        "note": "Selecting nodes with an XPath expression.",
        "values": {
            "pygixml": {"value": "yes", "detail": "Full XPath 1.0 (via pugixml)"},
            "lxml": {"value": "yes", "detail": "Full XPath 1.0, plus some XPath/EXSLT extensions"},
            "elementtree": {"value": "partial", "detail": "A small subset: no predicates like position()/functions, limited axes"},
            "xmltodict": {"value": "no"},
            "xmljson": {"value": "no"},
        },
    },
    {
        "feature": "XSLT transforms",
        "values": {
            "pygixml": {"value": "no"},
            "lxml": {"value": "yes", "detail": "via libxslt"},
            "elementtree": {"value": "no"},
            "xmltodict": {"value": "no"},
            "xmljson": {"value": "no"},
        },
    },
    {
        "feature": "XML Schema (XSD) / DTD validation",
        "values": {
            "pygixml": {"value": "no"},
            "lxml": {"value": "yes", "detail": "via libxml2"},
            "elementtree": {"value": "no"},
            "xmltodict": {"value": "no"},
            "xmljson": {"value": "no"},
        },
    },
    {
        "feature": "Streaming, item-by-item parse",
        "note": "Process one element at a time without holding the whole tree.",
        "values": {
            "pygixml": {"value": "yes", "detail": "iterparse/iterfind (yxml-based)"},
            "lxml": {"value": "yes", "detail": "iterparse"},
            "elementtree": {"value": "yes", "detail": "iterparse"},
            "xmltodict": {"value": "yes", "detail": "item_depth + item_callback"},
            "xmljson": {"value": "no", "detail": "needs an already-built tree"},
        },
    },
    {
        "feature": "Constant-memory XML \u2192 single JSON document",
        "note": "Converting a file too large to fit in RAM into one valid JSON document, without loading the whole tree.",
        "values": {
            "pygixml": {"value": "yes", "detail": "jsonify.stream_dump -- see docs/source/jsonify.rst for the one documented case where its time (never memory) can degrade"},
            "lxml": {"value": "no"},
            "elementtree": {"value": "no"},
            "xmltodict": {"value": "no", "detail": "item_depth streams *dicts* to a callback, not a single reconstructed JSON document"},
            "xmljson": {"value": "no"},
        },
    },
    {
        "feature": "Built-in XML \u2194 dict/JSON conversion",
        "values": {
            "pygixml": {"value": "yes", "detail": "dictify (xmltodict-compatible shape) + jsonify"},
            "lxml": {"value": "no", "detail": "needs a separate library, e.g. xmljson"},
            "elementtree": {"value": "no"},
            "xmltodict": {"value": "yes", "detail": "its entire purpose"},
            "xmljson": {"value": "yes", "detail": "its entire purpose (needs lxml or ElementTree for parsing first)"},
        },
    },
    {
        "feature": "YAML / TOON conversion",
        "values": {
            "pygixml": {"value": "yes", "detail": "pygixml convert / FormatDocument (optional deps)"},
            "lxml": {"value": "no"},
            "elementtree": {"value": "no"},
            "xmltodict": {"value": "no"},
            "xmljson": {"value": "no"},
        },
    },
    {
        "feature": "Dotted / attribute-style navigation",
        "note": "doc.root.child.grandchild instead of find()/XPath.",
        "values": {
            "pygixml": {"value": "yes", "detail": "objectify"},
            "lxml": {"value": "yes", "detail": "lxml.objectify"},
            "elementtree": {"value": "no"},
            "xmltodict": {"value": "no", "detail": "plain dict access only"},
            "xmljson": {"value": "no"},
        },
    },
    {
        "feature": "Command-line tools",
        "values": {
            "pygixml": {"value": "yes", "detail": "cat, query, jsonify, stream, convert"},
            "lxml": {"value": "no"},
            "elementtree": {"value": "no"},
            "xmltodict": {"value": "no"},
            "xmljson": {"value": "no"},
        },
    },
    {
        "feature": "Backend",
        "values": {
            "pygixml": {"value": "yes", "detail": "C++ (pugixml + an inlined yxml push parser) via Cython"},
            "lxml": {"value": "yes", "detail": "C (libxml2 / libxslt)"},
            "elementtree": {"value": "partial", "detail": "C accelerator (_elementtree) with a pure-Python fallback"},
            "xmltodict": {"value": "no", "detail": "pure Python, over the stdlib's expat"},
            "xmljson": {"value": "no", "detail": "pure Python"},
        },
    },
    {
        "feature": "Standard library (zero install)",
        "values": {
            "pygixml": {"value": "no"},
            "lxml": {"value": "no"},
            "elementtree": {"value": "yes"},
            "xmltodict": {"value": "no"},
            "xmljson": {"value": "no"},
        },
    },
    {
        "feature": "abi3 / stable-ABI wheels",
        "note": "One compiled wheel works across multiple Python minor versions (faster installs, smaller PyPI footprint).",
        "values": {
            "pygixml": {"value": "yes", "detail": "cp310-abi3, covers 3.10+"},
            "lxml": {"value": "no", "detail": "per-Python-version wheels"},
            "elementtree": {"value": "yes", "detail": "n/a -- stdlib, ships with the interpreter itself"},
            "xmltodict": {"value": "yes", "detail": "n/a -- pure Python, no compiled extension"},
            "xmljson": {"value": "yes", "detail": "n/a -- pure Python, no compiled extension"},
        },
    },
]


def run():
    return {"libraries": LIBRARIES, "features": FEATURES}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", help="path to write the feature matrix JSON")
    args = p.parse_args()

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(run(), f, indent=2, ensure_ascii=False)

    print(f"features: {len(FEATURES)} features x {len(LIBRARIES)} libraries -> {args.output}")
