import random, json
from pygixml import jsonify

TAGS = ["a", "b", "c", "d", "e"]

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def gen_node(tag, depth, max_depth, pretty):
    attrs = f' id="{random.randint(1,999)}"' if random.random() < 0.3 else ""
    if depth >= max_depth or random.random() < 0.3:
        text = f"v{random.randint(0,9999)}" if random.random() < 0.9 else ""
        return f"<{tag}{attrs}>{esc(text)}</{tag}>"
    children = []
    for _ in range(random.randint(1, 4)):
        ctag = random.choice(TAGS)
        for _ in range(random.choice([1, 1, 2, 2, 3, 4])):
            children.append(gen_node(ctag, depth + 1, max_depth, pretty))
    if random.random() < 0.5:
        random.shuffle(children)
    return f"<{tag}{attrs}>" + "".join(children) + f"</{tag}>"

fails = 0
N = 2000
for i in range(N):
    random.seed(i + 55555)
    xml = gen_node("root", 0, random.randint(2, 6), True).encode()
    with open('/tmp/bf.xml', 'wb') as f:
        f.write(xml)

    stream_indent = random.choice([2, 4])
    dom_indent = " " * stream_indent
    force_list = random.choice([None, {"a"}, {"a", "b"}])
    kwargs_dom = dict(pretty=True, indent=dom_indent)
    kwargs_stream = dict(indent=stream_indent)
    if force_list is not None:
        kwargs_dom["force_list"] = force_list
        kwargs_stream["force_list"] = force_list

    expected = jsonify.dumps_file('/tmp/bf.xml', **kwargs_dom)
    jsonify.stream_dump('/tmp/bf.xml', '/tmp/bf.json', **kwargs_stream)
    got = open('/tmp/bf.json').read()

    if got != expected:
        print(f"[{i}] BYTE MISMATCH kwargs_dom={kwargs_dom}")
        print(" xml:", xml[:500])
        print(" expected:", repr(expected))
        print(" got:     ", repr(got))
        fails += 1
        if fails >= 5:
            break

print(f"byte-fuzz fails: {fails}/{N}")
