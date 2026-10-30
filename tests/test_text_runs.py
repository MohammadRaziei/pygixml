"""Text split by child elements, in every XML -> dict/JSON engine.

An element's text is read in *runs*: text and CDATA next to each other (also across a
comment or processing instruction) are one run, and only a child element ends it.
Whitespace-only runs don't count. ``#text`` is the first run, or, with
``cdata_separator=<str>``, all of them joined by it. dictify.parse, the jsonify
writers (in memory and streamed) and iterdict / iterjsonl must all agree with this
reference, which is written with ElementTree so it shares no code with them.
"""
import json
import os
import random
import xml.etree.ElementTree as ET

import pytest

import pygixml
from pygixml import dictify, jsonify

OPTIONS = [{}, {"cdata_separator": ""}, {"cdata_separator": " "}, {"cdata_separator": "|"}]
_WS = " \t\r\n"


def reference(e, sep=None):
    runs = [t for t in [e.text] + [c.tail for c in e] if t and t.strip(_WS)]
    text = None if not runs else (runs[0] if sep is None else sep.join(runs))
    if not e.attrib and len(e) == 0:
        return text
    out = {"@" + k: v for k, v in e.attrib.items()}
    if text is not None:
        out["#text"] = text
    groups = {}
    for c in e:
        groups.setdefault(c.tag, []).append(reference(c, sep))
    for tag, vs in groups.items():
        out[tag] = vs if len(vs) > 1 else vs[0]
    return out


def _gen(r, depth=0, tag=None):
    tag = tag or r.choice("abc")
    attrs = "".join(f' k{i}="v{r.randint(0, 9)}"' for i in range(r.randint(0, 2)))
    items = []                                   # (is_element, xml)
    for _ in range(r.randint(0, 5) if depth < 3 else 0):
        k = r.random()
        if k < 0.4:
            items.append((True, _gen(r, depth + 1)))
        elif k < 0.75:
            items.append((False, r.choice(["x", "yy", " z ", "t&amp;t", "é", "\u00a0", "\u2003 ", " ", "\n  "])))
        else:
            items.append((False, r.choice(["<![CDATA[c]]>", "<!--n-->", "<?p d?>", "<![CDATA[ ]]>"])))
    # pugixml drops whitespace-only plain text when it parses, the other readers keep it. They
    # only agree when such text sits between two elements (a run of its own), so that is the
    # only place it may stay.
    for i, (is_el, x) in enumerate(items):
        if not is_el and x in (" ", "\n  "):
            before = i == 0 or items[i - 1][0]
            after = i == len(items) - 1 or items[i + 1][0]
            if not (before and after):
                items[i] = (False, "x")
    return f"<{tag}{attrs}>" + "".join(x for _, x in items) + f"</{tag}>"


def _docs(n, seed):
    r = random.Random(seed)
    return [_gen(r) for _ in range(n)]


@pytest.mark.parametrize("opt", OPTIONS, ids=["none", "empty", "space", "bar"])
def test_whole_document_engines_match_the_reference(tmp_path, opt):
    sep = opt.get("cdata_separator")
    p, j = str(tmp_path / "a.xml"), str(tmp_path / "a.json")
    for xml in _docs(250, seed=1):
        root = ET.fromstring(xml)
        want = {root.tag: reference(root, sep)}
        with open(p, "w", encoding="utf-8") as f:
            f.write(xml)
        jsonify.stream_dump(p, j, **opt)
        doc = pygixml.parse_string(xml)            # a node doesn't keep its document alive
        got = {
            "dictify.parse": dictify.parse(xml, **opt),
            "dictify.parse_file": dictify.parse_file(p, **opt),
            "jsonify.dumps_str": json.loads(jsonify.dumps_str(xml, **opt)),
            "jsonify.dumps_file": json.loads(jsonify.dumps_file(p, **opt)),
            "jsonify.dumps_node": json.loads(jsonify.dumps_node(doc.root, **opt)),
            "jsonify.stream_dump": json.load(open(j, encoding="utf-8")),
        }
        for name, value in got.items():
            assert value == want, (name, xml, opt)


@pytest.mark.parametrize("opt", OPTIONS, ids=["none", "empty", "space", "bar"])
def test_record_engines_match_the_reference(tmp_path, opt):
    sep = opt.get("cdata_separator")
    p, jl = str(tmp_path / "a.xml"), str(tmp_path / "a.jsonl")
    r = random.Random(2)
    for _ in range(60):
        recs = [_gen(r, 1, "rec") for _ in range(r.randint(1, 4))]
        xml = "<root>" + "".join(recs) + "</root>"
        with open(p, "w", encoding="utf-8") as f:
            f.write(xml)
        want = [reference(e, sep) for e in ET.fromstring(xml)]
        jsonify.stream_jsonl(p, jl, "rec", **opt)
        got = {
            "dictify.iterdict": list(dictify.iterdict(p, "rec", **opt)),
            "jsonify.iterjsonl": [json.loads(s) for s in jsonify.iterjsonl(p, "rec", **opt)],
            "jsonify.stream_jsonl": [json.loads(s) for s in open(jl, encoding="utf-8").read().splitlines()],
        }
        for name, value in got.items():
            assert value == want, (name, xml, opt)


def test_the_cases_that_used_to_differ():
    # text next to CDATA or a comment is one run; text after the first child counts when nothing came before
    for xml, want in [
        ("<a>x<![CDATA[c]]> z</a>", "xc z"),
        ("<a>x<!--n-->y</a>", "xy"),
        ("<a><![CDATA[c]]>x</a>", "cx"),
        ("<a><b/>tail</a>", {"b": None, "#text": "tail"}),
        ("<a>\n  <b/>tail</a>", {"b": None, "#text": "tail"}),
    ]:
        assert dictify.parse(xml)["a"] == want, xml


@pytest.mark.parametrize("opt", OPTIONS, ids=["none", "empty", "space", "bar"])
def test_no_break_space_is_text_not_whitespace(tmp_path, opt):
    # XML whitespace is space, tab, CR and LF; U+00A0 / U+2003 are real text in every engine
    # (an HTML &nbsp; must survive the way the C++ writers already kept it)
    sep = opt.get("cdata_separator")
    for xml in ("<p>\u00a0</p>", "<p>\u00a0<b/>x</p>", "<p>\u2003<b/>\u00a0</p>", "<p>a<b/>\u00a0</p>"):
        ref = reference(ET.fromstring(xml), sep)
        assert dictify.parse(xml, **opt) == {"p": ref}, xml
        assert json.loads(jsonify.dumps_str(xml, **opt)) == {"p": ref}, xml
        f = tmp_path / "n.xml"
        f.write_text(xml, encoding="utf-8")
        assert json.loads(jsonify.dumps_file(str(f), **opt)) == {"p": ref}, xml
    assert dictify.parse("<p>\u00a0</p>") == {"p": "\u00a0"}
    assert dictify.parse("<p> \u00a0 </p>", strip_whitespace=True) == {"p": "\u00a0"}
