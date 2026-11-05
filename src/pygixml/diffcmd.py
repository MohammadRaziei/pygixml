"""
pygixml.diffcmd: compare two XML / HTML files from the shell.

Usage::

    pygixml diff A B [OPTIONS]          # the edit script that turns A into B
    pygixml similarity A B [OPTIONS]    # structural similarity, 0..1

A and B are XML or HTML files; the format comes from the extension
(.xml, .html, .htm) or --from. Use "-" for one of them to read stdin.

Examples::

    pygixml diff old.html new.html
    pygixml diff old.xml new.xml --text-diff --ignore-attrs 'data-*'
    pygixml diff a.xml b.xml --json | jq '.[] | select(.action == "Delete")'
    pygixml diff a.html b.html --quiet && echo "same"       # exit 1 when they differ
    pygixml similarity page1.html page2.html                # 0.889
    pygixml similarity a.html b.html --content --method paths

Exit codes of ``diff``: 0 = done (and, with --exit-code or --quiet, no
differences), 1 = differences found (only with --exit-code / --quiet),
2 = trouble (unreadable file, input that does not parse, bad option).
``similarity`` returns 0, or 2 on trouble.

Both load the two documents in memory, like ``pygixml query``.
"""

from __future__ import annotations

import argparse
import json
import sys

import pygixml
from pygixml import PygiXMLError
from pygixml.convertcmd import _guess_format


def _common(p: argparse.ArgumentParser) -> None:
    p.add_argument("a", metavar="A", help='First file, or "-" for stdin.')
    p.add_argument("b", metavar="B", help='Second file, or "-" for stdin.')
    p.add_argument(
        "--from", dest="from_fmt", choices=("xml", "html"), default=None,
        help="Input format of both files; by default each is guessed from its extension.",
    )
    p.add_argument(
        "--case", choices=("lower", "keep", "escape"), default="lower",
        help="HTML input only: how tag and attribute names are written "
             "(see pygixml.html_to_xml).",
    )
    p.add_argument(
        "--ignore-attrs", action="append", default=[], metavar="NAME",
        help="Attribute to ignore; 'data-*' is a prefix. Repeat for several.",
    )
    p.add_argument("--keep-whitespace", action="store_true",
                   help="Compare blank text and whitespace runs as they are.")
    p.add_argument("--keep-comments", action="store_true", help="Compare comments too.")
    p.add_argument("--no-class-set", action="store_true",
                   help='Compare class="b a" and class="a b" as different.')


def _options(args) -> dict:
    return dict(
        ignore_whitespace=not args.keep_whitespace,
        ignore_comments=not args.keep_comments,
        ignore_attrs=tuple(args.ignore_attrs),
        class_as_set=not args.no_class_set,
    )


def _load(path: str, args, parser):
    fmt = args.from_fmt or (None if path == "-" else _guess_format(path))
    if fmt not in ("xml", "html"):
        parser.error(f"can't tell whether {path!r} is XML or HTML -- pass --from xml|html")
    if path == "-":
        text = sys.stdin.read()
    else:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    if fmt == "html":
        return pygixml.parse_html(text, case=args.case)
    flags = pygixml.ParseFlags
    return pygixml.parse_string(text, flags.DEFAULT | flags.WS_PCDATA | flags.COMMENTS)


def _load_both(args, parser):
    if args.a == "-" and args.b == "-":
        parser.error('only one of A and B can be "-" (stdin)')
    return _load(args.a, args, parser), _load(args.b, args, parser)


def _utf8_stdout() -> None:
    """Write UTF-8 whatever the locale says. A Windows pipe is cp1252 by default, and the
    paths, text and attribute values in a diff may be in any script."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def _q(s) -> str:
    return json.dumps(s, ensure_ascii=False)


def _word_diff(pieces) -> str:
    """[(0, 'keep'), (-1, 'gone'), (1, 'new')] -> keep[-gone-]{+new+}"""
    mark = {0: "{}", -1: "[-{}-]", 1: "{{+{}+}}"}
    return "".join(mark[op].format(piece) for op, piece in pieces)


def _line(act) -> str:
    kind = type(act).__name__
    if kind == "Insert":
        return f"insert   {act.parent} @{act.position}  {act.xml}"
    if kind == "InsertText":
        return f"insert   {act.parent} @{act.position}  {_q(act.text)}"
    if kind == "Delete":
        return f"delete   {act.path}"
    if kind == "Move":
        return f"move     {act.path} -> {act.parent} @{act.position}"
    if kind == "UpdateText":
        what = _word_diff(act.diff) if act.diff else f"{_q(act.old)} -> {_q(act.text)}"
        return f"update   {act.path}  {what}"
    if kind == "SetAttrib":
        was = "" if act.old is None else f"  (was {_q(act.old)})"
        return f"set      {act.path} {act.name}={_q(act.value)}{was}"
    return f"unset    {act.path} {act.name}  (was {_q(act.old)})"      # DeleteAttrib


def _fail(parser, e) -> int:
    sys.stderr.write(f"{parser.prog}: {e}\n")
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pygixml diff",
        description="Edit script that turns A into B (XML or HTML files).",
    )
    _common(parser)
    parser.add_argument("--json", action="store_true",
                        help='Print the actions as a JSON list ({"action": "Insert", ...}).')
    parser.add_argument("--text-diff", action="store_true",
                        help="Show changed text as a word-level diff: keep[-gone-]{+new+}.")
    parser.add_argument("--key", action="append", default=None, metavar="ATTR",
                        help="Attribute that identifies an element wherever it sits "
                             "(default: id). Repeat for several.")
    parser.add_argument("--no-moves", action="store_true",
                        help="Do not pair subtrees across parents (no Move actions).")
    parser.add_argument("--exit-code", action="store_true",
                        help="Exit with 1 when the documents differ.")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Print nothing; exit 0 when equal, 1 when they differ.")
    args = parser.parse_args(argv)
    _utf8_stdout()

    try:
        a, b = _load_both(args, parser)
        opts = _options(args)
        if args.quiet:
            return 0 if pygixml.is_equal(a, b, **opts) else 1
        actions = pygixml.diff(
            a, b, keys=tuple(args.key) if args.key else ("id",), moves=not args.no_moves,
            text_diff=args.text_diff or args.json, **opts)
    except (PygiXMLError, OSError, UnicodeDecodeError) as e:
        return _fail(parser, e)

    if args.json:
        out = [{"action": type(x).__name__, **x._asdict()} for x in actions]
        sys.stdout.write(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    else:
        for act in actions:
            sys.stdout.write(_line(act).replace("\n", "\\n") + "\n")
    return 1 if actions and args.exit_code else 0


def similarity_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pygixml similarity",
        description="Structural similarity of two XML or HTML files, 0 (nothing shared) to 1.",
    )
    _common(parser)
    parser.add_argument("--method", choices=("pqgram", "paths"), default="pqgram",
                        help="pqgram (default) or paths (cruder and cheaper).")
    parser.add_argument("--content", action="store_true",
                        help="Let text count too; by default only the structure does.")
    args = parser.parse_args(argv)
    _utf8_stdout()

    try:
        a, b = _load_both(args, parser)
        score = pygixml.similarity(a, b, method=args.method, content=args.content, **_options(args))
    except (PygiXMLError, OSError, UnicodeDecodeError) as e:
        return _fail(parser, e)
    sys.stdout.write(f"{score:.3f}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
