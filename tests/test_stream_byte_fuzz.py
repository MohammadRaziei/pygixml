"""
Byte-for-byte fuzz test: jsonify.stream_dump vs jsonify.dumps_file, over
many random nested XML documents (deep nesting, attrs, force_list,
pretty-printing). Uses tmp_path so it works on every OS (the original
version of this test hardcoded /tmp, which doesn't exist on Windows).
"""
import random
from pygixml import jsonify

TAGS = ["a", "b", "c", "d", "e"]
N = 500  # random cases; kept modest so CI stays fast


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _gen_node(tag, depth, max_depth):
    attrs = f' id="{random.randint(1, 999)}"' if random.random() < 0.3 else ""
    if depth >= max_depth or random.random() < 0.3:
        text = f"v{random.randint(0, 9999)}" if random.random() < 0.9 else ""
        return f"<{tag}{attrs}>{_esc(text)}</{tag}>"
    children = []
    for _ in range(random.randint(1, 4)):
        ctag = random.choice(TAGS)
        for _ in range(random.choice([1, 1, 2, 2, 3, 4])):
            children.append(_gen_node(ctag, depth + 1, max_depth))
    if random.random() < 0.5:
        random.shuffle(children)
    return f"<{tag}{attrs}>" + "".join(children) + f"</{tag}>"


def test_stream_dump_byte_fuzz(tmp_path):
    xml_path = tmp_path / "bf.xml"
    json_path = tmp_path / "bf.json"

    for i in range(N):
        random.seed(i + 55555)
        xml = _gen_node("root", 0, random.randint(2, 6)).encode()
        xml_path.write_bytes(xml)

        stream_indent = random.choice([2, 4])
        dom_indent = " " * stream_indent
        force_list = random.choice([None, {"a"}, {"a", "b"}])
        kwargs_dom = dict(pretty=True, indent=dom_indent)
        kwargs_stream = dict(indent=stream_indent)
        if force_list is not None:
            kwargs_dom["force_list"] = force_list
            kwargs_stream["force_list"] = force_list

        expected = jsonify.dumps_file(str(xml_path), **kwargs_dom)
        jsonify.stream_dump(str(xml_path), str(json_path), **kwargs_stream)
        got = json_path.read_text()

        assert got == expected, (
            f"byte mismatch at case {i} (kwargs_dom={kwargs_dom})\n"
            f" xml:      {xml[:500]!r}\n"
            f" expected: {expected!r}\n"
            f" got:      {got!r}"
        )
