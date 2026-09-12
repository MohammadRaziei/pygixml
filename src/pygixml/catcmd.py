"""
pygixml.catcmd — pretty-print (and, if colorama is installed,
colorize) an XML file for the terminal. The XML analog of
``cat data.json | jq`` -- except we produce XML, not consume it, so
this reads XML and shows it nicely instead.

Usage::

    pygixml cat [OPTIONS] FILE
    python -m pygixml cat [OPTIONS] FILE

Examples::

    pygixml cat data.xml                  # pretty + colorized (if a tty
                                           # and colorama is installed)
    cat data.xml | pygixml cat -          # from stdin
    pygixml cat data.xml --color always   # force color even when piped
    pygixml cat data.xml --color never    # force plain, no color
    pygixml cat data.xml --indent 4       # 4-space indent instead of 2

Loads the full document (like ``pygixml query``/``pygixml jsonify``'s
DOM mode) -- this is a tool for looking at a file, not for giant
records; use ``pygixml stream`` for anything too large to fit in
memory.

If colorama isn't installed, this still works -- it just prints plain
pretty-printed XML with no color codes, same as it would for
``--color never``.
"""

from __future__ import annotations

import argparse
import re
import sys


def _non_negative_int(s: str) -> int:
    n = int(s)
    if n < 0:
        raise argparse.ArgumentTypeError(f"must be >= 0, got {n}")
    return n


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Pretty-print (and colorize) an XML file.",
    )
    p.add_argument(
        "file", metavar="FILE",
        help='XML file to display. Use "-" to read from stdin.',
    )
    p.add_argument(
        "--indent", type=_non_negative_int, default=2, metavar="N",
        help="Spaces per indent level (default: 2).",
    )
    p.add_argument(
        "--color", choices=["auto", "always", "never"], default="auto",
        help="Colorize output. 'auto' (default) colorizes only on a "
             "real terminal and only if colorama is installed; "
             "'always'/'never' force it on/off.",
    )
    return p


_DECL_RE = re.compile(r"^\s*(<\?xml[^>]*\?>)")


def main(argv: list[str] | None = None) -> int:
    import pygixml
    from pygixml import _xmlcolor

    args = _build_parser().parse_args(argv)

    if args.file == "-":
        raw = sys.stdin.buffer.read().decode("utf-8")
        doc = pygixml.parse_string(raw)
    else:
        with open(args.file, "r", encoding="utf-8") as f:
            raw = f.read()
        doc = pygixml.parse_file(args.file)

    pretty = doc.to_string(indent=" " * args.indent)

    # to_string() doesn't round-trip the <?xml ...?> declaration -- pull
    # it from the original source instead, if it was there.
    decl_match = _DECL_RE.match(raw)
    if decl_match and not pretty.startswith("<?xml"):
        pretty = decl_match.group(1) + "\n" + pretty

    enabled = _xmlcolor.should_colorize(args.color, sys.stdout)
    out = _xmlcolor.colorize_xml(pretty, enabled)

    sys.stdout.write(out)
    if not out.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
