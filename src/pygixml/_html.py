"""
pygixml._html: read real-world (messy) HTML by first normalising it to
well-formed XML, then handing that to the normal pugixml parser.

    >>> import pygixml
    >>> pygixml.html_to_xml("<ul><li>a<li>b<br></ul>")
    '<ul><li>a</li><li>b<br/></li></ul>'
    >>> doc = pygixml.parse_html("<p>one<p>two")      # -> XMLDocument
    >>> doc.select_nodes("//p")                       # XPath, objectify, ...

Because the intermediate form is plain XML text, everything pygixml
already does (XPath, ``objectify``, ``dictify``, ``jsonify``, streaming)
works on HTML with no extra code.

What it fixes: void tags (``<br>``), implicitly closed ``<p>``/``<li>``/
``<td>``/..., stray end tags, unclosed tags at EOF, valueless attributes,
duplicate attributes, entities such as ``&nbsp;``, ``<script>``/``<style>``
raw text, names XML would reject (``@click``, ``[prop]``, ``o:p``), comments that
contain ``--``, and fragments with several top-level nodes (wrapped in a
root element).

What it does NOT do: the full HTML5 tree-building algorithm. No implied
``<html>/<head>/<body>``, no browser-style table repair, and tag/attribute
names are lower-cased, so SVG's ``viewBox`` arrives as ``viewbox``. That
is fine for scraping and data extraction; if you need byte-for-byte
browser fidelity, use a spec-compliant parser.

The module is private (``_html``) on purpose: a public ``pygixml.html``
would shadow the stdlib ``html`` package whenever the package directory
ends up on ``sys.path``.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

from .pygixml_cy import parse_string

# ponytail: stdlib html.parser as the tokenizer, plus a tiny tree fixer.
# Upgrade path if speed matters: port this tokenizer to C++ behind the
# same html_to_xml() signature.

_VOID = frozenset(
    "area base br col embed hr img input link meta param source track wbr".split()
)

# Implied end tags. _RULES[new_tag] is a list of (targets, stops): walk the
# open-element stack from the top; the first element found in `targets`
# gets closed (together with everything above it), and the walk gives up
# on reaching an element in `stops` (so nested lists/tables are untouched).
_P = (("p",), frozenset(
    "applet caption html table td th marquee object template button".split()
))
_RULES = {
    t: (_P,)
    for t in (
        "address article aside blockquote center details dialog dir div dl "
        "fieldset figcaption figure footer form h1 h2 h3 h4 h5 h6 header "
        "hgroup hr main menu nav ol p pre search section summary table ul"
    ).split()
}
_TABLE = frozenset(("table",))
_ROW = frozenset(("tr", "table"))
_SELECT = frozenset(("select", "datalist"))
_RULES.update({
    "li": ((("li",), frozenset(("ul", "ol", "menu"))), _P),
    "dt": ((("dt", "dd"), frozenset(("dl",))), _P),
    "dd": ((("dt", "dd"), frozenset(("dl",))), _P),
    "tr": ((("tr",), _TABLE),),
    "td": ((("td", "th"), _ROW),),
    "th": ((("td", "th"), _ROW),),
    "thead": ((("thead", "tbody", "tfoot"), _TABLE),),
    "tbody": ((("thead", "tbody", "tfoot"), _TABLE),),
    "tfoot": ((("thead", "tbody", "tfoot"), _TABLE),),
    "option": ((("option",), _SELECT),),
    "optgroup": ((("optgroup",), _SELECT), (("option",), _SELECT)),
})

_BAD_CHARS = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]")
_BAD_NAME = re.compile(r"[^\w.\-]")   # ":" too: a bare prefix is a namespace error
_BAD_NAME_START = re.compile(r"[^A-Za-z_\u00c0-\uffff]")


def _name(raw: str) -> str:
    """Make a tag/attribute name acceptable to XML: ``@click`` -> ``_click``,
    ``o:p`` -> ``o_p`` (an unbound ``prefix:`` breaks namespace-aware parsers)."""
    n = _BAD_NAME.sub("_", raw)
    return "_" + n if _BAD_NAME_START.match(n[:1]) else n


def _esc(s: str, attr: bool = False) -> str:
    s = _BAD_CHARS.sub("", s)
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return s.replace('"', "&quot;") if attr else s


class _Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.stack: list[str] = []   # open elements (original, lower-case names)
        self.tops = 0                # top-level elements seen
        self.loose = False           # top-level non-blank text seen

    def pop_to(self, i: int) -> None:
        """Close open elements until only ``i`` of them remain."""
        while len(self.stack) > i:
            self.out.append(f"</{_name(self.stack.pop())}>")

    def handle_starttag(self, tag, attrs, empty=False):
        for targets, stops in _RULES.get(tag, ()):
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i] in targets:
                    self.pop_to(i)
                    break
                if self.stack[i] in stops:
                    break
        if not self.stack:
            self.tops += 1
        seen, parts = set(), []
        for k, v in attrs:
            k = _name(k)
            if k not in seen:        # HTML keeps the first duplicate
                seen.add(k)
                parts.append(f' {k}="{_esc(v or "", True)}"')
        closed = empty or tag in _VOID
        self.out.append(f"<{_name(tag)}{''.join(parts)}{'/>' if closed else '>'}")
        if not closed:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs, empty=True)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i] == tag:
                self.pop_to(i)
                return
        # stray end tag: ignored, as browsers do

    def handle_data(self, data):
        if self.stack:
            self.out.append(_esc(data))
        elif data.strip():
            self.loose = True
            self.out.append(_esc(data))
        # blank text between top-level nodes is dropped

    def handle_comment(self, data):
        data = re.sub("-(?=-)", "- ", _BAD_CHARS.sub("", data))   # no "--" in XML comments
        self.out.append(f"<!--{data} -->" if data.endswith("-") else f"<!--{data}-->")

    # doctype, <?processing instructions?> and CDATA markers: dropped.


def html_to_xml(html: str, root: str = "root") -> str:
    """Convert HTML (possibly malformed, possibly a fragment) to a
    well-formed XML string.

    Output has exactly one root element. If the input already has exactly
    one top-level element (typically ``<html>``) it is used as is;
    otherwise everything is wrapped in ``<root>`` (name configurable via
    *root*).
    """
    b = _Builder()
    b.feed(html)
    b.close()
    b.pop_to(0)
    body = "".join(b.out)
    if b.tops == 1 and not b.loose:
        return body
    root = _name(root)
    return f"<{root}>{body}</{root}>"


def parse_html(html: str, root: str = "root", options=0xFFFFFFFF):
    """Parse HTML into an :class:`~pygixml.XMLDocument` (see
    :func:`html_to_xml` for what is normalised and what is not).

    *options* are the usual :class:`~pygixml.ParseFlags`, applied when the
    normalised XML is parsed.
    """
    return parse_string(html_to_xml(html, root), options)
