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
        '<a _at_click="1" _lbracket_p_rbracket_="2" _colon_x="3" _hash_r="4"'
        ' v-on_colon_go="5">t</a>'
    )


def test_prefixed_names_do_not_break_namespace_aware_parsers():
    assert conv("<o:p xlink:href=x>t</o:p>") == '<o_colon_p xlink_colon_href="x">t</o_colon_p>'


def test_attribute_value_escaping():
    out = conv("<a title='say \"hi\" &amp; <b>'>t</a>")
    assert ET.fromstring(out).get("title") == 'say "hi" & <b>'


def test_whitespace_in_attribute_values_survives():
    # (CRLF / lone CR are normalised to LF first, as the HTML spec says)
    src = "<div data-code='a\n\tb\r\nc\rd'>x</div>"
    assert ET.fromstring(conv(src)).get("data-code") == "a\n\tb\nc\nd"
    doc = pygixml.parse_html(src)
    assert doc.root.attribute("data-code").value == "a\n\tb\nc\nd"
    # HTML output keeps them literal (no &#10; noise)
    assert pygixml.xml_to_html(doc) == '<div data-code="a\n\tb\nc\nd">x</div>'


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


# --- reverse direction: xml_to_html -----------------------------------------

def back(html, **kw):
    return pygixml.xml_to_html(pygixml.parse_html(html), unwrap="root", **kw)


def test_xml_to_html_void_and_empty_elements():
    assert back("<div></div><br><img src=x>") == '<div></div><br><img src="x">'
    # never "<div/>": browsers read that as an open tag
    doc = pygixml.parse_string("<div/>")
    assert pygixml.xml_to_html(doc) == "<div></div>"


def test_xml_to_html_restores_encoded_names():
    out = back("<o:p @click=1 [x]=2 1bad=3>t</o:p>")
    assert out == '<o:p @click="1" [x]="2" 1bad="3">t</o:p>'
    assert pygixml.html_to_xml(out) == pygixml.html_to_xml("<o:p @click=1 [x]=2 1bad=3>t</o:p>")


def test_xml_to_html_script_style_raw_but_cannot_close_early():
    out = back("<script>if(a<b&&c){}</script><style>a>b{}</style>")
    assert out == "<script>if(a<b&&c){}</script><style>a>b{}</style>"
    doc = pygixml.parse_string("<script>x='&lt;/script&gt;'</script>")
    assert "</script><" not in pygixml.xml_to_html(doc).replace("</script>", "", 1)
    doc = pygixml.parse_string("<script>x='&lt;/script>'</script>")
    assert pygixml.xml_to_html(doc) == "<script>x='<\\/script>'</script>"


def test_xml_to_html_escaping():
    out = back("<p title='a\"b &amp; c'>1 &lt; 2 &amp; 3</p>")
    assert out == '<p title="a&quot;b &amp; c">1 &lt; 2 &amp; 3</p>'


def test_xml_to_html_whitespace_between_inline_tags_kept():
    assert back("<p>x <b>y</b> <i>z</i></p>") == "<p>x <b>y</b> <i>z</i></p>"


def test_xml_to_html_pre_leading_newline():
    for src in ("<pre>\nhi</pre>", "<pre>\n\nhi</pre>", "<pre>hi</pre>"):
        out = back(src)
        assert pygixml.html_to_xml(out) == pygixml.html_to_xml(src)


def test_xml_to_html_comments_doctype_unwrap():
    assert back("<!-- c --><p>x</p>") == "<!-- c --><p>x</p>"
    doc = pygixml.parse_html("<p>a</p><p>b</p>")
    assert pygixml.xml_to_html(doc) == "<root><p>a</p><p>b</p></root>"
    assert pygixml.xml_to_html(doc, unwrap="root", doctype=True) == "<!DOCTYPE html><p>a</p><p>b</p>"


def test_xml_to_html_pretty_only_touches_block_structure():
    out = back("<ul><li>a<li>b <b>c</b></ul><pre>  x\n  y</pre><p>t<span>1</span><span>2</span></p>", pretty=True)
    assert out == (
        "<ul>\n  <li>a</li>\n  <li>b <b>c</b></li>\n</ul>\n"
        "<pre>  x\n  y</pre>\n<p>t<span>1</span><span>2</span></p>"
    )
    div = back("<div><span>a</span><span>b</span></div>", pretty=True)
    assert div == "<div><span>a</span><span>b</span></div>"      # no space injected


def test_to_html_methods_on_node_and_document():
    doc = pygixml.parse_html("<ul><li>a<li>b</ul>")
    assert doc.to_html() == "<ul><li>a</li><li>b</li></ul>"
    assert doc.root.child("li").to_html() == "<li>a</li>"
    assert doc.to_html(pretty=True) == "<ul>\n  <li>a</li>\n  <li>b</li>\n</ul>"


@pytest.mark.parametrize("html", MESSY)
def test_round_trip_is_stable(html):
    once = back(html)
    assert back(once) == once                       # html -> xml -> html is idempotent
    assert pygixml.html_to_xml(once) == pygixml.html_to_xml(html)


def test_round_trip_real_world_shaped_page():
    # (also covers attribute newlines, see test_whitespace_in_attribute_values_survives)
    once = back(PAGE)
    assert back(once) == once
    assert back(once, pretty=True) == back(back(once, pretty=True), pretty=True)


# --- errors --------------------------------------------------------------

def test_errors_are_pygixml_errors():
    assert issubclass(pygixml.PygiXMLHTMLError, pygixml.PygiXMLError)


@pytest.mark.parametrize("bad", [b"<p>x</p>", None, 42])
def test_html_to_xml_rejects_non_str(bad):
    with pytest.raises(pygixml.PygiXMLHTMLError, match="must be str"):
        pygixml.html_to_xml(bad)
    with pytest.raises(pygixml.PygiXMLError):
        pygixml.parse_html(bad)


def test_xml_to_html_rejects_bad_nodes():
    with pytest.raises(pygixml.PygiXMLHTMLError, match="XMLNode or XMLDocument"):
        pygixml.xml_to_html("<p/>")
    null = pygixml.parse_string("<x/>").root.child("missing")
    with pytest.raises(pygixml.PygiXMLHTMLError, match="null"):
        pygixml.xml_to_html(null)


def test_very_deep_nesting_does_not_crash():
    # both directions are iterative in C++: no stack overflow, no RecursionError
    n = 20000
    doc = pygixml.parse_html("<div>" * n + "x")
    out = pygixml.xml_to_html(doc)
    assert out.startswith("<div><div>") and out.count("<div>") == n and out.count("</div>") == n


def test_empty_root_name_rejected():
    with pytest.raises(pygixml.PygiXMLHTMLError, match="root"):
        pygixml.html_to_xml("<p>x", root="")


# --- convert CLI / FormatDocument, reverse ----------------------------------

def test_format_document_to_html():
    from pygixml.formats import FormatDocument
    doc = FormatDocument({"ul": {"li": ["a", "b"]}})
    assert doc.to_html() == "<ul><li>a</li><li>b</li></ul>"
    # XML data is not run through HTML tag rules: case is kept, <p> doesn't auto-close
    assert FormatDocument({"Doc": {"p": {"p": "x"}}}).to_html() == "<Doc><p><p>x</p></p></Doc>"


def test_convert_cli_xml_to_html_and_html_cleanup(tmp_path):
    import subprocess, sys
    src = tmp_path / "d.xml"
    src.write_text("<ul><li>a</li><li/></ul>", encoding="utf-8")
    out = subprocess.run(
        [sys.executable, "-m", "pygixml", "convert", str(src), "--to", "html"],
        capture_output=True, text=True, check=True,
    ).stdout
    assert out.strip() == "<ul><li>a</li><li></li></ul>"
    messy = tmp_path / "m.html"
    messy.write_text("<ul><li>a<li>b<br></ul>", encoding="utf-8")
    out = subprocess.run(
        [sys.executable, "-m", "pygixml", "convert", str(messy), "-o", str(tmp_path / "c.html")],
        capture_output=True, text=True, check=True,
    )
    assert (tmp_path / "c.html").read_text(encoding="utf-8") == "<ul><li>a</li><li>b<br></li></ul>"


# --- C++ tokenizer specifics ---------------------------------------------

def test_nul_character_does_not_truncate_input():
    out = conv("<p>a</\x00b</p>c")
    assert out.endswith("c</p>") and "a" in out   # (bogus comment, then the rest is kept)
    assert conv("<p>a\x00b</p>") == "<p>ab</p>"


def test_eof_inside_a_tag_drops_the_tag_like_browsers_do():
    assert conv("<p>a</p><b") == "<p>a</p>"
    assert conv("x<<y") == "<root>x&lt;</root>"
    assert conv("<p>a</p><a href='unterminated") == "<p>a</p>"


def test_title_and_textarea_are_rcdata_script_style_are_raw():
    assert conv("<title>a &amp; <b>x</b></title>") == "<title>a &amp; &lt;b&gt;x&lt;/b&gt;</title>"
    assert conv("<textarea>\n<i>&lt;</textarea>") == "<textarea>&lt;i&gt;&lt;</textarea>"   # leading \n dropped
    assert conv("<script>a&amp;b</script>") == "<script>a&amp;amp;b</script>"                # no decoding


def test_html5_character_references():
    root = ET.fromstring(conv("<p>&copy &copy; &amp &notit; &#150; &#x41 &#0; &#xD800; &bogus; &</p>"))
    assert root.text == "\u00a9 \u00a9 & \u00ac" + "it; \u2013 A \ufffd \ufffd &bogus; &"


def test_legacy_reference_in_attribute_followed_by_equals_or_alnum_is_literal():
    # the classic ?a=1&copy=2 URL: must not turn into "?a=1(c)=2"
    el = ET.fromstring(conv("<a href='?a=1&copy=2&amp;b=3&copyx'>t</a>"))
    assert el.get("href") == "?a=1&copy=2&b=3&copyx"
    assert ET.fromstring(conv("<p>?a=1&copy=2</p>")).text == "?a=1\u00a9=2"       # text: decoded


def test_unicode_names_and_xml_name_rules():
    assert conv("<a日本 ü=1>t</a日本>") == '<a日本 ü="1">t</a日本>'
    assert conv("<é>t").startswith("<root>&lt;é&gt;t")       # HTML5: a tag name starts with an ASCII letter
    assert conv("<a -x=1 .y=2 z-=3>t</a>") == '<a _x2d_x="1" _x2e_y="2" z-="3">t</a>'
    out = back("<a -x=1 .y=2 :z=3 w\u2014v=4>t</a>")
    assert out == '<a -x="1" .y="2" :z="3" w\u2014v="4">t</a>'


def test_pretty_does_not_inject_newlines_next_to_top_level_text():
    doc = pygixml.parse_html("hello<ul><li>a<li>b</ul>")
    once = pygixml.xml_to_html(doc, unwrap="root", pretty=True)
    assert once == "hello<ul>\n  <li>a</li>\n  <li>b</li>\n</ul>"
    assert pygixml.xml_to_html(pygixml.parse_html(once), unwrap="root", pretty=True) == once


def test_text_of_only_illegal_characters_is_blank():
    assert conv("\ufffe<p>x</p>") == "<p>x</p>"          # no needless <root> wrapper


def test_lone_surrogate_does_not_abort():
    assert conv("<p>a\ud800b</p>").startswith("<p>a")


def test_convert_cli_html_to_html_keeps_mixed_content(tmp_path):
    import subprocess, sys
    src = tmp_path / "m.html"
    src.write_text("<p>a <b>x</b> c <i>y</i> d</p>\n<ul><li>1<li>2</ul>", encoding="utf-8")

    def run(*args):
        return subprocess.run(
            [sys.executable, "-m", "pygixml", "convert", str(src), *args],
            capture_output=True, text=True, check=True,
        ).stdout.rstrip("\n")

    assert run("--to", "html") == "<p>a <b>x</b> c <i>y</i> d</p><ul><li>1</li><li>2</li></ul>"
    assert run("--to", "html", "-p") == (
        "<p>a <b>x</b> c <i>y</i> d</p>\n<ul>\n  <li>1</li>\n  <li>2</li>\n</ul>"
    )
    xml = tmp_path / "m.xml"
    xml.write_text("<p>a <b>x</b> c <i>y</i> d</p>", encoding="utf-8")
    out = subprocess.run(
        [sys.executable, "-m", "pygixml", "convert", str(xml), "--to", "html"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert out == "<p>a <b>x</b> c <i>y</i> d</p>"
