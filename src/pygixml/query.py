"""
pygixml.query — command-line XML query tool.

Supports two query syntaxes:

  XPath   (default when query starts with / or //)
  Dotted  (objectify-style when query starts with .)

Usage::

    # As a module
    python -m pygixml.query [OPTIONS] FILE QUERY

    # As a CLI (after pip install)
    pygixml-query [OPTIONS] FILE QUERY

Examples::

    pygixml-query data.xml "//user-profile[@id='101']/first_name"
    pygixml-query data.xml ".database.user_profile.first_name"
    pygixml-query data.xml ".database.entry[1]"
    pygixml-query data.xml ".database.user_profile.@id"
    pygixml-query data.xml ".database.entry[*]"

    # Output formats
    pygixml-query data.xml ".database" --format xml
    pygixml-query data.xml ".database" --format json
    pygixml-query data.xml ".database" --format json --pretty

    # From stdin
    cat data.xml | pygixml-query - ".database.user_profile.first_name"

    # Multiple files
    pygixml-query *.xml ".config.host"
"""

from __future__ import annotations

import argparse
import sys
import os
from typing import Iterator


# ---------------------------------------------------------------------------
# Dotted query parser
# ---------------------------------------------------------------------------

def _parse_dotted(query: str) -> list:
    """Parse a dotted query string into a list of steps.

    Each step is one of:
      ('child',  'tag_name')       — child element
      ('attr',   'attr_name')      — attribute (prefixed with @)
      ('index',  int)              — [N] indexing (0-based)
      ('all',    None)             — [*] all siblings
      ('text',   None)             — text() content

    Example:
      ".database.user_profile.@id"
      → [('child','database'), ('child','user_profile'), ('attr','id')]

      ".database.entry[1]"
      → [('child','database'), ('child','entry'), ('index', 1)]
    """
    if not query.startswith("."):
        raise ValueError(f"Dotted query must start with '.', got {query!r}")

    steps = []
    # strip leading dot and split on '.' — but preserve [n] suffixes
    parts = query[1:].split(".")
    for part in parts:
        if not part:
            continue
        # check for index suffix: tag[N] or tag[*]
        if "[" in part:
            name, bracket = part.split("[", 1)
            bracket = bracket.rstrip("]")
            if name:
                steps.append(("child", name))
            if bracket == "*":
                steps.append(("all", None))
            else:
                steps.append(("index", int(bracket)))
        elif part.startswith("@"):
            steps.append(("attr", part[1:]))
        elif part == "text()":
            steps.append(("text", None))
        else:
            steps.append(("child", part))
    return steps


# ---------------------------------------------------------------------------
# Dotted query executor
# ---------------------------------------------------------------------------

def _execute_dotted(root, steps: list) -> list:
    """Execute parsed dotted steps against an ObjectifiedElement root.

    Returns a flat list of results — each item is either:
      - an ObjectifiedElement (for child/all steps)
      - a scalar (str/int/float/bool) for @attr or text() steps
    """
    from pygixml.objectify import ObjectifiedElement, NodeSequence

    current = [root]

    for kind, value in steps:
        next_nodes = []

        for node in current:
            if not isinstance(node, ObjectifiedElement):
                continue

            if kind == "child":
                try:
                    result = getattr(node, value)
                    if isinstance(result, NodeSequence):
                        next_nodes.extend(result)
                    else:
                        next_nodes.append(result)
                except AttributeError:
                    pass

            elif kind == "attr":
                val = node.get(value)
                if val is not None:
                    next_nodes.append(val)

            elif kind == "text":
                text = str(node)
                if text:
                    next_nodes.append(text)

            elif kind == "index":
                try:
                    result = getattr(node, _last_child_name(node))
                    if isinstance(result, NodeSequence):
                        next_nodes.append(result[value])
                    else:
                        if value == 0:
                            next_nodes.append(result)
                except (AttributeError, IndexError):
                    pass

            elif kind == "all":
                # collect all children regardless of tag
                for child in node:
                    next_nodes.append(child)

        current = next_nodes

    return current


def _last_child_name(node) -> str:
    """Return the tag name of the last accessed child — used for [N] indexing.

    Since we process steps sequentially, the index step follows a child step,
    so we re-access via the tag collected in the previous step.
    This is handled by keeping track in _execute_dotted_tracked below.
    """
    return ""


def _execute_dotted_tracked(root, steps: list) -> list:
    """Execute dotted steps with proper index handling."""
    from pygixml.objectify import ObjectifiedElement, NodeSequence

    current = [root]
    last_tag = None

    for kind, value in steps:
        next_nodes = []

        if kind == "child":
            last_tag = value
            for node in current:
                if not isinstance(node, ObjectifiedElement):
                    continue
                try:
                    result = getattr(node, value)
                    if isinstance(result, NodeSequence):
                        next_nodes.extend(result)
                    else:
                        next_nodes.append(result)
                except AttributeError:
                    pass

        elif kind == "index":
            # re-group current into sequences per parent and pick [value]
            # current already contains all siblings from prev child step
            try:
                if value < 0:
                    next_nodes.append(current[value])
                else:
                    next_nodes.append(current[value])
            except IndexError:
                pass

        elif kind == "all":
            next_nodes = list(current)

        elif kind == "attr":
            for node in current:
                if isinstance(node, ObjectifiedElement):
                    val = node.get(value)
                    if val is not None:
                        next_nodes.append(val)

        elif kind == "text":
            for node in current:
                if isinstance(node, ObjectifiedElement):
                    text = str(node)
                    if text:
                        next_nodes.append(text)

        current = next_nodes

    return current


# ---------------------------------------------------------------------------
# XPath query executor
# ---------------------------------------------------------------------------

def _execute_xpath(doc, query: str) -> list:
    """Execute an XPath query and return a list of results."""
    root = doc.root
    nodes = root.select_nodes(query)
    results = []
    for xpath_node in nodes:
        node = xpath_node.node
        if node:
            results.append(node)
    return results


# ---------------------------------------------------------------------------
# Result formatting
# ---------------------------------------------------------------------------

def _format_result(result, fmt: str, pretty: bool) -> str:
    """Format a single result as a string."""
    from pygixml.objectify import ObjectifiedElement
    import pygixml

    # scalar value (attr or text)
    if not isinstance(result, (ObjectifiedElement, pygixml.XMLNode)):
        return str(result)

    if fmt == "xml":
        if isinstance(result, ObjectifiedElement):
            return result.xml
        else:
            return result.to_string()

    elif fmt == "json":
        from pygixml import jsonify
        if isinstance(result, ObjectifiedElement):
            s = jsonify.dumps_obj(result, pretty=pretty)
        else:
            s = jsonify.dumps_node(result, pretty=pretty)
        return s

    elif fmt == "text":
        if isinstance(result, ObjectifiedElement):
            return str(result)
        else:
            return result.text() or ""

    elif fmt == "value":
        if isinstance(result, ObjectifiedElement):
            val = result()
            return str(val) if val is not None else ""
        else:
            return result.text() or ""

    return str(result)


# ---------------------------------------------------------------------------
# Core query function (importable as Python API)
# ---------------------------------------------------------------------------

def query(
    source: str,
    q: str,
    *,
    fmt: str = "value",
    pretty: bool = False,
    encoding: str = "utf-8",
) -> list:
    """Query an XML source with XPath or dotted notation.

    Args:
        source (str): XML file path, ``"-"`` for stdin, or XML string.
        q (str): Query — XPath (starting with ``/``) or dotted
            (starting with ``.``).
        fmt (str): Output format — ``"value"`` (default), ``"xml"``,
            ``"json"``, ``"text"``.
        pretty (bool): Pretty-print JSON or XML output.
        encoding (str): File encoding. Default ``"utf-8"``.

    Returns:
        list: Query results as formatted strings.

    Example::

        from pygixml.query import query

        results = query("data.xml", ".database.user_profile.first_name")
        results = query("data.xml", "//first_name", fmt="xml")
        results = query("<root><x>1</x></root>", ".root.x")
    """
    import pygixml
    from pygixml import objectify

    # --- load document ---
    if source == "-":
        xml_str = sys.stdin.read()
        doc = pygixml.parse_string(xml_str)
        root = objectify.from_string(xml_str)
    elif source.lstrip().startswith("<"):
        doc = pygixml.parse_string(source)
        root = objectify.from_string(source)
    else:
        doc = pygixml.parse_file(source)
        root = objectify.from_file(source)

    # --- execute query ---
    if q.startswith("."):
        steps = _parse_dotted(q)
        raw_results = _execute_dotted_tracked(root, steps)
    elif q.startswith("/") or q.startswith("//"):
        raw_results = _execute_xpath(doc, q)
    else:
        # try as XPath anyway
        raw_results = _execute_xpath(doc, q)

    # --- format results ---
    return [_format_result(r, fmt, pretty) for r in raw_results]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pygixml-query",
        description=(
            "Query XML files using XPath or dotted objectify-style notation.\n\n"
            "Query syntax:\n"
            "  XPath:  starts with /  e.g.  //user-profile[@id='101']\n"
            "  Dotted: starts with .  e.g.  .database.user_profile.first_name\n\n"
            "Dotted notation:\n"
            "  .root.child          child element\n"
            "  .root.child.@attr    attribute value\n"
            "  .root.items[0]       first sibling\n"
            "  .root.items[-1]      last sibling\n"
            "  .root.items[*]       all siblings\n"
            "  .root.child.text()   text content\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "files",
        nargs="+",
        metavar="FILE",
        help='XML file(s) to query. Use "-" to read from stdin.',
    )
    p.add_argument(
        "query",
        metavar="QUERY",
        help="XPath or dotted query string.",
    )
    p.add_argument(
        "--format", "-f",
        choices=["value", "text", "xml", "json"],
        default="value",
        dest="fmt",
        help=(
            "Output format: value (type-inferred scalar, default), "
            "text (raw string), xml (serialised XML), json (JSON string)."
        ),
    )
    p.add_argument(
        "--pretty", "-p",
        action="store_true",
        default=False,
        help="Pretty-print XML or JSON output.",
    )
    p.add_argument(
        "--separator", "-s",
        default="\n",
        metavar="SEP",
        help="Separator between results (default: newline).",
    )
    p.add_argument(
        "--null", "-0",
        action="store_true",
        default=False,
        help="Separate results with NUL byte (for xargs -0).",
    )
    p.add_argument(
        "--count", "-c",
        action="store_true",
        default=False,
        help="Print the number of results instead of results.",
    )
    p.add_argument(
        "--encoding", "-e",
        default="utf-8",
        metavar="ENC",
        help="File encoding (default: utf-8).",
    )
    p.add_argument(
        "--quiet", "-q",
        action="store_true",
        default=False,
        help="Suppress errors — exit 1 on no results, 0 on match.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()

    # Special case: last positional is the query, rest are files.
    # argparse can't do this natively — we split manually.
    args = parser.parse_args(argv)

    # The last positional is the query; everything before it is files.
    all_positional = args.files
    if len(all_positional) < 2:
        parser.error("Must provide at least one FILE and a QUERY.")

    files = all_positional[:-1]
    q     = all_positional[-1]

    sep = "\0" if args.null else args.separator
    total = 0
    exit_code = 0

    for path in files:
        try:
            results = query(
                path, q,
                fmt=args.fmt,
                pretty=args.pretty,
                encoding=args.encoding,
            )
        except Exception as e:
            if not args.quiet:
                print(f"pygixml-query: {path}: {e}", file=sys.stderr)
            exit_code = 1
            continue

        if args.count:
            total += len(results)
        else:
            if results:
                print(sep.join(str(r) for r in results))
            elif not args.quiet:
                exit_code = 1   # no match = exit 1 like grep

    if args.count:
        print(total)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())