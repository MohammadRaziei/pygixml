"""
Tests for pygixml.formats.FormatDocument (the to_json/to_yaml/to_toon/
to_xml + from_* class) and the `pygixml convert` CLI built on it.
"""
import json
import subprocess
import sys

import pytest

from pygixml.formats import FormatDocument

XML = '<order id="7"><customer>acme</customer><items><item>a</item><item>b</item></items></order>'
EXPECTED_DICT = {
    "order": {
        "@id": "7",
        "customer": "acme",
        "items": {"item": ["a", "b"]},
    }
}


# --- FormatDocument: XML ---------------------------------------------

def test_from_xml_parses_into_expected_dict():
    doc = FormatDocument.from_xml(XML)
    assert doc.data == EXPECTED_DICT


def test_to_xml_roundtrips():
    doc = FormatDocument(EXPECTED_DICT)
    xml_out = doc.to_xml()
    doc2 = FormatDocument.from_xml(xml_out)
    assert doc2.data == EXPECTED_DICT


def test_to_xml_wraps_data_without_single_root_key():
    # {"a": 1, "b": 2} has two top-level keys -- not valid as-is for XML
    doc = FormatDocument({"a": 1, "b": 2})
    xml_out = doc.to_xml(root_tag="wrapped")
    assert xml_out.strip().startswith("<wrapped>") or "<wrapped>" in xml_out
    doc2 = FormatDocument.from_xml(xml_out)
    assert doc2.data == {"wrapped": {"a": "1", "b": "2"}}


def test_to_xml_pretty(tmp_path):
    doc = FormatDocument(EXPECTED_DICT)
    out = doc.to_xml(pretty=True)
    assert "\n" in out


# --- FormatDocument: JSON ----------------------------------------------

def test_json_roundtrip():
    doc = FormatDocument(EXPECTED_DICT)
    text = doc.to_json()
    doc2 = FormatDocument.from_json(text)
    assert doc2.data == EXPECTED_DICT


def test_json_pretty_has_newlines():
    doc = FormatDocument(EXPECTED_DICT)
    assert "\n" in doc.to_json(pretty=True)
    assert "\n" not in doc.to_json(pretty=False)


# --- FormatDocument: YAML ----------------------------------------------

def test_yaml_roundtrip():
    pytest.importorskip("yaml")
    doc = FormatDocument(EXPECTED_DICT)
    text = doc.to_yaml()
    doc2 = FormatDocument.from_yaml(text)
    assert doc2.data == EXPECTED_DICT


# --- FormatDocument: TOON ----------------------------------------------

def test_toon_roundtrip():
    pytest.importorskip("ctoon")
    doc = FormatDocument(EXPECTED_DICT)
    text = doc.to_toon()
    doc2 = FormatDocument.from_toon(text)
    assert doc2.data == EXPECTED_DICT


# --- Missing optional dependency: clear error, not a crash --------------

def test_missing_yaml_gives_clear_error(monkeypatch):
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name == "yaml":
            raise ModuleNotFoundError("No module named 'yaml'")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    doc = FormatDocument({"x": 1})
    with pytest.raises(ImportError, match="pip install PyYAML"):
        doc.to_yaml()
    with pytest.raises(ImportError, match="pip install PyYAML"):
        FormatDocument.from_yaml("x: 1")


def test_missing_ctoon_gives_clear_error(monkeypatch):
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name == "ctoon":
            raise ModuleNotFoundError("No module named 'ctoon'")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    doc = FormatDocument({"x": 1})
    with pytest.raises(ImportError, match="pip install ctoon"):
        doc.to_toon()


# --- generic dispatch ---------------------------------------------------

def test_to_format_and_from_format_dispatch():
    doc = FormatDocument(EXPECTED_DICT)
    text = doc.to_format("json")
    doc2 = FormatDocument.from_format(text, "json")
    assert doc2.data == EXPECTED_DICT


def test_to_format_unknown_raises():
    doc = FormatDocument({"x": 1})
    with pytest.raises(ValueError):
        doc.to_format("yamlll")


# --- pygixml convert CLI -------------------------------------------------

def run(*args, input=None):
    return subprocess.run(
        [sys.executable, "-m", "pygixml", "convert", *args],
        capture_output=True, text=True, input=input,
    )


@pytest.fixture
def xml_file(tmp_path):
    p = tmp_path / "data.xml"
    p.write_text(XML)
    return str(p)


def test_convert_xml_to_json_via_extension(xml_file, tmp_path):
    out = tmp_path / "data.json"
    r = run(xml_file, "-o", str(out))
    assert r.returncode == 0, r.stderr
    assert json.loads(out.read_text()) == EXPECTED_DICT


def test_convert_json_to_xml_via_extension(tmp_path):
    jf = tmp_path / "data.json"
    jf.write_text(json.dumps(EXPECTED_DICT))
    out = tmp_path / "data.xml"
    r = run(str(jf), "-o", str(out))
    assert r.returncode == 0, r.stderr
    assert FormatDocument.from_xml(out.read_text()).data == EXPECTED_DICT


def test_convert_stdout_requires_to(xml_file):
    r = run(xml_file)
    assert r.returncode == 2
    assert "--to" in r.stderr


def test_convert_stdin_requires_from(xml_file):
    with open(xml_file) as f:
        content = f.read()
    r = run("-", "--to", "json", input=content)
    assert r.returncode == 2
    assert "--from" in r.stderr


def test_convert_stdin_with_explicit_from(xml_file):
    with open(xml_file) as f:
        content = f.read()
    r = run("-", "--from", "xml", "--to", "json", input=content)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == EXPECTED_DICT


def test_convert_pretty_json(xml_file):
    r = run(xml_file, "--to", "json", "--pretty")
    assert "\n" in r.stdout


def test_convert_unknown_extension_needs_from(xml_file, tmp_path):
    weird = tmp_path / "data.weird"
    weird.write_text(XML)
    r = run(str(weird), "--to", "json")
    assert r.returncode == 2
    assert "--from" in r.stderr


def test_convert_yaml_roundtrip_via_cli(tmp_path):
    pytest.importorskip("yaml")
    xf = tmp_path / "d.xml"
    xf.write_text(XML)
    yf = tmp_path / "d.yaml"
    r = run(str(xf), "-o", str(yf))
    assert r.returncode == 0, r.stderr
    r2 = run(str(yf), "--to", "json")
    assert json.loads(r2.stdout) == EXPECTED_DICT


# --- public API exposure -------------------------------------------------

def test_formats_exposed_on_pygixml_package():
    import pygixml
    assert pygixml.formats is not None
    assert pygixml.formats.FormatDocument is FormatDocument
    assert "formats" in pygixml.__all__
