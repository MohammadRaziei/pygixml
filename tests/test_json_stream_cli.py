"""
Tests for the `pygixml jsonify` (née `json`) and `pygixml stream` CLI
subcommands.
"""
import json
import subprocess
import sys
import pytest

ORDERS_XML = """<orders>
  <order status="shipped"><id>1</id><customer>acme</customer><total>150.5</total></order>
  <order status="pending"><id>2</id><customer>beta</customer><total>42.0</total></order>
  <order status="shipped"><id>3</id><customer>acme</customer><total>9.99</total></order>
</orders>
"""


@pytest.fixture
def orders_file(tmp_path):
    p = tmp_path / "orders.xml"
    p.write_text(ORDERS_XML)
    return str(p)


def run(*args, input=None):
    return subprocess.run(
        [sys.executable, "-m", "pygixml", *args],
        capture_output=True, text=True, input=input,
    )


# --- pygixml jsonify -------------------------------------------------

def test_json_compact_matches_dumps_file(orders_file):
    from pygixml import jsonify
    expected = jsonify.dumps_file(orders_file, pretty=False)
    r = run("jsonify", orders_file)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == expected


def test_json_pretty(orders_file):
    r = run("jsonify", orders_file, "-p")
    parsed = json.loads(r.stdout)
    assert parsed["orders"]["order"][0]["customer"] == "acme"
    assert "\n" in r.stdout  # actually pretty-printed


def test_json_to_output_file(orders_file, tmp_path):
    out = tmp_path / "out.json"
    r = run("jsonify", orders_file, "-o", str(out))
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text())
    assert len(data["orders"]["order"]) == 3


def test_json_forced_stream_matches_dom_mode(orders_file, tmp_path):
    out_dom = tmp_path / "dom.json"
    out_stream = tmp_path / "stream.json"
    run("jsonify", orders_file, "-o", str(out_dom), "--no-stream")
    run("jsonify", orders_file, "-o", str(out_stream), "--stream")
    assert out_dom.read_text() == out_stream.read_text()


def test_json_from_stdin(orders_file):
    with open(orders_file) as f:
        content = f.read()
    r = run("jsonify", "-", input=content)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["orders"]["order"][0]["customer"] == "acme"


def test_json_force_list_on_singleton(tmp_path):
    p = tmp_path / "single.xml"
    p.write_text("<root><item>only</item></root>")
    r = run("jsonify", str(p), "--force-list", "item")
    parsed = json.loads(r.stdout)
    assert parsed["root"]["item"] == ["only"]


def test_json_is_an_alias_for_jsonify(orders_file):
    r = run("json", orders_file)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["orders"]["order"][0]["customer"] == "acme"


# --- pygixml stream -------------------------------------------------

def test_stream_jsonl_all(orders_file):
    r = run("stream", orders_file, "--tag", "order")
    lines = [json.loads(l) for l in r.stdout.strip().splitlines()]
    assert len(lines) == 3
    assert r.returncode == 0


def test_stream_where_numeric_gt(orders_file):
    r = run("stream", orders_file, "--tag", "order", "--where", "total>100")
    lines = [json.loads(l) for l in r.stdout.strip().splitlines()]
    assert len(lines) == 1
    assert lines[0]["id"] == "1"


def test_stream_where_attr_eq(orders_file):
    r = run("stream", orders_file, "--tag", "order", "--where", "@status=shipped")
    lines = [json.loads(l) for l in r.stdout.strip().splitlines()]
    assert len(lines) == 2


def test_stream_multiple_where_are_anded(orders_file):
    r = run("stream", orders_file, "--tag", "order",
            "--where", "@status=shipped", "--where", "customer=acme")
    lines = [json.loads(l) for l in r.stdout.strip().splitlines()]
    assert len(lines) == 2
    assert all(l["customer"] == "acme" for l in lines)


def test_stream_format_array(orders_file):
    r = run("stream", orders_file, "--tag", "order",
            "--where", "total>100", "--format", "array")
    parsed = json.loads(r.stdout)
    assert isinstance(parsed, list)
    assert len(parsed) == 1


def test_stream_format_array_no_matches_is_valid_json(orders_file):
    r = run("stream", orders_file, "--tag", "order", "--where", "total>99999",
            "--format", "array")
    assert json.loads(r.stdout) == []


def test_stream_count(orders_file):
    r = run("stream", orders_file, "--tag", "order", "--where", "@status=shipped",
            "--count")
    assert r.stdout.strip() == "2"


def test_stream_limit(orders_file):
    r = run("stream", orders_file, "--tag", "order", "--limit", "1")
    lines = r.stdout.strip().splitlines()
    assert len(lines) == 1


def test_stream_from_stdin(orders_file):
    with open(orders_file) as f:
        content = f.read()
    r = run("stream", "-", "--tag", "order", "--where", "total<50", input=content)
    lines = [json.loads(l) for l in r.stdout.strip().splitlines()]
    assert len(lines) == 2


def test_stream_no_match_exit_code(orders_file):
    r = run("stream", orders_file, "--tag", "order", "--where", "total>99999")
    assert r.returncode == 1


def test_stream_bad_where_expr(orders_file):
    r = run("stream", orders_file, "--tag", "order", "--where", "nonsense_no_operator")
    assert r.returncode == 2


# --- dispatch / backward compat -------------------------------------

def test_unknown_subcommand():
    r = run("wat")
    assert r.returncode == 1
    assert "unknown subcommand" in r.stderr


def test_pygixq_still_works(orders_file):
    r = subprocess.run([sys.executable, "-m", "pygixml", "query",
                        orders_file, ".orders.order[0].customer"],
                        capture_output=True, text=True)
    assert r.stdout.strip() == "acme"
