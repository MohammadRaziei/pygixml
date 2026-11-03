"""
bench_html_memory_one.py: peak RSS of ONE (library, HTML file) parse, measured in
THIS process, one JSON line on stdout. The worker half of bench_html_memory.py,
for the same reason as bench_op_memory_one.py: a fresh process per data point,
because ru_maxrss only ever grows.

Operation: html_parse, as in bench_html.py (HTML string in, tree out, tree kept
alive until the next repeat replaces it).
"""
import argparse
import json
import os
import resource

REPEATS = 3  # peak RSS only grows across repeats; a few make sure it is not a cold-cache fluke


def _parser(library):
    if library == "pygixml":
        import pygixml
        return pygixml.parse_html
    if library == "lxml":
        import lxml.html as LH
        return LH.document_fromstring
    if library in ("bs4_html_parser", "bs4_lxml"):
        from bs4 import BeautifulSoup
        backend = "html.parser" if library == "bs4_html_parser" else "lxml"
        return lambda h: BeautifulSoup(h, backend)
    if library == "html5lib":
        import html5lib
        return html5lib.parse
    if library == "selectolax":
        from selectolax.lexbor import LexborHTMLParser
        return LexborHTMLParser
    raise ValueError(f"no parser for library={library!r}")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("library")
    p.add_argument("html_path")
    args = p.parse_args()
    result = {"operation": "html_parse", "library": args.library, "bytes": os.path.getsize(args.html_path)}
    try:
        parse = _parser(args.library)
        with open(args.html_path, "r", encoding="utf-8") as f:
            text = f.read()
        tree = None
        for _ in range(REPEATS):
            tree = parse(text)
        result["available"] = True
        result["peak_rss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
        del tree
    except Exception as e:
        result["available"] = False
        result["error"] = f"{type(e).__name__}: {e}"
    print(json.dumps(result))


if __name__ == "__main__":
    main()
