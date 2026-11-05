"""Tests for the `pygixml diff` and `pygixml similarity` CLI subcommands."""
import json
import subprocess
import sys

import pytest

import pygixml

OLD = "<ul class='m'><li>Home<li>About us<li>Blog</ul>"
NEW = "<ul class='m'><li>Home<li>About<li>Blog<li>Contact</ul>"


def run(*args, input=None):
    return subprocess.run(
        [sys.executable, "-m", "pygixml", *args], capture_output=True, text=True, input=input,
    )


@pytest.fixture
def pages(tmp_path):
    a, b = tmp_path / "old.html", tmp_path / "new.html"
    a.write_text(OLD, encoding="utf-8")
    b.write_text(NEW, encoding="utf-8")
    return str(a), str(b)


def test_diff_prints_one_line_per_action(pages):
    r = run("diff", *pages)
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines() == [
        "insert   /ul[1] @3  <li>Contact</li>",
        'update   /ul[1]/li[2]/text()[1]  "About us" -> "About"',
    ]


def test_diff_text_diff_shows_a_word_level_diff(pages):
    r = run("diff", *pages, "--text-diff")
    assert "About[- us-]" in r.stdout


def test_diff_json_is_the_action_list(pages):
    r = run("diff", *pages, "--json")
    out = json.loads(r.stdout)
    expected = pygixml.diff(pygixml.parse_html(OLD), pygixml.parse_html(NEW))
    assert [o["action"] for o in out] == [type(x).__name__ for x in expected]
    assert out[0] == {"action": "Insert", "parent": "/ul[1]", "position": 3, "xml": "<li>Contact</li>"}


def test_diff_exit_codes(pages):
    a, b = pages
    assert run("diff", a, b).returncode == 0                       # a diff is not an error
    assert run("diff", a, b, "--exit-code").returncode == 1
    assert run("diff", a, a, "--exit-code").returncode == 0
    q = run("diff", a, b, "--quiet")
    assert q.returncode == 1 and q.stdout == ""
    assert run("diff", a, a, "-q").returncode == 0


def test_diff_reads_stdin_and_needs_from_there(pages):
    a, b = pages
    r = run("diff", "-", b, "--from", "html", input=OLD)
    assert r.returncode == 0 and "insert" in r.stdout
    assert run("diff", "-", b, input=OLD).returncode == 2          # format cannot be guessed
    assert run("diff", "-", "-", "--from", "html", input=OLD).returncode == 2


def test_diff_trouble_exits_2(tmp_path, pages):
    r = run("diff", pages[0], str(tmp_path / "missing.html"))
    assert r.returncode == 2 and "missing.html" in r.stderr
    notes = tmp_path / "notes.txt"
    notes.write_text("x")
    assert run("diff", str(notes), pages[0]).returncode == 2       # unknown extension
    bad = tmp_path / "bad.xml"
    bad.write_text("<a><b></a>")
    assert run("diff", str(bad), str(bad)).returncode == 2         # does not parse


def test_diff_xml_with_ignore_attrs(tmp_path):
    a, b = tmp_path / "a.xml", tmp_path / "b.xml"
    a.write_text('<r><i data-x="1" id="z">t</i></r>')
    b.write_text('<r><i data-x="2" id="z">t</i></r>')
    assert run("diff", str(a), str(b)).stdout.startswith("set")
    assert run("diff", str(a), str(b), "--ignore-attrs", "data-*", "--exit-code").returncode == 0


def test_diff_unicode_and_multiline_stay_on_one_line_each(tmp_path):
    a, b = tmp_path / "a.html", tmp_path / "b.html"
    a.write_text("<p>سلام دنیا</p>", encoding="utf-8")
    b.write_text("<p>سلام</p>", encoding="utf-8")
    r = run("diff", str(a), str(b))
    assert r.returncode == 0 and "سلام" in r.stdout and len(r.stdout.splitlines()) == 1


def test_similarity_matches_the_api(pages):
    a, b = pygixml.parse_html(OLD), pygixml.parse_html(NEW)
    r = run("similarity", *pages)
    assert r.returncode == 0 and r.stdout.strip() == f"{pygixml.similarity(a, b):.3f}"
    r = run("similarity", *pages, "--content", "--method", "paths")
    assert r.stdout.strip() == f"{pygixml.similarity(a, b, method='paths', content=True):.3f}"
    assert run("similarity", pages[0], pages[0]).stdout.strip() == "1.000"


def test_similarity_trouble_exits_2(tmp_path):
    assert run("similarity", str(tmp_path / "nope.xml"), str(tmp_path / "nope.xml")).returncode == 2


def test_unknown_subcommand_lists_the_new_ones():
    r = run("nope")
    assert "diff" in r.stderr and "similarity" in r.stderr
