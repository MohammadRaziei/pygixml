"""
pygixml.convertcmd — convert a file between XML, JSON, YAML, and TOON.

Usage::

    pygixml convert INPUT [OPTIONS]
    python -m pygixml convert INPUT [OPTIONS]

Format is auto-detected from file extensions (.xml, .json, .yaml/.yml,
.toon) when possible; use --from/--to to override, and you must give
--to when writing to stdout (there's no extension to infer from).

Examples::

    pygixml convert data.xml -o data.json
    pygixml convert data.xml -o data.yaml
    pygixml convert data.json -o data.xml -p
    pygixml convert data.yaml --to toon
    cat data.xml | pygixml convert - --to json

YAML support needs PyYAML (``pip install PyYAML``); TOON support needs
ctoon (``pip install ctoon``). Both are optional -- pygixml doesn't
require them just to convert JSON <-> XML, and you get a clear error
telling you what to install if you ask for a format you don't have.

Loads the whole document in memory (like ``pygixml query``/``cat``) --
for XML too large to fit in memory, use ``pygixml jsonify --stream``
or ``pygixml stream`` instead.
"""

from __future__ import annotations

import argparse
import os
import sys

from pygixml.formats import FORMATS

_EXT_TO_FORMAT = {
    ".xml": "xml",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toon": "toon",
}


def _guess_format(path: str) -> str | None:
    _, ext = os.path.splitext(path)
    return _EXT_TO_FORMAT.get(ext.lower())


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Convert a file between XML, JSON, YAML, and TOON.",
    )
    p.add_argument(
        "file", metavar="INPUT",
        help='File to convert. Use "-" to read from stdin.',
    )
    p.add_argument(
        "--output", "-o", metavar="PATH", default=None,
        help="Write the result here instead of stdout.",
    )
    p.add_argument(
        "--from", dest="from_fmt", choices=FORMATS, default=None,
        help="Input format. Auto-detected from INPUT's extension if omitted.",
    )
    p.add_argument(
        "--to", dest="to_fmt", choices=FORMATS, default=None,
        help="Output format. Auto-detected from --output's extension if "
             "omitted; required when writing to stdout.",
    )
    p.add_argument(
        "--pretty", "-p", action="store_true", default=False,
        help="Pretty-print, where the target format supports it (json, xml).",
    )
    p.add_argument(
        "--indent", default=None, metavar="N_OR_STR",
        help="Indent for json (a number of spaces) or xml (a literal "
             "string, e.g. a tab).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    from pygixml.formats import FormatDocument

    parser = _build_parser()
    args = parser.parse_args(argv)

    from_fmt = args.from_fmt or (
        None if args.file == "-" else _guess_format(args.file)
    )
    if from_fmt is None:
        parser.error(
            f"can't tell the input format from {args.file!r} -- pass --from "
            f"explicitly (one of {FORMATS})"
        )

    to_fmt = args.to_fmt or (
        _guess_format(args.output) if args.output else None
    )
    if to_fmt is None:
        parser.error(
            "can't tell the output format -- pass --to explicitly "
            f"(one of {FORMATS}), or use -o FILE.ext"
        )

    if args.file == "-":
        text = sys.stdin.read()
    else:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()

    try:
        doc = FormatDocument.from_format(text, from_fmt)
    except ImportError as e:
        sys.stderr.write(f"{parser.prog}: {e}\n")
        return 3
    except Exception as e:
        sys.stderr.write(f"{parser.prog}: couldn't parse {from_fmt} input: {e}\n")
        return 1

    to_kwargs = {}
    if to_fmt in ("json", "xml"):
        to_kwargs["pretty"] = args.pretty
        if args.indent is not None:
            to_kwargs["indent"] = (
                int(args.indent) if to_fmt == "json" else args.indent
            )

    try:
        result = doc.to_format(to_fmt, **to_kwargs)
    except ImportError as e:
        sys.stderr.write(f"{parser.prog}: {e}\n")
        return 3

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
    else:
        sys.stdout.write(result)
        if not result.endswith("\n"):
            sys.stdout.write("\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
