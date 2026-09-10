"""
pygixml.streamcmd — stream matching elements out of a (possibly
giant) XML file as JSON, with bounded ("one record") memory.

Unlike ``pygixml query`` (which loads the whole document), this reads
the file once, tag by tag, via :func:`pygixml.iterparse`, and never
holds more than one matched element's subtree in memory at a time --
suitable for files far larger than RAM.

Usage::

    python -m pygixml stream FILE --tag TAG [OPTIONS]

Examples::

    # every <order> as one JSON object per line (JSONL)
    pygixml stream orders.xml --tag order

    # only orders over $100
    pygixml stream orders.xml --tag order --where "total>100"

    # only orders for a given customer, matching an attribute
    pygixml stream orders.xml --tag order --where "@status=shipped"

    # multiple --where are AND'ed together
    pygixml stream orders.xml --tag order \\
        --where "total>100" --where "customer=acme"

    # wrap matches in a JSON array instead of JSONL (still one pass,
    # still bounded memory -- the array brackets are just written as
    # each match streams by, never buffered)
    pygixml stream orders.xml --tag order --format array -p

    # stop after the first 10 matches
    pygixml stream orders.xml --tag order --limit 10

    # just count matches, don't print them
    pygixml stream orders.xml --tag order --where "total>100" --count

    cat orders.xml | pygixml stream - --tag order
"""

from __future__ import annotations

import argparse
import sys


_OPS = ["!=", ">=", "<=", "=", ">", "<"]  # longest-first, checked in order


def _parse_where(expr: str):
    """Parse "path OP value" into (path, op, value)."""
    for op in _OPS:
        idx = expr.find(op)
        if idx != -1:
            return expr[:idx].strip(), op, expr[idx + len(op):].strip()
    raise ValueError(
        f"--where {expr!r}: expected one of {_OPS} (e.g. \"price>10\", "
        f"\"@status=shipped\")"
    )


def _resolve_path(elem, path: str):
    """Get a value off a StreamElement: '@attr', '.'/'text()', or a
    findtext()-style child path like 'a/b/c'."""
    if path.startswith("@"):
        return elem.get(path[1:])
    if path in (".", "text()"):
        return elem.text
    return elem.findtext(path)


def _compare(actual, op: str, expected: str) -> bool:
    if actual is None:
        return False
    if op in ("=", "!="):
        eq = str(actual) == expected
        return eq if op == "=" else not eq
    # numeric comparison
    try:
        a, b = float(actual), float(expected)
    except (TypeError, ValueError):
        return False
    if op == ">":
        return a > b
    if op == "<":
        return a < b
    if op == ">=":
        return a >= b
    if op == "<=":
        return a <= b
    return False


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pygixml-stream",
        description="Stream matching elements out of a huge XML file as JSON, "
                     "in bounded (one-record) memory.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("file", metavar="FILE",
                    help='XML file to scan. Use "-" to read from stdin.')
    p.add_argument("--tag", "-t", required=True, metavar="TAG",
                    help="Only elements with this tag are considered.")
    p.add_argument("--where", "-w", action="append", default=[],
                    metavar="EXPR",
                    help='Filter, e.g. "price>10" or "@status=shipped". '
                         "Repeatable; all conditions must hold (AND).")
    p.add_argument("--format", "-f", choices=["jsonl", "array"], default="jsonl",
                    help="jsonl: one JSON object per line (default). "
                         "array: a single JSON array, still streamed.")
    p.add_argument("--pretty", "-p", action="store_true", default=False,
                    help="Pretty-print each matched object (2-space indent).")
    p.add_argument("--force-list", action="append", default=None,
                    dest="force_list", metavar="TAG",
                    help="Always serialize this child tag as a list. Repeatable.")
    p.add_argument("--limit", "-n", type=int, default=None, metavar="N",
                    help="Stop after N matches.")
    p.add_argument("--count", "-c", action="store_true", default=False,
                    help="Print only the number of matches.")
    p.add_argument("--output", "-o", metavar="PATH", default=None,
                    help="Write output here instead of stdout.")
    return p


def main(argv: list[str] | None = None) -> int:
    import pygixml
    from pygixml import jsonify

    args = _build_parser().parse_args(argv)

    try:
        conditions = [_parse_where(w) for w in args.where]
    except ValueError as e:
        print(f"pygixml-stream: {e}", file=sys.stderr)
        return 2

    force_list = set(args.force_list) if args.force_list else None
    source = sys.stdin.buffer if args.file == "-" else args.file

    out = open(args.output, "w", encoding="utf-8") if args.output else sys.stdout

    count = 0
    exit_code = 1  # like grep: 0 only if something matched (or --count ran)
    try:
        if args.format == "array" and not args.count:
            out.write("[")

        for event, elem in pygixml.iterparse(source, events=("end",), tag=args.tag):
            try:
                if not all(_compare(_resolve_path(elem, path), op, val)
                           for path, op, val in conditions):
                    continue

                exit_code = 0
                count += 1

                if not args.count:
                    if args.format == "array":
                        if count > 1:
                            out.write(",")
                        if args.pretty:
                            out.write("\n  ")
                    line = elem.to_json(force_list=force_list)
                    if args.pretty and args.format == "jsonl":
                        import json as _json
                        line = _json.dumps(_json.loads(line), indent=2, ensure_ascii=False)
                    out.write(line)
                    if args.format == "jsonl":
                        out.write("\n")

                if args.limit is not None and count >= args.limit:
                    break
            finally:
                elem.clear()

        if args.format == "array" and not args.count:
            out.write("\n]\n" if args.pretty and count else "]")

        if args.count:
            out.write(f"{count}\n")
    finally:
        if args.output:
            out.close()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
