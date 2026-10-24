"""
pygixml._html: read real-world (messy) HTML by first normalising it to
well-formed XML, then handing that to the normal pugixml parser.

    >>> import pygixml
    >>> pygixml.html_to_xml("<ul><li>a<li>b<br></ul>")
    '<ul><li>a</li><li>b<br/></li></ul>'
    >>> doc = pygixml.parse_html("<p>one<p>two")      # -> XMLDocument
    >>> doc.root.select_nodes("//p")                  # XPath, objectify, ...
    >>> pygixml.xml_to_html(doc, unwrap="root")       # ... and back to HTML
    '<p>one</p><p>two</p>'

Because the intermediate form is plain XML text, everything pygixml
already does (XPath, ``objectify``, ``dictify``, ``jsonify``, streaming)
works on HTML with no extra code.

What it fixes: void tags (``<br>``), implicitly closed ``<p>``/``<li>``/
``<td>``/..., stray end tags, unclosed tags at EOF, valueless attributes,
duplicate attributes, entities such as ``&nbsp;``, ``<script>``/``<style>``
raw text, names XML would reject (``@click``, ``[prop]``, ``o:p``; encoded
reversibly, see below), comments that
contain ``--``, and fragments with several top-level nodes (wrapped in a
root element).

Names XML rejects are encoded, not dropped, so :func:`xml_to_html` can
restore them: ``o:p`` -> ``o_colon_p``, ``@click`` -> ``_at_click``,
``[prop]`` -> ``_lbracket_prop_rbracket_``, and any other character ``c``
-> ``_x<hex>_`` (``1bad`` -> ``_x31_bad``). The one ambiguity: an original
name that already contains a literal ``_colon_`` or ``_at_`` decodes to the
character.

All failures raise :class:`PygiXMLHTMLError` (a :class:`PygiXMLError`).

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

from .pygixml_cy import (
    ParseFlags, PygiXMLError, XMLDocument, XMLNode, parse_string,
)


_KEEP_ALL = ParseFlags.DEFAULT | ParseFlags.WS_PCDATA | ParseFlags.COMMENTS


class PygiXMLHTMLError(PygiXMLError):
    """Raised by the HTML helpers: input that isn't a ``str``, a tokenizer
    failure (with line/column), normalised XML the parser rejects, a null or
    unsupported node passed to :func:`xml_to_html`, or a tree nested too
    deeply to serialize.  Subclass of :class:`PygiXMLError`.
    """

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

_FIRST_NL = frozenset(("pre", "textarea", "listing"))   # parsers eat a leading "\n"
_BAD_CHARS = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]")
_VALID_NAME = re.compile(r"[A-Za-z_\u00c0-\uffff][\w.\-]*")
_NAME_START = re.compile(r"[A-Za-z_\u00c0-\uffff]")
_NAME_CHAR = re.compile(r"[\w.\-]")
_CHAR_WORDS = {
    ":": "colon", "@": "at", "#": "hash", "[": "lbracket", "]": "rbracket",
    "(": "lparen", ")": "rparen", "*": "star", "+": "plus", "/": "slash",
}
_WORD_CHARS = {w: c for c, w in _CHAR_WORDS.items()}
_TOKEN = re.compile("_(" + "|".join(_WORD_CHARS) + "|x[0-9a-f]+)_")


def _name(raw: str) -> str:
    """Encode a tag/attribute name so XML accepts it, reversibly:
    ``o:p`` -> ``o_colon_p``, ``@click`` -> ``_at_click`` (an unbound
    ``prefix:`` would break namespace-aware parsers)."""
    if _VALID_NAME.fullmatch(raw):
        return raw
    out = []
    for i, ch in enumerate(raw):
        if (_NAME_START if i == 0 else _NAME_CHAR).match(ch):
            out.append(ch)
        elif ch in _CHAR_WORDS:
            out.append(f"_{_CHAR_WORDS[ch]}_")
        else:
            out.append(f"_x{ord(ch):x}_")
    return "".join(out)


def _unname(name: str) -> str:
    """Inverse of :func:`_name`."""
    if "_" not in name:
        return name
    return _TOKEN.sub(
        lambda m: _WORD_CHARS.get(m[1]) or chr(int(m[1][1:], 16)), name
    )


def _esc(s: str, attr: bool = False, keep_ws: bool = False) -> str:
    s = _BAD_CHARS.sub("", s)
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    if attr:
        s = s.replace('"', "&quot;")
        if not keep_ws:   # XML parsers turn raw \n \r \t in attributes into spaces
            s = s.replace("\n", "&#10;").replace("\r", "&#13;").replace("\t", "&#9;")
    return s


def _comment(data: str) -> str:
    data = re.sub("-(?=-)", "- ", _BAD_CHARS.sub("", data))   # no "--" in XML comments
    return f"<!--{data} -->" if data.endswith("-") else f"<!--{data}-->"


class _Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.stack: list[str] = []   # open elements (original, lower-case names)
        self.tops = 0                # top-level elements seen
        self.loose = False           # top-level non-blank text seen
        self.skip_nl = False         # just opened <pre>/<textarea>: eat one "\n"

    def pop_to(self, i: int) -> None:
        """Close open elements until only ``i`` of them remain."""
        while len(self.stack) > i:
            self.out.append(f"</{_name(self.stack.pop())}>")

    def handle_starttag(self, tag, attrs, empty=False):
        self.skip_nl = False
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
            self.skip_nl = tag in _FIRST_NL

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs, empty=True)

    def handle_endtag(self, tag):
        self.skip_nl = False
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i] == tag:
                self.pop_to(i)
                return
        # stray end tag: ignored, as browsers do

    def handle_data(self, data):
        if self.skip_nl:             # the HTML spec drops it; xml_to_html re-adds it
            self.skip_nl = False
            data = data[1:] if data.startswith("\n") else data
        if self.stack:
            self.out.append(_esc(data))
        elif data.strip():
            self.loose = True
            self.out.append(_esc(data))
        # blank text between top-level nodes is dropped

    def handle_comment(self, data):
        self.out.append(_comment(data))

    # doctype, <?processing instructions?> and CDATA markers: dropped.


def html_to_xml(html: str, root: str = "root") -> str:
    """Convert HTML (possibly malformed, possibly a fragment) to a
    well-formed XML string.

    Output has exactly one root element. If the input already has exactly
    one top-level element (typically ``<html>``) it is used as is;
    otherwise everything is wrapped in ``<root>`` (name configurable via
    *root*).

    Raises:
        PygiXMLHTMLError: *html* isn't a ``str`` (decode bytes first), or
            the tokenizer failed (message includes line and column).
    """
    if not isinstance(html, str):
        raise PygiXMLHTMLError(
            f"html must be str, not {type(html).__name__} (decode bytes first)"
        )
    b = _Builder()
    try:
        b.feed(html)
        b.close()
    except Exception as e:
        line, col = b.getpos()
        raise PygiXMLHTMLError(
            f"couldn't tokenize HTML near line {line}, column {col}: {e}"
        ) from e
    b.pop_to(0)
    body = "".join(b.out)
    if b.tops == 1 and not b.loose:
        return body
    root = _name(root)
    return f"<{root}>{body}</{root}>"


def parse_html(html: str, root: str = "root", options=None):
    """Parse HTML into an :class:`~pygixml.XMLDocument` (see
    :func:`html_to_xml` for what is normalised and what is not).

    *options* are the usual :class:`~pygixml.ParseFlags`. The default keeps
    whitespace-only text and comments (``DEFAULT | WS_PCDATA | COMMENTS``):
    in HTML the space in ``<b>a</b> <i>b</i>`` is content, and dropping
    comments would make :func:`xml_to_html` lose them (conditional comments,
    for one).

    Raises:
        PygiXMLHTMLError: see :func:`html_to_xml`; also if the normalised
            XML is rejected by the XML parser.
    """
    if options is None:
        options = _KEEP_ALL
    xml = html_to_xml(html, root)
    try:
        return parse_string(xml, options)
    except PygiXMLError as e:
        raise PygiXMLHTMLError(
            f"normalised HTML was rejected by the XML parser: {e}"
        ) from e


# ---------------------------------------------------------------- XML -> HTML

_RAW = frozenset(("script", "style"))                      # text is not escaped
_VERBATIM = frozenset(("pre", "textarea", "script", "style"))   # never re-indented
_INLINE = frozenset((
    "a abbr b bdi bdo br button cite code data del dfn em i img input ins kbd "
    "label mark q s samp select small span strong sub sup textarea time u var wbr"
).split())
_SCRIPT_END = re.compile(r"</(?=(?:script|style))", re.I)


def _kids(node):
    out, k = [], node.first_child()
    while k:
        out.append(k)
        k = k.next_sibling
    return out


def _emit(node, out, pretty, indent, depth):
    t = node.type
    if t == "comment":
        out.append(_comment(node.value or ""))
    elif t in ("pcdata", "cdata"):
        out.append(_esc(node.value or ""))
    elif t == "element":
        tag = _unname(node.name)
        low = tag.lower()
        out.append("<" + tag)
        a = node.first_attribute()
        while a:
            out.append(f' {_unname(a.name)}="{_esc(a.value or "", True, True)}"')
            a = a.next_attribute
        out.append(">")
        if low in _VOID:                  # void: HTML forbids content and end tag
            return
        kids = _kids(node)
        if low in _RAW:                   # script/style: raw text, but can't close early
            out.append(_SCRIPT_END.sub(r"<\\/", _BAD_CHARS.sub("", "".join(
                k.value or "" for k in kids if k.type in ("pcdata", "cdata")))))
        else:
            first = kids[0] if kids else None
            if low in _FIRST_NL and first is not None and (first.value or "").startswith("\n"):
                out.append("\n")
            block = pretty and kids and low not in _VERBATIM and low not in _INLINE and all(
                (k.type == "element" and _unname(k.name).lower() not in _INLINE)
                or k.type == "comment"
                or (k.type in ("pcdata", "cdata") and not (k.value or "").strip())
                for k in kids
            )
            for k in kids:
                if block:
                    if k.type in ("pcdata", "cdata"):
                        continue          # whitespace between blocks: re-indented instead
                    out.append("\n" + indent * (depth + 1))
                _emit(k, out, block, indent, depth + 1)
            if block:
                out.append("\n" + indent * depth)
        out.append(f"</{tag}>")
    # doctype, <?pi?>, declarations: dropped


def xml_to_html(node, pretty: bool = False, indent: str = "  ",
                doctype: bool = False, unwrap: str | None = None) -> str:
    """Serialize an XML node or document as HTML (the inverse of
    :func:`parse_html`, not of :func:`html_to_xml`'s exact text).

    Unlike ``to_string()`` this follows HTML rules: void tags are written
    ``<br>``, empty elements ``<div></div>`` (never ``<div/>``, which a
    browser reads as an open tag), ``<script>``/``<style>`` contents are
    not escaped, and names encoded by :func:`html_to_xml` are restored
    (``o_colon_p`` -> ``o:p``).

    Args:
        node: an :class:`XMLNode` or :class:`XMLDocument`.
        pretty: indent block-level structure. Inline elements, text and
            ``<pre>``/``<textarea>``/``<script>``/``<style>`` are never
            re-indented, so rendering doesn't change.
        indent: indentation unit when *pretty*.
        doctype: prepend ``<!DOCTYPE html>``.
        unwrap: if the top-level element has this name (typically the
            ``"root"`` that :func:`html_to_xml` adds around fragments),
            emit only its children.

    Raises:
        PygiXMLHTMLError: *node* isn't a node/document, is null, or the tree
            is nested too deeply.
    """
    if isinstance(node, XMLDocument):
        tops = _kids(node)
    elif isinstance(node, XMLNode):
        if node.type == "null":
            raise PygiXMLHTMLError("can't serialize a null node")
        tops = _kids(node) if node.type == "document" else [node]
    else:
        raise PygiXMLHTMLError(
            f"expected XMLNode or XMLDocument, not {type(node).__name__}"
        )
    if unwrap is not None:
        elems = [t for t in tops if t.type == "element"]
        if len(elems) == 1 and elems[0].name == unwrap:
            tops = _kids(elems[0])
    parts = []
    try:
        for t in tops:
            if pretty and parts:
                parts.append("\n")
            _emit(t, parts, pretty, indent, 0)
    except RecursionError as e:
        raise PygiXMLHTMLError("document is nested too deeply to serialize") from e
    return ("<!DOCTYPE html>" + ("\n" if pretty else "") if doctype else "") + "".join(parts)
