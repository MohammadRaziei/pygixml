"""
Tests for pygixml.html_to_xml / pygixml.parse_html (messy HTML -> XML).
"""
import xml.etree.ElementTree as ET

import pytest

import pygixml
from pygixml import dictify


def conv(html, **kw):
    return pygixml.html_to_xml(html, **kw)


# --- well-formedness -------------------------------------------------

MESSY = [
    "<ul><li>a<li>b<br></ul>",
    "<p>one<p>two",
    "<div class=a class=b disabled @click='x' [p]=1>x &nbsp; &amp; &lt;<img src=a.png></div>",
    "<!DOCTYPE html><html><head><title>t</title><script>if(a<b&&c){}</script></head>"
    "<body><table><tr><td>1<td>2<tr><td>3</table></body></html>",
    "text only",
    "",
    "<!-- a -- b - --><p>x</p></div></p>",
    "<select><optgroup label=a><option>1<option>2<optgroup label=b><option>3</select>",
    "<dl><dt>a<dd>b<dt>c<dd>d</dl>",
    "<a href='x?a=1&b=2'>link</a><b>bold<i>both</b>italic</i>",
    "<div><span>unclosed",
    "<p>\x00ctrl\x0b chars</p>",
    "<x:y z:w='1'>ns-ish</x:y>",
    "<1bad 2attr=x>t</1bad>",
]


@pytest.mark.parametrize("html", MESSY)
def test_output_is_well_formed_xml(html):
    ET.fromstring(conv(html))           # stdlib parser is the strict judge
    pygixml.parse_html(html)            # and so is pugixml


# --- tag-level fixes ---------------------------------------------------

def test_void_tags_are_self_closed():
    assert conv("<div>a<br>b<hr><img src=x></div>") == '<div>a<br/>b<hr/><img src="x"/></div>'


def test_li_implicitly_closed_but_nested_lists_kept():
    out = conv("<ul><li>a<ul><li>b<li>c</ul><li>d</ul>")
    assert out == "<ul><li>a<ul><li>b</li><li>c</li></ul></li><li>d</li></ul>"


def test_p_closed_by_block_but_not_across_table_cell():
    assert conv("<div><p>a<div>b</div></div>") == "<div><p>a</p><div>b</div></div>"
    out = conv("<p>a<table><tr><td><p>x<p>y</table>")
    assert ET.fromstring(out).findall(".//td/p")[1].text == "y"


def test_table_cells_and_rows():
    out = conv("<table><tr><td>1<td>2<tr><td>3</table>")
    assert out == "<table><tr><td>1</td><td>2</td></tr><tr><td>3</td></tr></table>"


def test_stray_end_tags_ignored_and_misnested_closed():
    assert conv("<p>x</p></div></span>") == "<p>x</p>"
    assert conv("<b>bold<i>both</b>after</i>") == "<root><b>bold<i>both</i></b>after</root>"


def test_unclosed_at_eof():
    assert conv("<div><span>hi") == "<div><span>hi</span></div>"


def test_names_are_lowercased():
    assert conv("<DIV CLASS=A>x</DIV>") == '<div class="A">x</div>'


# --- attributes --------------------------------------------------------

def test_valueless_and_duplicate_attributes():
    assert conv("<input disabled value=1 value=2>") == '<input disabled="" value="1"/>'


def test_invalid_attribute_names_sanitised():
    assert conv("<a @click=1 [p]=2 :x=3 #r=4 v-on:go=5>t</a>") == (
        '<a _click="1" _p_="2" _x="3" _r="4" v-on_go="5">t</a>'
    )


def test_prefixed_names_do_not_break_namespace_aware_parsers():
    assert conv("<o:p xlink:href=x>t</o:p>") == '<o_p xlink_href="x">t</o_p>'


def test_attribute_value_escaping():
    out = conv("<a title='say \"hi\" &amp; <b>'>t</a>")
    assert ET.fromstring(out).get("title") == 'say "hi" & <b>'


# --- text, entities, raw text, comments -------------------------------

def test_entities_become_characters():
    root = ET.fromstring(conv("<p>a&nbsp;b &copy; &lt;&amp;&gt; &#65;</p>"))
    assert root.text == "a\u00a0b \u00a9 <&> A"


def test_script_and_style_are_raw_text():
    root = ET.fromstring(conv("<div><script>if(a<b && c>d){x='</'+'p>'}</script></div>"))
    assert root.find("script").text == "if(a<b && c>d){x='</'+'p>'}"


def test_comment_with_double_dash_and_trailing_dash():
    ET.fromstring(conv("<!-- a -- b ---><p/>"))
    assert pygixml.parse_html("<p><!-- x -- y -->t</p>") is not None


def test_doctype_and_pi_dropped():
    assert conv("<!DOCTYPE html><?php echo 1 ?><p>x</p>") == "<p>x</p>"


def test_control_characters_removed():
    assert ET.fromstring(conv("<p>a\x00b\x0bc</p>")).text == "abc"


# --- root handling ----------------------------------------------------

def test_single_root_kept_fragment_wrapped():
    assert conv("<html><body>x</body></html>\n") == "<html><body>x</body></html>"
    assert conv("<p>a</p><p>b</p>") == "<root><p>a</p><p>b</p></root>"
    assert conv("hello <b>w</b>") == "<root>hello <b>w</b></root>"
    assert conv("") == "<root></root>"


def test_custom_wrapper_name():
    assert conv("<p>a</p><p>b</p>", root="frag") == "<frag><p>a</p><p>b</p></frag>"


# --- integration with the rest of pygixml ------------------------------

PAGE = """<!DOCTYPE html>
<html lang=en>
<head><meta charset=utf-8><title>Shop</title></head>
<body>
  <ul id=items>
    <li class=item data-id=1>Apple<br><span class=price>1.5
    <li class=item data-id=2>Pear<span class=price>2.0
  </ul>
  <p>Done &amp; dusted
</body>
</html>"""


def test_parse_html_xpath():
    doc = pygixml.parse_html(PAGE)
    root = doc.first_child()
    assert root.name == "html"
    prices = [n.node.child_value() for n in root.select_nodes("//span[@class='price']")]
    assert [p.strip() for p in prices] == ["1.5", "2.0"]
    ids = [n.node.attribute("data-id").value for n in root.select_nodes("//li")]
    assert ids == ["1", "2"]


def test_parse_html_dictify():
    d = dictify.parse(conv(PAGE))
    items = d["html"]["body"]["ul"]["li"]
    assert [i["@data-id"] for i in items] == ["1", "2"]
    assert d["html"]["@lang"] == "en"


def test_parse_html_accepts_parse_flags():
    doc = pygixml.parse_html("<p><!-- c -->t</p>", options=pygixml.ParseFlags.MINIMAL)
    assert doc.first_child().name == "p"


# --- FormatDocument / CLI ----------------------------------------------

def test_format_document_from_html():
    from pygixml.formats import FormatDocument
    doc = FormatDocument.from_html("<ul><li>a<li>b</ul>")
    assert doc.data == {"ul": {"li": ["a", "b"]}}


def test_convert_cli_html_to_json(tmp_path):
    import json, subprocess, sys
    src = tmp_path / "page.html"
    src.write_text("<ul><li>a<li>b<br></ul>", encoding="utf-8")
    out = subprocess.run(
        [sys.executable, "-m", "pygixml", "convert", str(src), "--to", "json"],
        capture_output=True, text=True, check=True,
    ).stdout
    assert json.loads(out) == {"ul": {"li": ["a", {"br": None, "#text": "b"}]}}
