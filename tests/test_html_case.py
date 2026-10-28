"""html_to_xml / parse_html `case`: "lower" (default), "keep", "escape"."""
import random
import re
import xml.etree.ElementTree as ET

import pytest

import pygixml
from pygixml import decode_name, html_to_xml, parse_html, xml_to_html

CASES = ["lower", "keep", "escape"]


def test_default_is_lower():
    h = "<DIV Class=a>t</DIV>"
    assert html_to_xml(h) == html_to_xml(h, case="lower") == '<div class="a">t</div>'


def test_keep_writes_names_as_given():
    h = '<DIV @Click=1 viewBox="x"><svg><linearGradient/></svg></DIV>'
    assert html_to_xml(h, case="keep") == (
        '<DIV _x0040_Click="1" viewBox="x"><svg><linearGradient/></svg></DIV>')


def test_escape_writes_lower_case_names_with_escapes():
    assert html_to_xml('<DIV @Click=1 viewBox="x"></DIV>', case="escape") == (
        '<_x0044__x0049__x0056_ _x0040__x0043_lick="1" view_x0042_ox="x"></_x0044__x0049__x0056_>')


@pytest.mark.parametrize("case", CASES)
def test_values_and_text_are_never_touched(case):
    assert '="Big Text">Hello World<' in html_to_xml('<p CLASS="Big Text">Hello World</p>', case=case)


def test_at_click_and_at_Click_are_different_attributes_only_when_case_is_kept():
    h = "<p @Click=1 @click=2>t</p>"
    assert html_to_xml(h) == '<p _x0040_click="1">t</p>'                     # first wins, as in a browser
    for case in ("keep", "escape"):
        d = parse_html(h, case=case)
        assert xml_to_html(d) == '<p @Click="1" @click="2">t</p>'


def test_same_spelling_duplicate_still_first_wins():
    for case in CASES:
        assert html_to_xml("<p a=1 a=2>t</p>", case=case) == '<p a="1">t</p>'


def test_end_tag_takes_the_spelling_of_its_start_tag():
    assert html_to_xml("<Div>a</DIV>", case="keep") == "<Div>a</Div>"
    assert html_to_xml("<DIV>a</div>", case="keep") == "<DIV>a</DIV>"
    assert html_to_xml("<DIV>a<span>b", case="keep") == "<DIV>a<span>b</span></DIV>"      # implied end tags


def test_logic_ignores_case():
    k = lambda h: html_to_xml(h, case="keep")
    assert k("<P>a<P>b") == "<root><P>a</P><P>b</P></root>"                   # implied end tag
    assert k("<UL><LI>a<LI>b</UL>") == "<UL><LI>a</LI><LI>b</LI></UL>"
    assert k("a<BR>b") == "<root>a<BR/>b</root>"                              # void
    assert k("<SCRIPT>if(a<b){}</SCRIPT>") == "<SCRIPT>if(a&lt;b){}</SCRIPT>"  # raw text
    assert k("<TextArea>\nx</TEXTAREA>") == "<TextArea>x</TextArea>"          # leading newline dropped
    assert k("<TABLE><TR><TD>1<TD>2</TABLE>") == "<TABLE><TR><TD>1</TD><TD>2</TD></TR></TABLE>"


@pytest.mark.parametrize("case", ["keep", "escape"])
def test_round_trip_restores_the_original_spelling(case):
    h = '<DIV @Click="1" viewBox="x" Data-ID="a"><svg><linearGradient></linearGradient></svg><o:P>t</o:P></DIV>'
    assert xml_to_html(parse_html(h, case=case)) == h


def test_decode_name_reads_escaped_case():
    d = parse_html("<Foo>t</Foo>", case="escape")
    assert d.root.name == "_x0046_oo"
    assert decode_name(d.root.name) == "Foo"


def test_bad_case_value():
    for bad in ("Lower", "upper", "", None, 1, True):
        with pytest.raises(pygixml.PygiXMLHTMLError, match="case"):
            html_to_xml("<p>", case=bad)
        with pytest.raises(pygixml.PygiXMLHTMLError, match="case"):
            parse_html("<p>", case=bad)


# --- the three modes are the same document, only the spelling of names differs -----------

_TAGS = ["div", "P", "Span", "BR", "Ul", "LI", "a", "Table", "TR", "TD", "svg", "linearGradient", "o:P", "Img"]
_ATTRS = ["Class", "@Click", "viewBox", "DATA-ID", "v-Bind:Foo", "[Prop]", "id"]


def _random_html(r):
    out = []
    for _ in range(r.randint(1, 12)):
        k = r.random()
        if k < 0.55:
            tag = r.choice(_TAGS)
            attrs = r.sample(_ATTRS, r.randint(0, 3))                  # no two spelled the same except by case: sample is distinct
            out.append("<" + tag + "".join(f' {a}="V{r.randint(0, 9)}"' for a in attrs) + ">")
        elif k < 0.8:
            out.append("</" + r.choice([t.swapcase() if r.random() < 0.5 else t for t in _TAGS]) + ">")
        else:
            out.append(r.choice(["Text", " ", "a &amp; B", "x"]))
    return "".join(out)


def _canon(xml):
    def rec(e):
        attrs = tuple(sorted((decode_name(k).lower(), v) for k, v in e.attrib.items()))
        return (decode_name(e.tag).lower(), attrs, (e.text or ""), tuple((rec(c), c.tail or "") for c in e))
    return rec(ET.fromstring(xml))


def test_three_modes_give_the_same_document():
    r = random.Random(21)
    n = 0
    for _ in range(1500):
        h = _random_html(r)
        # distinct spellings of one attribute (Class/class) can't occur: _ATTRS holds each name once
        xs = {c: html_to_xml(h, case=c) for c in CASES}
        assert _canon(xs["lower"]) == _canon(xs["keep"]) == _canon(xs["escape"]), (h, xs)
        # escape mode leaves no upper-case ASCII letter in any name
        for m in re.finditer(r"</?([^\s/>]+)|\s([^\s=>/]+)=\"", xs["escape"]):
            name = m.group(1) or m.group(2)
            assert not re.search("[A-Z]", re.sub("_x[0-9A-F]+_", "", name)), (h, name)
        # keep and escape restore the same HTML; lower is that HTML with names lower-cased
        hk = xml_to_html(parse_html(h, case="keep"))
        assert hk == xml_to_html(parse_html(h, case="escape")), h
        n += 1
    assert n == 1500


# --- FormatDocument and the convert CLI ----------------------------------------------------

def test_format_document_from_html_case():
    from pygixml.formats import FormatDocument
    h = "<UL @Click=1><LI>a</UL>"
    assert FormatDocument.from_html(h).data == {"ul": {"@_x0040_click": "1", "li": "a"}}
    assert FormatDocument.from_html(h, case="keep").data == {"UL": {"@_x0040_Click": "1", "LI": "a"}}
    assert FormatDocument.from_format(h, "html", case="escape").data == {
        "_x0055__x004C_": {"@_x0040__x0043_lick": "1", "_x004C__x0049_": "a"}}


def _convert(args, **kw):
    import subprocess, sys
    return subprocess.run([sys.executable, "-m", "pygixml", "convert", *args],
                          capture_output=True, text=True, **kw)


@pytest.mark.parametrize("case, expected", [
    ("lower", '<div @click="1"><p>x</p></div>'),
    ("keep", '<DIV @Click="1"><P>x</P></DIV>'),
    ("escape", '<DIV @Click="1"><P>x</P></DIV>'),
])
def test_convert_cli_case(tmp_path, case, expected):
    src = tmp_path / "m.html"
    src.write_text('<DIV @Click=1><P>x</DIV>', encoding="utf-8")
    r = _convert([str(src), "--to", "html", "--case", case], check=True)
    assert r.stdout.strip() == expected
    j = _convert([str(src), "--to", "json", "--case", case], check=True).stdout
    assert ("DIV" in j) == (case == "keep")


def test_convert_cli_case_needs_html_input(tmp_path):
    src = tmp_path / "a.xml"
    src.write_text("<a/>", encoding="utf-8")
    r = _convert([str(src), "--to", "json", "--case", "keep"])
    assert r.returncode == 2 and "--case only applies to html input" in r.stderr
    r = _convert([str(src), "--to", "json", "--case", "nope"])
    assert r.returncode == 2


def test_html_to_dict_keeps_all_the_text_of_an_element():
    from pygixml.formats import FormatDocument
    assert FormatDocument.from_html("<p>Hi<br>x</p>").data == {"p": {"br": None, "#text": "Hix"}}
    assert FormatDocument.from_html("<p>Hi <b>there</b> you</p>").data == {"p": {"b": "there", "#text": "Hi  you"}}
    assert FormatDocument.from_html("<p>Hi<br>x</p>", cdata_separator=None).data == {"p": {"br": None, "#text": "Hi"}}


def test_convert_cli_html_to_json_keeps_tail_text(tmp_path):
    import json
    src = tmp_path / "t.html"
    src.write_text("<p>Hi<br>x</p>", encoding="utf-8")
    assert json.loads(_convert([str(src), "--to", "json"], check=True).stdout) == {"p": {"br": None, "#text": "Hix"}}
