"""encode_name / decode_name / XMLNameCodec: the SQL/XML name mapping
(ISO/IEC 9075-14, "Mapping SQL identifiers to XML Names")."""
import random
import re
import xml.etree.ElementTree as ET

import pytest

import pygixml
from pygixml import XMLNameCodec, decode_name, encode_name

# --- the spec, typed out independently of the C++: XML 1.0 5th ed. names without ':' ---
_START = ("A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D"
          "\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD\U00010000-\U000EFFFF")
_CHAR = _START + "\\-.0-9\u00B7\u0300-\u036F\u203F-\u2040"
NCNAME = re.compile(f"[{_START}][{_CHAR}]*")


@pytest.mark.parametrize("raw, mapped", [
    ("@Click", "_x0040_Click"),                 # case is kept
    ("o:p", "o_x003A_p"),
    ("[prop]", "_x005B_prop_x005D_"),
    ("#ref", "_x0023_ref"),
    ("v-on:go", "v-on_x003A_go"),
    ("1bad", "_x0031_bad"),                     # fine inside a name, not first
    ("-x", "_x002D_x"),
    (".y", "_x002E_y"),
    ("a1-b.c", "a1-b.c"),
    ("xml:lang", "_x0078_ml_x003A_lang"),       # "xml" in any case: the first letter goes
    ("XMLfoo", "_x0058_MLfoo"),
    ("xmlns", "_x0078_mlns"),
    ("axml", "axml"),
    ("my_xvalue", "my_x005F_xvalue"),           # '_' before 'x' is escaped: one-to-one
    ("_x0040_", "_x005F_x0040_"),               # a name that already looks like an escape
    ("snake_case", "snake_case"),
    ("é-ñ", "é-ñ"),
    ("日本", "日本"),
    ("😀", "😀"),                                # U+1F600 is a legal name character
    ("a\uFFFEb", "a_xFFFE_b"),
    ("a\U000F0000", "a_x0F0000_"),              # above U+FFFF: 6 digits
    ("a b", "a_x0020_b"),
])
def test_known_mappings(raw, mapped):
    assert encode_name(raw) == mapped
    assert decode_name(mapped) == raw


def test_partial_escaping_keeps_inner_colons():
    c = XMLNameCodec(fully_escaped=False)
    assert c.encode("o:p") == "o:p"
    assert c.encode(":x") == "_x003A_x"
    assert c.encode("xmlns") == "xmlns"
    assert encode_name("o:p", fully_escaped=False) == "o:p"
    assert encode_name("o:p", False) != encode_name("o:p")


@pytest.mark.parametrize("mapped, raw", [
    ("_x0040_click", "@click"),
    ("_x0040_", "@"),
    ("_x00e9_", "é"),                           # lower-case hex
    ("_x1F600_", "😀"),                          # 5 digits (PostgreSQL)
    ("_x0001F600_", "😀"),                       # 8 digits (.NET)
    ("a_x0040_b_x0023_c", "a@b#c"),
    # not escapes: left alone
    ("_x40_", "_x40_"), ("_x0040", "_x0040"), ("_xZZZZ_", "_xZZZZ_"), ("_X0040_", "_X0040_"),
    ("_x0000_", "_x0000_"), ("_xD800_", "_xD800_"), ("_x110000_", "_x110000_"),
    ("_x000000040_", "_x000000040_"),           # 9 digits
    ("plain", "plain"), ("", ""),
])
def test_decode_edge_cases(mapped, raw):
    assert decode_name(mapped) == raw


_ALPHABET = list("abxXmlML_:-.019@#[]() \u00B7\u00E9\u0300\u2014\u2040\u3042\uFFFE\uFFFD") + ["\U0001F600", "\U000F0000", "\U00010000"]


def _samples(n=4000, seed=3):
    r = random.Random(seed)
    for _ in range(n):
        yield "".join(r.choice(_ALPHABET) for _ in range(r.randint(1, 8)))


@pytest.mark.parametrize("full", [True, False])
def test_round_trip(full):
    for s in _samples():
        assert decode_name(encode_name(s, full)) == s, s


def test_mapping_is_one_to_one():
    seen = {}
    for s in _samples(6000, seed=4):
        e = encode_name(s)
        assert seen.setdefault(e, s) == s, (s, seen[e], e)


def test_result_is_always_a_valid_xml_name():
    for s in _samples():
        e = encode_name(s)
        assert NCNAME.fullmatch(e), (s, e)               # no ':' anywhere, legal characters only
        assert not e[:3].lower() == "xml", (s, e)
        # expat still has the XML 1.0 4th-edition name tables: it rejects U+203F/2040,
        # U+FFFD and everything above U+FFFF, which the current spec (and libxml2) allow.
        if not any(c in "\u203F\u2040\uFFFD" or ord(c) > 0xFFFF for c in e):
            ET.fromstring(f"<{e} {e}='1'/>")             # an XML parser agrees (expat)
        pygixml.parse_string(f"<{e} {e}='1'/>")
        # partial escaping may keep inner colons, never a leading one
        assert not encode_name(s, False).startswith(":"), s


def test_codec_object():
    c = XMLNameCodec()
    assert c.encode("@Click") == "_x0040_Click"
    assert c.decode("_x0040_Click") == "@Click"
    assert repr(c) == "XMLNameCodec(fully_escaped=True)"
    assert repr(XMLNameCodec(0)) == "XMLNameCodec(fully_escaped=False)"
    assert XMLNameCodec(fully_escaped=False).decode("_x003A_x") == ":x"


def test_errors():
    for bad in (None, 42, b"abc"):
        with pytest.raises(pygixml.PygiXMLHTMLError):
            encode_name(bad)
        with pytest.raises(pygixml.PygiXMLHTMLError):
            decode_name(bad)
    with pytest.raises(pygixml.PygiXMLHTMLError):
        encode_name("")
    with pytest.raises(pygixml.PygiXMLHTMLError):
        encode_name("a\ud800b")                          # a lone surrogate can't be mapped back
    assert decode_name("") == ""


# --- the HTML helpers use exactly this mapping -------------------------------------------

@pytest.mark.parametrize("name", ["@click", "[p]", "v-on:go", "#r", "1bad", "-x", ".y", "xml:lang",
                                  "xmlns", "a_xb", "ü", "日本", "(evt)", "*ngif", "$a", "a+b"])
def test_html_to_xml_uses_encode_name(name):
    assert f'{encode_name(name)}="1"' in pygixml.html_to_xml(f"<p {name}=1>t</p>")
    back = pygixml.xml_to_html(pygixml.parse_html(f"<p {name}=1>t</p>"))
    assert back == f'<p {name}="1">t</p>'


def test_decode_name_reads_parsed_names():
    doc = pygixml.parse_html("<o:p>t</o:p>")
    assert doc.root.name == "o_x003A_p"
    assert decode_name(doc.root.name) == "o:p"


def test_html_lower_cases_names_before_mapping():
    # HTML names are case-insensitive, so the tokenizer folds them first; the mapping
    # itself keeps case. (@Click and @click only differ when you call encode_name.)
    assert "_x0040_click=" in pygixml.html_to_xml("<p @Click=1>t</p>")
    assert encode_name("@Click") != encode_name("@click")
