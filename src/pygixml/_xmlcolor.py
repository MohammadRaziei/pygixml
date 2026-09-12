"""
pygixml._xmlcolor — a small regex-based XML syntax highlighter for
terminal output, used by ``pygixml cat``.

Design goal: this is a *display* helper, not a parser -- it only has
to look right on well-formed XML that pugixml already accepted, so a
handful of regexes covering tags/attrs/comments/CDATA/declaration is
enough (unlike jsonify, correctness here is cosmetic, not structural).

Colorization requires ``colorama`` (used for its ``Fore``/``Style``
ANSI codes and, on legacy Windows consoles, for making them actually
render). If colorama isn't installed, :func:`colorize_xml` just
returns the input unchanged -- no crash, no raw escape codes, plain
output, exactly like ``cat`` would show it.
"""

from __future__ import annotations

import re

try:
    import colorama
    HAVE_COLORAMA = True
except ImportError:
    HAVE_COLORAMA = False


_TAG_RE = re.compile(
    r'(?P<comment><!--.*?-->)'
    r'|(?P<cdata><!\[CDATA\[.*?\]\]>)'
    r'|(?P<decl><\?.*?\?>)'
    r'|(?P<doctype><!DOCTYPE[^>]*>)'
    r'|(?P<tag><\s*/?\s*[\w:.\-]+'
    r'(?:\s+[\w:.\-]+\s*=\s*(?:"[^"]*"|\'[^\']*\'))*'
    r'\s*/?\s*>)',
    re.DOTALL,
)

_ATTR_RE = re.compile(
    r'(?P<attrname>[\w:.\-]+)(?P<eq>\s*=\s*)(?P<value>"[^"]*"|\'[^\']*\')'
)

_TAG_SPLIT_RE = re.compile(
    r'^(<\s*/?\s*)([\w:.\-]+)(.*?)(\s*/?\s*>)$', re.DOTALL
)


def color_available() -> bool:
    """Whether colorization is possible at all (colorama installed)."""
    return HAVE_COLORAMA


def should_colorize(mode: str, stream) -> bool:
    """Resolve a --color {auto,always,never} choice against a stream.

    'auto' colorizes only when the stream is a real terminal --
    piping into a file or another program never gets raw escape codes.
    """
    if mode == "never":
        return False
    if mode == "always":
        return HAVE_COLORAMA
    # auto
    is_tty = bool(getattr(stream, "isatty", None) and stream.isatty())
    return HAVE_COLORAMA and is_tty


def colorize_xml(text: str, enabled: bool) -> str:
    """Return `text` with ANSI color codes for XML syntax, or `text`
    unchanged if `enabled` is False or colorama isn't installed."""
    if not enabled or not HAVE_COLORAMA:
        return text

    # We've already decided color is wanted -- don't let colorama's
    # own tty auto-detection second-guess that (it would strip codes
    # again when stdout isn't a real console, e.g. under test capture).
    colorama.init(strip=False)

    reset = colorama.Style.RESET_ALL
    c_tag = colorama.Fore.CYAN
    c_attr = colorama.Fore.YELLOW
    c_val = colorama.Fore.GREEN
    c_punct = colorama.Fore.WHITE + colorama.Style.DIM
    c_comment = colorama.Style.DIM
    c_cdata = colorama.Fore.MAGENTA
    c_decl = colorama.Style.DIM

    def colorize_tag(tag_text: str) -> str:
        m = _TAG_SPLIT_RE.match(tag_text)
        if not m:
            return tag_text
        open_punct, name, attrs, close_punct = m.groups()
        out = [c_punct + open_punct + reset, c_tag + name + reset]
        pos = 0
        for am in _ATTR_RE.finditer(attrs):
            gap = attrs[pos:am.start()]
            if gap:
                out.append(c_punct + gap + reset)
            out.append(c_attr + am.group("attrname") + reset)
            out.append(c_punct + am.group("eq") + reset)
            out.append(c_val + am.group("value") + reset)
            pos = am.end()
        tail = attrs[pos:]
        if tail:
            out.append(c_punct + tail + reset)
        out.append(c_punct + close_punct + reset)
        return "".join(out)

    parts = []
    pos = 0
    for m in _TAG_RE.finditer(text):
        parts.append(text[pos:m.start()])  # plain text content
        if m.group("comment"):
            parts.append(c_comment + m.group("comment") + reset)
        elif m.group("cdata"):
            parts.append(c_cdata + m.group("cdata") + reset)
        elif m.group("decl") or m.group("doctype"):
            parts.append(c_decl + m.group(0) + reset)
        else:
            parts.append(colorize_tag(m.group("tag")))
        pos = m.end()
    parts.append(text[pos:])
    return "".join(parts)
