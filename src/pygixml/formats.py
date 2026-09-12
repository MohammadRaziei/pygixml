"""
pygixml.formats — convert structured data between XML, JSON, YAML, and
TOON, all through one common representation: a plain Python dict, in
the same shape :func:`pygixml.dictify.parse` produces (``@attr`` /
``#text`` / repeated-siblings-as-list).

:class:`FormatDocument` wraps that dict. Each ``to_*``/``from_*``
method imports its own (optional) dependency right where it's used --
not at module import time -- so importing ``pygixml.formats`` never
fails just because you don't have PyYAML or ctoon installed; you only
pay for the format you actually use, and only find out about a
missing package when you try to use it, with a clear ``pip install``
instruction.

    json   -- stdlib, always available
    xml    -- pygixml.dictify, always available (this package)
    yaml   -- needs PyYAML  (pip install PyYAML)
    toon   -- needs ctoon   (pip install ctoon)

Example::

    from pygixml.formats import FormatDocument

    doc = FormatDocument.from_xml(open("data.xml").read())
    open("data.yaml", "w").write(doc.to_yaml())
    open("data.toon", "w").write(doc.to_toon())
"""

from __future__ import annotations

FORMATS = ("json", "xml", "yaml", "toon")


def _missing(package: str, pip_name: str, format_name: str) -> ImportError:
    return ImportError(
        f"{format_name} support needs the '{package}' package, which isn't "
        f"installed. Install it with: pip install {pip_name}"
    )


class FormatDocument:
    """A parsed document, held as a plain dict, convertible to/from
    JSON, XML, YAML, or TOON."""

    def __init__(self, data):
        self.data = data

    def __repr__(self):
        return f"FormatDocument({self.data!r})"

    def __eq__(self, other):
        if isinstance(other, FormatDocument):
            return self.data == other.data
        return NotImplemented

    # ----------------------------------------------------------- JSON --

    def to_json(self, pretty: bool = False, indent: int = 2) -> str:
        import json
        return json.dumps(
            self.data,
            indent=indent if pretty else None,
            ensure_ascii=False,
        )

    @classmethod
    def from_json(cls, text: str) -> "FormatDocument":
        import json
        return cls(json.loads(text))

    # ------------------------------------------------------------ XML --

    def to_xml(self, pretty: bool = False, indent: str = "  ",
               root_tag: str = "root", **kwargs) -> str:
        from pygixml import dictify
        data = self.data
        if not (isinstance(data, dict) and len(data) == 1):
            # dictify.unparse requires exactly one {root_tag: value} key;
            # JSON/YAML/TOON have no such constraint, so wrap if needed.
            data = {root_tag: data}
        return dictify.unparse(data, pretty=pretty, indent=indent, **kwargs)

    @classmethod
    def from_xml(cls, text: str, **kwargs) -> "FormatDocument":
        from pygixml import dictify
        return cls(dictify.parse(text, **kwargs))

    # ----------------------------------------------------------- YAML --

    def to_yaml(self, **kwargs) -> str:
        try:
            import yaml
        except ImportError:
            raise _missing("PyYAML", "PyYAML", "YAML") from None
        kwargs.setdefault("allow_unicode", True)
        kwargs.setdefault("sort_keys", False)
        return yaml.safe_dump(self.data, **kwargs)

    @classmethod
    def from_yaml(cls, text: str) -> "FormatDocument":
        try:
            import yaml
        except ImportError:
            raise _missing("PyYAML", "PyYAML", "YAML") from None
        return cls(yaml.safe_load(text))

    # ----------------------------------------------------------- TOON --

    def to_toon(self, **kwargs) -> str:
        try:
            import ctoon
        except ImportError:
            raise _missing("ctoon", "ctoon", "TOON") from None
        return ctoon.dumps(self.data, **kwargs)

    @classmethod
    def from_toon(cls, text: str) -> "FormatDocument":
        try:
            import ctoon
        except ImportError:
            raise _missing("ctoon", "ctoon", "TOON") from None
        return cls(ctoon.loads(text))

    # --------------------------------------------------------- generic --

    @classmethod
    def from_format(cls, text: str, fmt: str, **kwargs) -> "FormatDocument":
        try:
            method = getattr(cls, f"from_{fmt}")
        except AttributeError:
            raise ValueError(
                f"unknown format {fmt!r}; expected one of {FORMATS}"
            ) from None
        return method(text, **kwargs)

    def to_format(self, fmt: str, **kwargs) -> str:
        try:
            method = getattr(self, f"to_{fmt}")
        except AttributeError:
            raise ValueError(
                f"unknown format {fmt!r}; expected one of {FORMATS}"
            ) from None
        return method(**kwargs)
