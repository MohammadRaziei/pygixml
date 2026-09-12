"""
Tests for `pygixml cat` (pretty-print + optional color for XML) and
the underlying pygixml._xmlcolor helper.
"""
import re
import subprocess
import sys

import pytest

from pygixml import _xmlcolor

XML = '<?xml version="1.0"?>\n<orders><order status="shipped" id="7"><customer>acme</customer></order></orders>'

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


@pytest.fixture
def xml_file(tmp_path):
    p = tmp_path / "data.xml"
    p.write_text(XML)
    return str(p)


def run(*args, input=None):
    return subprocess.run(
        [sys.executable, "-m", "pygixml", "cat", *args],
        capture_output=True, text=True, input=input,
    )


# --- _xmlcolor unit tests -------------------------------------------

def test_colorize_disabled_returns_unchanged():
    text = "<a>x</a>"
    assert _xmlcolor.colorize_xml(text, enabled=False) == text


def test_colorize_enabled_adds_ansi_codes_when_colorama_available():
    text = "<a>x</a>"
    out = _xmlcolor.colorize_xml(text, enabled=True)
    if _xmlcolor.HAVE_COLORAMA:
        assert out != text
        assert "\x1b[" in out
    else:
        assert out == text  # no crash, just no color


def test_colorize_strips_to_same_text_ignoring_ansi():
    text = '<order status="shipped"><item>1</item></order>'
    out = _xmlcolor.colorize_xml(text, enabled=True)
    assert _ANSI_RE.sub("", out) == text


def test_should_colorize_never_is_always_false():
    class FakeTTY:
        def isatty(self):
            return True
    assert _xmlcolor.should_colorize("never", FakeTTY()) is False


def test_should_colorize_auto_respects_isatty():
    class NotATTY:
        def isatty(self):
            return False
    assert _xmlcolor.should_colorize("auto", NotATTY()) is False


# --- CLI tests --------------------------------------------------------

def test_cat_pretty_prints(xml_file):
    r = run(xml_file, "--color", "never")
    assert r.returncode == 0, r.stderr
    assert "<orders>" in r.stdout
    assert "  <order" in r.stdout  # indented


def test_cat_preserves_declaration(xml_file):
    r = run(xml_file, "--color", "never")
    assert r.stdout.startswith('<?xml version="1.0"?>')


def test_cat_custom_indent(xml_file):
    r = run(xml_file, "--color", "never", "--indent", "4")
    assert "\n    <order" in r.stdout


def test_cat_indent_zero_is_valid(xml_file):
    r = run(xml_file, "--color", "never", "--indent", "0")
    assert r.returncode == 0, r.stderr
    assert "\n<order" in r.stdout  # no leading spaces


def test_cat_negative_indent_rejected(xml_file):
    r = run(xml_file, "--indent", "-1")
    assert r.returncode == 2
    assert "must be >= 0" in r.stderr


def test_cat_color_never_has_no_ansi(xml_file):
    r = run(xml_file, "--color", "never")
    assert "\x1b[" not in r.stdout


def test_cat_color_always_has_ansi_if_colorama_present(xml_file):
    r = run(xml_file, "--color", "always")
    if _xmlcolor.HAVE_COLORAMA:
        assert "\x1b[" in r.stdout
    else:
        assert "\x1b[" not in r.stdout  # no crash, just plain


def test_cat_default_auto_no_ansi_when_piped(xml_file):
    # subprocess capture is never a tty, so auto must not emit codes
    r = run(xml_file)
    assert "\x1b[" not in r.stdout


def test_cat_from_stdin(xml_file):
    with open(xml_file) as f:
        content = f.read()
    r = run("-", "--color", "never", input=content)
    assert "<orders>" in r.stdout


def test_cat_output_to_file(xml_file, tmp_path):
    out = tmp_path / "pretty.xml"
    r = run(xml_file, "--color", "never", "-o", str(out))
    assert r.returncode == 0, r.stderr
    assert r.stdout == ""  # nothing on stdout when writing to a file
    assert "<orders>" in out.read_text()


def test_cat_output_to_file_auto_color_is_off(xml_file, tmp_path):
    # a file is never a terminal, so --color auto (the default) must
    # not emit ANSI codes into it even if colorama is installed
    out = tmp_path / "pretty.xml"
    run(xml_file, "-o", str(out))
    assert "\x1b[" not in out.read_text()


def test_cat_output_to_file_color_always_still_colorizes(xml_file, tmp_path):
    out = tmp_path / "pretty.xml"
    run(xml_file, "-o", str(out), "--color", "always")
    if _xmlcolor.HAVE_COLORAMA:
        assert "\x1b[" in out.read_text()


def test_cat_content_round_trips_ignoring_whitespace_and_color(xml_file):
    r = run(xml_file, "--color", "never")
    stripped = re.sub(r"\s+", "", r.stdout)
    assert 'status="shipped"' in r.stdout
    assert "acme" in stripped
