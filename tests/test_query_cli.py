"""
Tests for the pygixml.query CLI (pygixq) -- covers the two bugs found
and fixed manually: (1) argparse's files/query split being clobbered
by a leftover manual re-split, and (2) the dotted-path executor
treating the first segment (the root's own tag) as a real child-descent
step when objectify.from_file/from_string already return the root
element itself.
"""
import subprocess
import sys
import pytest

XML = """<database>
  <user_profile id="101">
    <first_name>Ali</first_name>
    <age>30</age>
  </user_profile>
  <entry>one</entry>
  <entry>two</entry>
  <entry>three</entry>
  <config><host>localhost</host></config>
</database>
"""


@pytest.fixture
def xml_file(tmp_path):
    p = tmp_path / "db.xml"
    p.write_text(XML)
    return str(p)


def run_cli(*args, input=None):
    return subprocess.run(
        [sys.executable, "-m", "pygixml.query", *args],
        capture_output=True, text=True, input=input,
    )


def test_cli_runs_at_all(xml_file):
    # regression test for the argparse files/query split bug: this used
    # to always fail with "Must provide at least one FILE and a QUERY."
    r = run_cli(xml_file, "//first_name")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "Ali"


def test_dotted_root_is_anchor_not_child(xml_file):
    # regression test: from_file() already returns the root element, so
    # ".database.user_profile.first_name" must not try root.database
    r = run_cli(xml_file, ".database.user_profile.first_name")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "Ali"


def test_dotted_attr(xml_file):
    r = run_cli(xml_file, ".database.user_profile.@id")
    assert r.stdout.strip() == "101"


def test_dotted_index(xml_file):
    r = run_cli(xml_file, ".database.entry[1]")
    assert r.stdout.strip() == "two"


def test_dotted_all(xml_file):
    r = run_cli(xml_file, ".database.entry[*]")
    assert r.stdout.split() == ["one", "two", "three"]


def test_dotted_text_fn(xml_file):
    r = run_cli(xml_file, ".database.user_profile.first_name.text()")
    assert r.stdout.strip() == "Ali"


def test_xpath_predicate(xml_file):
    r = run_cli(xml_file, "//user_profile[@id='101']/first_name")
    assert r.stdout.strip() == "Ali"


def test_json_format(xml_file):
    import json
    r = run_cli(xml_file, ".database.user_profile", "--format", "json")
    parsed = json.loads(r.stdout)
    assert parsed == {"user_profile": {"@id": "101", "first_name": "Ali", "age": "30"}}


def test_count(xml_file):
    r = run_cli(xml_file, ".database.entry[*]", "--count")
    assert r.stdout.strip() == "3"


def test_multi_file(xml_file):
    r = run_cli(xml_file, xml_file, ".database.config.host")
    assert r.stdout.split() == ["localhost", "localhost"]


def test_stdin(xml_file):
    with open(xml_file) as f:
        content = f.read()
    r = run_cli("-", ".database.config.host", input=content)
    assert r.stdout.strip() == "localhost"


def test_no_match_exit_code(xml_file):
    r = run_cli(xml_file, ".database.nope")
    assert r.returncode == 1
