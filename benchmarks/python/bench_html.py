"""
bench_html.py: HTML parsing, pygixml.parse_html against the usual Python
HTML parsers: lxml.html, BeautifulSoup (html.parser and lxml backends),
html5lib and selectolax (Lexbor). Same JSON shape as throughput.json
(minus memory), so the report renders it with the same code.

The corpus is generated here, in memory, from a fixed seed: deliberately
messy HTML (unclosed <p>/<li>/<td>/<tr>, void tags, entities, valueless
attributes) in three shapes (article, table, listing) and three sizes.

Two operations, each a real task rather than "parse and throw away" alone:

  parse          HTML string in, tree out, tree discarded.
  extract_links  parse + collect (href, text) of every <a>; the check
                 below makes sure every library finds the same links.
"""
import argparse
import json
import random
import sys
import time

SIZES = {"small": 20_000, "medium": 200_000, "large": 2_000_000}
WORDS = ("alpha beta gamma delta lorem ipsum dolor sit amet parser tree node "
         "markup fast simple robust").split()


def _text(rng, n):
    return " ".join(rng.choice(WORDS) for _ in range(n))


def _link(rng, i):
    return f'<a href="/item/{i}?ref={rng.randint(1, 999)}" class=ext>{_text(rng, 2)} {i}</a>'


def _article(rng, i):
    return (f"<h2 id=s{i}>{_text(rng, 3)}</h2>\n"
            f"<p>{_text(rng, 12)} <em>{_text(rng, 2)}</em> &amp; {_link(rng, i)} &copy; 2026<br>\n"
            f"<p>{_text(rng, 20)} <b>{_text(rng, 1)}</b> {_link(rng, i + 1)} &nbsp;{_text(rng, 8)}\n"
            f"<ul><li>{_text(rng, 3)}<li>{_text(rng, 3)} {_link(rng, i + 2)}</ul>\n")


def _table(rng, i):
    return (f"<table border=1 disabled><tr><td>{i}<td>{_text(rng, 2)}<td>{_link(rng, i)}\n"
            f"<tr><td>{i + 1}<td>{_text(rng, 2)}<td>{_text(rng, 3)}</table>\n")


def _listing(rng, i):
    return (f'<div class="card"><img src="/img/{i}.png" alt="{_text(rng, 2)}">'
            f"<h3>{_link(rng, i)}</h3><p class=price>${rng.randint(1, 99)}.{rng.randint(10, 99)}"
            f"<ul><li>{_text(rng, 2)}<li>{_text(rng, 2)}</ul></div>\n")


GENRES = {"article": _article, "table": _table, "listing": _listing}


def make_page(genre, target_bytes, seed=1234):
    rng = random.Random(f"{seed}/{genre}/{target_bytes}")
    parts, size, i = ["<!DOCTYPE html><html><head><title>bench</title><meta charset=utf-8></head><body>\n"], 0, 0
    while size < target_bytes:
        chunk = GENRES[genre](rng, i)
        parts.append(chunk)
        size += len(chunk)
        i += 3
    parts.append("</body></html>")
    return "".join(parts)


def _libraries():
    """name -> (parse(html), links(html)); only libraries that import."""
    libs = {}
    import pygixml

    def pyg_links(h):
        return [(n.node.attribute("href").value, n.node.child_value())
                for n in pygixml.parse_html(h).first_child().select_nodes("//a")]
    libs["pygixml"] = (pygixml.parse_html, pyg_links)

    try:
        import lxml.html as LH
        libs["lxml"] = (LH.document_fromstring,
                        lambda h: [(a.get("href"), a.text_content()) for a in LH.document_fromstring(h).xpath("//a")])
    except ImportError:
        pass
    try:
        from bs4 import BeautifulSoup
        for key, backend in (("bs4_html_parser", "html.parser"), ("bs4_lxml", "lxml")):
            if backend == "lxml" and "lxml" not in libs:
                continue
            libs[key] = ((lambda h, b=backend: BeautifulSoup(h, b)),
                         (lambda h, b=backend: [(a.get("href"), a.get_text())
                                                for a in BeautifulSoup(h, b).find_all("a")]))
    except ImportError:
        pass
    try:
        import html5lib
        ns = "{http://www.w3.org/1999/xhtml}a"
        libs["html5lib"] = (html5lib.parse,
                            lambda h: [(a.get("href"), "".join(a.itertext())) for a in html5lib.parse(h).iter(ns)])
    except ImportError:
        pass
    try:
        from selectolax.lexbor import LexborHTMLParser as LP
        libs["selectolax"] = (LP, lambda h: [(a.attributes.get("href"), a.text()) for a in LP(h).css("a")])
    except ImportError:
        pass
    return libs


def _best(fn, arg, repeats):
    best = float("inf")
    for _ in range(repeats):
        t = time.perf_counter()
        fn(arg)
        best = min(best, time.perf_counter() - t)
    return {"available": True, "seconds": best}


def run(repeats):
    libs = _libraries()
    results = []
    for genre in GENRES:
        for size, target in SIZES.items():
            html = make_page(genre, target)
            row = {"genre": genre, "size": size, "bytes": len(html.encode("utf-8")),
                   "html_parse": {}, "html_extract_links": {}}
            counts = {}
            for name, (parse, links) in libs.items():
                try:
                    counts[name] = len(links(html))
                    row["html_parse"][name] = _best(parse, html, repeats)
                    row["html_extract_links"][name] = _best(links, html, repeats)
                except Exception as e:  # a library failing is a result, not a crash
                    row["html_parse"][name] = row["html_extract_links"][name] = {"available": False, "error": repr(e)}
            if len(set(counts.values())) > 1:
                print(f"bench_html: WARNING {genre}/{size}: libraries found different link counts {counts}",
                      file=sys.stderr)
            results.append(row)
    return {
        "operation_notes": {
            "html_parse": "HTML string in, tree out, tree discarded",
            "html_extract_links": "parse, then collect (href, text) of every <a>",
        },
        "repeats": repeats,
        "metric": "best (min) wall-clock seconds over repeats",
        "results": results,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", help="path to write html.json")
    p.add_argument("--repeats", type=int, default=5)
    a = p.parse_args()
    out = run(a.repeats)
    with open(a.output, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"bench_html: {len(out['results'])} corpus entries -> {a.output}", file=sys.stderr)
