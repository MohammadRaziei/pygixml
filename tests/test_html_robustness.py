"""parse_html must turn any input into well-formed XML, lose no text, and survive a round trip.

No downloaded corpus: the entity table is Python's own HTML5 table, the rest are the kinds of
input that broke the converter (or html5lib-tests' tokenizer cases) one at a time.
"""
import html.entities
import re
import xml.etree.ElementTree as ET

import pytest

import pygixml


def _xml_root(doc):
    """ElementTree root of a parse_html result (several top-level nodes are wrapped)."""
    xml = re.sub(r"^<\?xml[^>]*\?>", "", doc.to_string())
    return ET.fromstring("<top>" + xml + "</top>")


NASTY = [
    "", "just text", "<", "<<<>>>", "&", "&&&;", "<p", "<p a", "<p a=", '<p a="', "<p a='x",
    "</", "</p", "</>", "<!", "<!-", "<!--", "<!-->", "<!--->", "<!---->", "<!--a--!>x",
    "<![CDATA[", "<![CDATA[>l", "<![CDATA[a]]>b", "<!DOCTYPE", "<!DOCTYPE html", "<!DOCTYPE html>x",
    "<?php echo 1 ?>x", "<?xml version='1.0'?><p>x</p>",
    "<br>a<BR>b<br/>c</br>d", "<img src=a.png alt=x><input disabled value=v checked>",
    "<p>a<p>b<p>c", "<b><i>x</b>y</i>", "<ul><li>a<li>b</ul>", "<table><tr><td>1<td>2</table>",
    "<script>if(a<b){x='</div>'}</script>after", "<style>a>b{}</style>", "<title>a<b>c</title>",
    "<textarea><i>x</i></textarea>", '<a href="a&amp;b" title=\'q"r\'>t</a>',
    "<div @click=a x-data:foo=1 :class=c 1x=2 a.b=3>t</div>", "<o:p>x</o:p><svg:rect/>",
    "<my-el>a</my-el><x_y>b</x_y><1a>c</1a>", "<p class=a class=b ID=x>t</p>",
    "a < b & c &unknown; &#999999999; &#x110000; &#0; &#x80;", "caf\u00e9 \u4e2d\u6587 \U0001F600",
    "<div>" * 3000 + "x", "<p>" + "x" * 100000 + "</p>", "<!-- a --><html><p>x</p></html><!-- z -->",
]


@pytest.mark.parametrize("src", NASTY, ids=lambda s: repr(s[:30]))
def test_nasty_input_gives_well_formed_xml_and_a_stable_round_trip(src):
    doc = pygixml.parse_html(src)
    _xml_root(doc)                               # well-formed
    first = doc.to_string()
    second = pygixml.parse_html(doc.to_html()).to_string()
    assert second == first                       # html -> xml -> html -> xml is a fixed point


def test_every_html5_named_entity_decodes_to_its_value():
    wrong = []
    for name, value in html.entities.html5.items():
        text = _xml_root(pygixml.parse_html(f"<p>&{name}</p>")).find("p").text
        if text != value:
            wrong.append((name, value, text))
    assert not wrong, wrong[:5]


def test_text_survives_a_leading_comment_and_unterminated_constructs():
    for src, needle in [
        ("<!-- c -->text", "text"),
        ("<!x>text", "text"),
        ("<![CDATA[>text", "text"),
        ("<p>a</p><![CDATA[>b", "b"),
    ]:
        assert needle in pygixml.parse_html(src).to_string()
