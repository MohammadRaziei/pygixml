"""
pygixml.jsoncmd — command-line XML -> JSON converter.

Usage::

    pygixml jsonify [OPTIONS] FILE     # `json` also works, as a short alias
    python -m pygixml jsonify [OPTIONS] FILE

Examples::

    pygixml jsonify data.xml                       # print JSON to stdout
    pygixml jsonify data.xml -p                    # pretty-printed
    pygixml jsonify data.xml -o data.json          # write to a file
    pygixml jsonify big.xml -o big.json --stream   # force streaming mode
    pygixml jsonify huge.xml -o huge.json          # auto-streams: huge.xml
                                                    # is over the size threshold
    cat data.xml | pygixml jsonify -               # read from stdin
    pygixml jsonify data.xml --force-list item     # always make <item> a list

Streaming mode (used automatically for files over ~64MB, or with
--stream) calls :func:`pygixml.jsonify.stream_dump`, which holds only a
small fixed-size scratch buffer in memory regardless of input size --
see the module docstring in ``jsonify.pxi`` for the complexity
characteristics (O(n) time / O(1) memory for the common case of one
repeated tag per nesting level; a rarer interleaved-siblings shape can
cost more time, never more memory). Non-streaming mode builds a full
in-memory DOM first (:func:`pygixml.jsonify.dumps_file`), which is
fine for small/medium files and slightly faster.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile


STREAM_THRESHOLD_BYTES = 64 * 1024 * 1024  # 64MB


def _non_negative_int(s: str) -> int:
    n = int(s)
    if n < 0:
        raise argparse.ArgumentTypeError(f"must be >= 0, got {n}")
    return n


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Convert an XML file to JSON.",
    )
    p.add_argument(
        "file",
        metavar="FILE",
        help='XML file to convert. Use "-" to read from stdin.',
    )
    p.add_argument(
        "--output", "-o",
        metavar="PATH",
        default=None,
        help="Write JSON here instead of stdout.",
    )
    p.add_argument(
        "--pretty", "-p",
        action="store_true",
        default=False,
        help="Pretty-print with 2-space indent (default: compact).",
    )
    p.add_argument(
        "--indent",
        type=_non_negative_int,
        default=None,
        metavar="N",
        help="Pretty-print with N-space indent (implies --pretty).",
    )
    p.add_argument(
        "--force-list",
        action="append",
        default=None,
        metavar="TAG",
        dest="force_list",
        help="Always serialize this child tag as a list, even with a "
             "single occurrence. Repeatable.",
    )
    p.add_argument(
        "--attr-prefix",
        default="@",
        metavar="STR",
        help='Prefix for attribute keys (default: "@").',
    )
    p.add_argument(
        "--cdata-key",
        default="#text",
        metavar="STR",
        help='Key for mixed text content (default: "#text").',
    )
    p.add_argument(
        "--stream",
        action="store_true",
        default=False,
        help=f"Force streaming mode (auto-enabled above "
             f"{STREAM_THRESHOLD_BYTES // (1024*1024)}MB already).",
    )
    p.add_argument(
        "--no-stream",
        action="store_true",
        default=False,
        help="Force the in-memory (DOM) mode even for large files.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    import pygixml
    from pygixml import jsonify

    args = _build_parser().parse_args(argv)
    indent = args.indent if args.indent is not None else (2 if args.pretty else 0)
    force_list = set(args.force_list) if args.force_list else None

    tmp_input = None
    try:
        source = args.file
        if source == "-":
            tmp_input = tempfile.NamedTemporaryFile(suffix=".xml", delete=False)
            shutil.copyfileobj(sys.stdin.buffer, tmp_input)
            tmp_input.close()
            source = tmp_input.name

        size = os.path.getsize(source)
        use_stream = args.stream or (size > STREAM_THRESHOLD_BYTES and not args.no_stream)

        kwargs = dict(force_list=force_list, attr_prefix=args.attr_prefix,
                      cdata_key=args.cdata_key)

        if args.output:
            if use_stream:
                jsonify.stream_dump(source, args.output, indent=indent, **kwargs)
            else:
                text = jsonify.dumps_file(source, pretty=bool(indent),
                                           indent=" " * indent if indent else "\t",
                                           **kwargs)
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(text)
        else:
            if use_stream:
                tmp_out = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
                tmp_out.close()
                try:
                    jsonify.stream_dump(source, tmp_out.name, indent=indent, **kwargs)
                    with open(tmp_out.name, "rb") as f:
                        shutil.copyfileobj(f, sys.stdout.buffer)
                finally:
                    os.unlink(tmp_out.name)
            else:
                text = jsonify.dumps_file(source, pretty=bool(indent),
                                           indent=" " * indent if indent else "\t",
                                           **kwargs)
                sys.stdout.write(text)
                if not text.endswith("\n"):
                    sys.stdout.write("\n")
    finally:
        if tmp_input is not None:
            os.unlink(tmp_input.name)

    return 0


if __name__ == "__main__":
    sys.exit(main())
