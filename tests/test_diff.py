"""
Tests for pygixml.diff / is_equal / signature / similarity.

The key test is an independent reference patcher: it applies the edit script
to a plain-Python tree model (using only the documented path/position
semantics) and the result must equal the target tree.
"""
import random
import re
import xml.etree.ElementTree as ET

import pytest

import pygixml
from pygixml import (Delete, DeleteAttrib, Insert, InsertText, Move, SetAttrib,
                     UpdateText)


# --------------------------------------------------------------- reference model

def collapse(s):
    return " ".join(s.split())


def model(el, drop=()):
    """ElementTree element -> ('e', tag, attrs, children) / ('t', text)."""
    kids = []
    if el.text and collapse(el.text):
        kids.append(["t", collapse(el.text)])
    for c in el:
        kids.append(model(c, drop))
        if c.tail and collapse(c.tail):
            kids.append(["t", collapse(c.tail)])
    attrs = {k: v for k, v in el.attrib.items() if k not in drop}
    return ["e", el.tag, attrs, kids]


def top_model(xml):
    return [model(ET.fromstring(xml))]


def frozen(nodes):
    return tuple(
        ("t", n[1]) if n[0] == "t" else ("e", n[1], tuple(sorted(n[2].items())), frozen(n[3]))
        for n in nodes
    )


STEP = re.compile(r"^(.*)\[(\d+)\]$")


def find(top, path):
    """(siblings list, index) of the node at `path` in the model."""
    siblings, idx = top, None
    for step in path.strip("/").split("/"):
        if idx is not None:
            siblings = siblings[idx][3]
        name, k = STEP.match(step).groups()
        count = 0
        for i, n in enumerate(siblings):
            if (name == "text()" and n[0] == "t") or (n[0] == "e" and n[1] == name):
                count += 1
                if count == int(k):
                    idx = i
                    break
        else:
            raise AssertionError(f"path not found: {path}")
    return siblings, idx


def children_of(top, path):
    if path == "/":
        return top
    siblings, idx = find(top, path)
    return siblings[idx][3]


def apply(top, actions):
    for a in actions:
        if isinstance(a, Insert):
            children_of(top, a.parent).insert(a.position, model(ET.fromstring(a.xml)))
        elif isinstance(a, InsertText):
            children_of(top, a.parent).insert(a.position, ["t", a.text])
        elif isinstance(a, Delete):
            siblings, idx = find(top, a.path)
            del siblings[idx]
        elif isinstance(a, Move):
            siblings, idx = find(top, a.path)
            node = siblings.pop(idx)
            children_of(top, a.parent).insert(a.position, node)
        elif isinstance(a, UpdateText):
            siblings, idx = find(top, a.path)
            assert siblings[idx][1] == a.old
            siblings[idx][1] = a.text
        elif isinstance(a, SetAttrib):
            siblings, idx = find(top, a.path)
            assert siblings[idx][2].get(a.name) == a.old
            siblings[idx][2][a.name] = a.value
        elif isinstance(a, DeleteAttrib):
            siblings, idx = find(top, a.path)
            assert siblings[idx][2].pop(a.name) == a.old
        else:
            raise AssertionError(a)
    return top


def check(a_xml, b_xml, **kw):
    actions = pygixml.diff(pygixml.parse_string(a_xml), pygixml.parse_string(b_xml), **kw)
    got = apply(top_model(a_xml), actions)
    assert frozen(got) == frozen(top_model(b_xml)), (a_xml, b_xml, actions)
    return actions


# ------------------------------------------------------------------- basics

def test_identical_documents_give_empty_script():
    xml = "<r><a x='1'>t</a><b/></r>"
    assert pygixml.diff(pygixml.parse_string(xml), pygixml.parse_string(xml)) == []


def test_text_update_with_character_diff():
    acts = check("<d><p>Hello brave world</p></d>", "<d><p>Hello new world</p></d>", text_diff=True)
    assert len(acts) == 1 and isinstance(acts[0], UpdateText)
    assert acts[0].path == "/d[1]/p[1]/text()[1]"
    assert acts[0].diff == [(0, "Hello "), (-1, "brave"), (1, "new"), (0, " world")]
    assert check("<d><p>a</p></d>", "<d><p>b</p></d>")[0].diff is None


def test_word_diff_in_other_scripts():
    def pieces(a, b):
        return check(f"<d><p>{a}</p></d>", f"<d><p>{b}</p></d>", text_diff=True)[0].diff
    assert pieces("سلام دنیای زیبا", "سلام دنیای قشنگ") == [(0, "سلام دنیای "), (-1, "زیبا"), (1, "قشنگ")]
    assert pieces("你好世界", "你好地球") == [(0, "你好"), (-1, "世界"), (1, "地球")]
    assert pieces("say 😀 now", "say 😀😀 later") == [(0, "say 😀"), (1, "😀"), (0, " "), (-1, "now"), (1, "later")]


def test_reorder_is_one_move_not_delete_plus_insert():
    acts = check("<ul><li>a</li><li>b</li><li>c</li></ul>", "<ul><li>c</li><li>a</li><li>b</li></ul>")
    assert [type(a) for a in acts] == [Move]


def test_insert_delete_and_whole_subtree_in_one_action():
    acts = check("<r><p>x</p></r>", "<r><p>x</p><q><z/><z>t</z></q></r>")
    assert acts == [Insert("/r[1]", 1, "<q><z/><z>t</z></q>")]
    acts = check("<r><p>x</p><q>y</q></r>", "<r/>")
    assert acts == [Delete("/r[1]/p[1]"), Delete("/r[1]/q[1]")]


def test_attribute_actions():
    acts = check("<r a='1' b='2'/>", "<r b='3' c='4'/>")
    assert set(acts) == {DeleteAttrib("/r[1]", "a", "1"), SetAttrib("/r[1]", "b", "3", "2"),
                         SetAttrib("/r[1]", "c", "4", None)}


def test_moved_subtree_to_another_parent():
    acts = check("<r><s><i>keep me</i><j>and me</j></s><t/></r>", "<r><s/><t><i>keep me</i><j>and me</j></t></r>")
    assert all(isinstance(a, Move) for a in acts)
    acts = check("<r><s><i>keep me</i><j>and me</j></s><t/></r>", "<r><s/><t><i>keep me</i><j>and me</j></t></r>", moves=False)
    assert any(isinstance(a, Delete) for a in acts) and any(isinstance(a, Insert) for a in acts)


def test_keys_pair_elements_wherever_they_are():
    acts = check("<r><a id='1'><x>1</x></a><a id='2'><x>2</x></a></r>",
                 "<r><a id='2'><x>2</x></a><a id='1' k='v'><x>1</x></a></r>")
    assert {type(a) for a in acts} == {Move, SetAttrib}


def test_top_level_fragments_and_mixed_content():
    check("<p>a <b>x</b> c</p>", "<p>a <b>y</b> c <i>z</i></p>")
    pa, pb = pygixml.parse_html("<p>one<p>two"), pygixml.parse_html("<p>one<p>2<p>three")
    assert pygixml.diff(pa, pb)


# ------------------------------------------------------------ normalisation

def test_is_equal_normalisation_options():
    parse = pygixml.parse_html
    a = parse('<div class="b a" style="x" data-k="1"><p>one  two\n</p><!-- c --></div>')
    b = parse('<div data-k="2" style="y" class="a  b a"><p> one two </p></div>')
    assert not pygixml.is_equal(a, b)
    assert not pygixml.is_equal(a, b, ignore_attrs=["style"])
    assert pygixml.is_equal(a, b, ignore_attrs=["style", "data-*"])
    assert not pygixml.is_equal(a, b, ignore_attrs=["style", "data-*"], class_as_set=False)
    assert not pygixml.is_equal(a, b, ignore_attrs="style data-k".split(), ignore_whitespace=False)
    assert pygixml.diff(a, b, ignore_attrs=["style", "data-*"]) == []


def test_comments_can_be_compared():
    a, b = pygixml.parse_html("<p>x<!-- one --></p>"), pygixml.parse_html("<p>x<!-- two --></p>")
    assert pygixml.is_equal(a, b)
    assert not pygixml.is_equal(a, b, ignore_comments=False)
    acts = pygixml.diff(a, b, ignore_comments=False)
    assert len(acts) == 1 and isinstance(acts[0], UpdateText) and acts[0].path.endswith("comment()[1]")


def test_xmlnode_arguments_and_errors():
    d = pygixml.parse_string("<r><a>1</a></r>")
    assert pygixml.diff(d.root, d.root) == []
    with pytest.raises(pygixml.PygiXMLDiffError, match="XMLNode or XMLDocument"):
        pygixml.diff("<r/>", d)
    null = d.root.child("missing")
    with pytest.raises(pygixml.PygiXMLDiffError, match="null"):
        pygixml.is_equal(null, d)
    with pytest.raises(pygixml.PygiXMLDiffError):
        pygixml.diff(d, d, threshold=2)
    assert issubclass(pygixml.PygiXMLDiffError, pygixml.PygiXMLError)


# ------------------------------------------------------------------- fuzz

TAGS = ["a", "b", "li", "p", "div"]
WORDS = ["red", "blue", "fast", "slow", "big", "tiny", "x1", "y2"]


def random_tree(r, depth=0):
    el = ET.Element(r.choice(TAGS))
    if r.random() < 0.3:
        el.set(r.choice(["id", "k", "m"]), str(r.randint(1, 6)))
    if depth < 3:
        for _ in range(r.randint(0, 4)):
            if r.random() < 0.3:
                t = " ".join(r.choice(WORDS) for _ in range(r.randint(1, 4)))
                if len(el):
                    el[-1].tail = (el[-1].tail or "") + " " + t
                else:
                    el.text = (el.text or "") + t
            else:
                el.append(random_tree(r, depth + 1))
    return el


def mutate(r, root):
    els = list(root.iter())
    for _ in range(r.randint(1, 5)):
        op = r.choice(["text", "attr", "delete", "insert", "move", "swap"])
        els = list(root.iter())
        target = r.choice(els)
        parents = {c: p for p in root.iter() for c in p}
        if op == "text":
            target.text = " ".join(r.choice(WORDS) for _ in range(r.randint(1, 4)))
        elif op == "attr":
            target.set(r.choice(["id", "k", "m"]), str(r.randint(1, 6)))
        elif op == "delete" and target is not root:
            parents[target].remove(target)
        elif op == "insert":
            target.insert(r.randint(0, len(target)), random_tree(r, 2))
        elif op == "move" and target is not root:
            dest = r.choice(els)
            anc = dest
            while anc is not None and anc is not target:
                anc = parents.get(anc)
            if anc is None:                      # dest is not inside target
                parents[target].remove(target)
                dest.insert(r.randint(0, len(dest)), target)
        elif op == "swap" and len(target) >= 2:
            kids = list(target)
            r.shuffle(kids)
            for k in kids:
                target.remove(k)
            for k in kids:
                target.append(k)
    return root


@pytest.mark.parametrize("seed", range(5))
@pytest.mark.parametrize("opts", [{}, {"moves": False}, {"keys": ()}, {"threshold": 0.9}])
def test_fuzz_script_reproduces_target(seed, opts):
    r = random.Random(seed)
    for _ in range(40):
        a = random_tree(r)
        b = mutate(r, ET.fromstring(ET.tostring(a)))
        axml, bxml = ET.tostring(a, encoding="unicode"), ET.tostring(b, encoding="unicode")
        check(axml, bxml, **opts)
        assert pygixml.diff(pygixml.parse_string(axml), pygixml.parse_string(axml)) == []


def test_fuzz_unrelated_trees():
    r = random.Random(99)
    for _ in range(60):
        check(ET.tostring(random_tree(r), encoding="unicode"), ET.tostring(random_tree(r), encoding="unicode"))


# --------------------------------------------------------------- embedding

A = "<doc><h1>T</h1><ul><li>a</li><li>b</li></ul><p>text <b>x</b></p></doc>"
SAME_SHAPE = "<doc><h1>Other</h1><ul><li>c</li><li>d</li></ul><p>words <b>y</b></p></doc>"
OTHER = "<table><tr><td>1</td><td>2</td></tr><tr><td>3</td><td>4</td></tr></table>"


@pytest.mark.parametrize("method", ["pqgram", "paths"])
def test_similarity_properties(method):
    a, same, other = (pygixml.parse_string(x) for x in (A, SAME_SHAPE, OTHER))
    s = lambda x, y, **kw: pygixml.similarity(x, y, method=method, **kw)
    assert s(a, a) == 1.0
    assert s(a, same) == 1.0                         # structure only: text is ignored
    assert s(a, same, content=True) < 1.0            # ...unless content is asked for
    assert s(a, other) < 0.5 < s(a, same)
    assert s(a, other) == s(other, a)                # symmetric
    assert 0.0 <= s(a, other) <= 1.0


def test_small_edit_keeps_similarity_high():
    a = pygixml.parse_string(A)
    b = pygixml.parse_string(A.replace("<li>b</li>", "<li>b</li><li>c</li>"))
    assert 0.8 < pygixml.similarity(a, b) < 1.0


def test_signature_is_a_sparse_count_vector():
    sig = pygixml.signature(pygixml.parse_string(A))
    assert sig and all(isinstance(k, int) and v >= 1 for k, v in sig.items())
    assert sig == pygixml.signature(pygixml.parse_string(A))
    assert sig != pygixml.signature(pygixml.parse_string(OTHER))
    assert sum(pygixml.signature(pygixml.parse_string(A), method="paths").values()) == 13   # one path per node: 12 + the document


def test_embedding_normalisation_and_errors():
    a, b = pygixml.parse_html("<p class='a b'>x</p>"), pygixml.parse_html("<p> <!--c--> class</p>")
    assert pygixml.similarity(a, a) == 1.0 and pygixml.similarity(b, b) == 1.0
    with pytest.raises(pygixml.PygiXMLDiffError, match="method"):
        pygixml.signature(a, method="nope")
    with pytest.raises(pygixml.PygiXMLDiffError):
        pygixml.signature(a, p=0)
    with pytest.raises(pygixml.PygiXMLDiffError):
        pygixml.similarity(a, "x")
