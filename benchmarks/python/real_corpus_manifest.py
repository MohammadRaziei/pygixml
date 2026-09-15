"""
real_corpus_manifest.py — turn a directory of real-world XML files
(fetched by CMake, see benchmarks/cmake/FetchRealCorpus.cmake) into a
manifest.json in the same shape corpus.py's synthetic corpus uses, so
bench_throughput.py can run against real and synthetic data through
the exact same code path.

Source is Bootstrap Icons (github.com/twbs/icons) -- SVG is XML; this
is real, production, MIT-licensed markup, not generated for this
benchmark. Individual icon files are tiny (a few hundred bytes each),
so rather than feed thousands of individual manifest entries into a
7-repeat timing loop, files are grouped into three size buckets
(small/medium/large, by file count) and each bucket's files are
concatenated under one wrapping root -- producing exactly three
combined documents, the same shape as each synthetic genre/size cell.
"""
import argparse
import glob
import json
import os


def _wrap(paths):
    body = []
    for path in paths:
        with open(path, "r", encoding="utf-8") as f:
            body.append(f.read())
    return '<?xml version="1.0" encoding="UTF-8"?><real_icons>' + "".join(body) + "</real_icons>"


def build_manifest(corpus_dir, out_dir, bucket_max_files=400):
    files = sorted(glob.glob(os.path.join(corpus_dir, "**", "*.svg"), recursive=True))
    if not files:
        return []

    n = len(files)
    files.sort(key=os.path.getsize)
    thirds = [files[: n // 3], files[n // 3: 2 * n // 3], files[2 * n // 3:]]
    names = ["small", "medium", "large"]

    os.makedirs(out_dir, exist_ok=True)
    manifest = []
    for size_name, group in zip(names, thirds):
        sample = group[:bucket_max_files] or files[:1]
        xml = _wrap(sample)
        path = os.path.join(out_dir, f"real_svg_icons_{size_name}.xml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(xml)
        manifest.append({
            "genre": "real_svg_icons", "size": size_name, "n": len(sample),
            "path": path, "bytes": len(xml.encode("utf-8")),
        })
    return manifest


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("corpus_dir", help="directory of real .svg files (already downloaded/extracted by CMake)")
    p.add_argument("out_dir", help="directory to write the combined per-bucket .xml files into")
    p.add_argument("output", help="path to write manifest.json")
    args = p.parse_args()

    manifest = build_manifest(args.corpus_dir, args.out_dir)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    for entry in manifest:
        print(f"{entry['genre']:16s} {entry['size']:8s} {entry['n']:>4d} files  "
              f"{entry['bytes']:>10,} bytes  {entry['path']}")
    print(f"manifest -> {args.output}")
