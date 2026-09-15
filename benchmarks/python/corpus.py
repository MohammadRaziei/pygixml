"""
corpus.py — deterministic XML corpus generator for the pygixml
benchmark suite.

Methodology note (documented here, and in benchmarks/README.md): this
corpus is **synthetic but realistic**, not fetched from a real-world
dataset. It's generated deterministically (seeded) across several
common XML "genres" (RSS-like feeds, product catalogs, deep config
trees, flat record lists) at several sizes, plus a wide N-sweep used
specifically for the scaling/memory story. We chose synthetic
generation over fetching an external corpus so every genre's shape
(nesting depth, attribute density, repetition pattern) is known and
controllable — which matters here specifically because pygixml's
complexity characteristics (see docs/source/jsonify.rst) depend on
*shape*, not just size, and a benchmark that can't control shape can't
tell that story. Nothing here is tuned to make pygixml look good; the
generators were written once, from realistic examples, before any
numbers were collected.
"""
import random
import os


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# ---------------------------------------------------------------- RSS --

def gen_rss(n_items, seed=1):
    rnd = random.Random(seed)
    authors = ["A. Writer", "B. Reporter", "C. Editor", "D. Correspondent"]
    cats = ["world", "tech", "sports", "science", "business"]
    items = []
    for i in range(n_items):
        items.append(
            "<item>"
            f"<title>Story #{i}: {_esc('Something happened, allegedly')}</title>"
            f"<link>https://example.com/news/{i}</link>"
            f"<description>{_esc('A longer summary paragraph describing story ' + str(i) + ' in reasonable detail, as a real feed would.')}</description>"
            f"<pubDate>2026-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}T00:00:00Z</pubDate>"
            f"<author>{_esc(rnd.choice(authors))}</author>"
            f"<category>{_esc(rnd.choice(cats))}</category>"
            "</item>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<rss version="2.0"><channel>'
        "<title>Example Feed</title><link>https://example.com</link>"
        "<description>An example RSS feed for benchmarking</description>"
        + "".join(items) +
        "</channel></rss>"
    )


# -------------------------------------------------------- product catalog --

def gen_catalog(n_products, seed=2):
    rnd = random.Random(seed)
    cats = ["electronics", "home", "outdoors", "toys", "books"]
    products = []
    for i in range(n_products):
        n_attrs = rnd.randint(2, 5)
        attrs = "".join(
            f'<attribute name="{_esc(f"attr{j}")}">{_esc(rnd.randint(1, 999))}</attribute>'
            for j in range(n_attrs)
        )
        n_reviews = rnd.choice([0, 1, 1, 2, 3])
        reviews = "".join(
            f'<review rating="{rnd.randint(1,5)}">{_esc("Decent product, review " + str(r))}</review>'
            for r in range(n_reviews)
        )
        products.append(
            f'<product id="P{i:06d}" category="{_esc(rnd.choice(cats))}">'
            f"<name>{_esc(f'Product {i}')}</name>"
            f"<price currency=\"USD\">{rnd.uniform(1, 999):.2f}</price>"
            f"<in_stock>{'true' if rnd.random() > 0.2 else 'false'}</in_stock>"
            f"<attributes>{attrs}</attributes>"
            f"<reviews>{reviews}</reviews>"
            "</product>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<catalog>" + "".join(products) + "</catalog>"
    )


# ----------------------------------------------------------- config tree --

def gen_config(depth=6, breadth=4, seed=3):
    """Deeply nested, low-repetition tree (settings/config file shape)."""
    rnd = random.Random(seed)
    counter = [0]

    def node(level):
        counter[0] += 1
        tag = f"section{counter[0]}"
        if level >= depth:
            return f"<{tag}>{_esc(rnd.choice(['true', 'false', str(rnd.randint(0, 9999)), 'default']))}</{tag}>"
        children = "".join(node(level + 1) for _ in range(breadth))
        attrs = f' env="{_esc(rnd.choice(["prod", "dev", "staging"]))}"' if rnd.random() < 0.3 else ""
        return f"<{tag}{attrs}>{children}</{tag}>"

    return '<?xml version="1.0" encoding="UTF-8"?><config>' + node(0) + "</config>"


# ------------------------------------------------------------ flat records --

def gen_records(n, seed=4):
    """The classic record-list shape: <root><record>...</record>...</root>,
    one repeated tag per level -- the shape almost all real giant XML
    actually has, and the shape pygixml.jsonify.stream_dump is O(n) for."""
    rnd = random.Random(seed)
    statuses = ["pending", "shipped", "delivered", "cancelled"]
    recs = []
    for i in range(n):
        recs.append(
            f'<order id="{i}" status="{rnd.choice(statuses)}">'
            f"<customer>customer_{i % 500}</customer>"
            f"<items>"
            f'<item><sku>SKU{i}</sku><qty>{rnd.randint(1, 9)}</qty></item>'
            f'<item><sku>SKU{i+1}</sku><qty>{rnd.randint(1, 5)}</qty></item>'
            f"</items>"
            f"<total>{i * 1.5:.2f}</total>"
            "</order>"
        )
    return '<?xml version="1.0" encoding="UTF-8"?><orders>' + "".join(recs) + "</orders>"


def gen_interleaved(n, seed=5):
    """The adversarial shape: two *different* repeated tags interleaved
    at the same level -- the one documented case where
    jsonify.stream_dump's time can approach O(n^2). Used only in the
    'under the hood' scaling story, not the general throughput corpus."""
    parts = ['<?xml version="1.0" encoding="UTF-8"?><root>']
    for i in range(n):
        parts.append(f"<sale>{i}</sale><tax>{i * 0.1:.2f}</tax>")
    parts.append("</root>")
    return "".join(parts)


GENRES = {
    "rss": gen_rss,
    "catalog": gen_catalog,
    "records": gen_records,
}

SIZES = {
    "small": 100,
    "medium": 1_000,
    "large": 10_000,
}


def write_corpus(out_dir):
    """Write the multi-genre throughput corpus (genre x size) plus one
    fixed deep config tree. Returns a list of {genre, size, path, bytes}."""
    os.makedirs(out_dir, exist_ok=True)
    manifest = []

    for genre_name, gen_fn in GENRES.items():
        for size_name, n in SIZES.items():
            xml = gen_fn(n)
            path = os.path.join(out_dir, f"{genre_name}_{size_name}.xml")
            with open(path, "w", encoding="utf-8") as f:
                f.write(xml)
            manifest.append({
                "genre": genre_name, "size": size_name, "n": n,
                "path": path, "bytes": len(xml.encode("utf-8")),
            })

    cfg = gen_config()
    cfg_path = os.path.join(out_dir, "config_deep.xml")
    with open(cfg_path, "w", encoding="utf-8") as f:
        f.write(cfg)
    manifest.append({
        "genre": "config", "size": "fixed", "n": None,
        "path": cfg_path, "bytes": len(cfg.encode("utf-8")),
    })

    return manifest


if __name__ == "__main__":
    import argparse
    import json

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("out_dir", help="directory to write the corpus .xml files + manifest.json into")
    args = p.parse_args()

    manifest = write_corpus(args.out_dir)

    manifest_path = os.path.join(args.out_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    for entry in manifest:
        print(f"{entry['genre']:10s} {str(entry['size']):8s} {entry['bytes']:>10,} bytes  {entry['path']}")
    print(f"manifest -> {manifest_path}")
