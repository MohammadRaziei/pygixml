import json, statistics, math
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parent.parent / "results"  # benchmarks/results, populated by `cmake --build build --target pygixml_benchmark`

throughput = json.load(open(R / "throughput.json"))
tmem = json.load(open(R / "throughput_memory.json"))
memory = json.load(open(R / "memory.json"))
scaling = json.load(open(R / "scaling.json"))
sizes = json.load(open(R / "sizes.json"))
sysinfo = json.load(open(R / "system_info.json"))
cli = json.load(open(R / "cli.json"))

GENRE_LABEL = {"rss": "RSS feed", "catalog": "product catalog", "records": "flat order records", "config": "deeply-nested config", "real_svg_icons": "real SVG icon set"}
SIZE_LABEL = {"small": "small", "medium": "medium", "large": "large", "fixed": "fixed"}


def point_label(row):
    g = GENRE_LABEL.get(row["genre"], row["genre"])
    s = SIZE_LABEL.get(row["size"], row["size"])
    return f'{g} / {s}'


def e_ratio(rows, op, target="pygixml", ref="lxml", field="seconds", from_="throughput"):
    """E[target/ref]: ratio at each matching data point, averaged across points."""
    ratios = []
    points = []
    for row in rows:
        libs = row[op] if from_ == "throughput" else row["libraries"]
        t = libs.get(target, {})
        rf = libs.get(ref, {})
        if not (t.get("available") and rf.get("available")):
            continue
        tv, rv = t[field], rf[field]
        if not tv or not rv:
            continue
        ratios.append(rv / tv)  # >1 means target is faster/smaller (ref/target)
        points.append({"label": point_label(row), "target": tv, "ref": rv, "ratio": rv / tv})
    if not ratios:
        return None
    return {"mean": statistics.mean(ratios), "n": len(ratios), "points": points}


def series_for_chart(rows, op, libs, field="seconds", from_="throughput"):
    labels = [point_label(r) for r in rows if op in r]
    out = {"labels": labels, "series": {}}
    for lib in libs:
        vals = []
        for r in rows:
            d = r[op] if from_ == "throughput" else r["libraries"]
            v = d.get(lib, {})
            vals.append(v[field] if v.get("available") else None)
        out["series"][lib] = vals
    return out


def throughput_series(rows, op, libs):
    """MB/s = bytes processed / seconds, per library per data point."""
    labels = [point_label(r) for r in rows if op in r]
    out = {"labels": labels, "series": {}}
    for lib in libs:
        vals = []
        for r in rows:
            if op not in r:
                continue
            v = r[op].get(lib, {})
            if v.get("available") and v.get("seconds"):
                vals.append((r["bytes"] / 1e6) / v["seconds"])
            else:
                vals.append(None)
        out["series"][lib] = vals
    return out


rows_t = throughput["results"]          # list with genre/size/bytes + op dicts
rows_m = {op: tmem[op] for op in tmem}  # each: list of {genre,size,bytes,libraries}

out = {"system_info": sysinfo, "repeats": throughput["repeats"]}

# ---------------- package sizes ----------------
out["sizes"] = sizes

# ---------------- Core Module: parse ----------------
out["core_parse"] = {
    "throughput": throughput_series(rows_t, "parse", ["pygixml", "lxml", "elementtree"]),
    "time": series_for_chart(rows_t, "parse", ["pygixml", "lxml", "elementtree"]),
    "memory": series_for_chart(rows_m["parse"], None, ["pygixml", "lxml", "elementtree"], field="peak_rss_mb", from_="mem"),
    "e_time_lxml": e_ratio(rows_t, "parse", ref="lxml"),
    "e_time_et": e_ratio(rows_t, "parse", ref="elementtree"),
    "e_mem_lxml": e_ratio(rows_m["parse"], None, ref="lxml", field="peak_rss_mb", from_="mem"),
    "e_mem_et": e_ratio(rows_m["parse"], None, ref="elementtree", field="peak_rss_mb", from_="mem"),
}

# ---------------- Core Module: iterparse ----------------
out["core_iterparse"] = {
    "throughput": throughput_series(rows_t, "iterparse", ["pygixml", "lxml", "elementtree"]),
    "time": series_for_chart(rows_t, "iterparse", ["pygixml", "lxml", "elementtree"]),
    "memory": series_for_chart(rows_m["iterparse"], None, ["pygixml", "lxml", "elementtree"], field="peak_rss_mb", from_="mem"),
    "e_time_lxml": e_ratio(rows_t, "iterparse", ref="lxml"),
    "e_time_et": e_ratio(rows_t, "iterparse", ref="elementtree"),
    "e_mem_lxml": e_ratio(rows_m["iterparse"], None, ref="lxml", field="peak_rss_mb", from_="mem"),
    "e_mem_et": e_ratio(rows_m["iterparse"], None, ref="elementtree", field="peak_rss_mb", from_="mem"),
}

# ---------------- Objectify ----------------
out["objectify"] = {
    "throughput": throughput_series(rows_t, "to_object", ["pygixml", "lxml"]),
    "time": series_for_chart(rows_t, "to_object", ["pygixml", "lxml"]),
    "memory": series_for_chart(rows_m["to_object"], None, ["pygixml", "lxml"], field="peak_rss_mb", from_="mem"),
    "e_time_lxml": e_ratio(rows_t, "to_object", ref="lxml"),
    "e_mem_lxml": e_ratio(rows_m["to_object"], None, ref="lxml", field="peak_rss_mb", from_="mem"),
}

# ---------------- Dictify: dict_convert ----------------
out["dictify_convert"] = {
    "throughput": throughput_series(rows_t, "dict_convert", ["pygixml", "xmltodict"]),
    "time": series_for_chart(rows_t, "dict_convert", ["pygixml", "xmltodict"]),
    "memory": series_for_chart(rows_m["dict_convert"], None, ["pygixml", "xmltodict"], field="peak_rss_mb", from_="mem"),
    "e_time_xmltodict": e_ratio(rows_t, "dict_convert", ref="xmltodict"),
    "e_mem_xmltodict": e_ratio(rows_m["dict_convert"], None, ref="xmltodict", field="peak_rss_mb", from_="mem"),
}
# ---------------- Dictify: dict_stream ----------------
out["dictify_stream"] = {
    "throughput": throughput_series(rows_t, "dict_stream", ["pygixml", "xmltodict"]),
    "time": series_for_chart(rows_t, "dict_stream", ["pygixml", "xmltodict"]),
    "memory": series_for_chart(rows_m["dict_stream"], None, ["pygixml", "xmltodict"], field="peak_rss_mb", from_="mem"),
    "e_time_xmltodict": e_ratio(rows_t, "dict_stream", ref="xmltodict"),
    "e_mem_xmltodict": e_ratio(rows_m["dict_stream"], None, ref="xmltodict", field="peak_rss_mb", from_="mem"),
}

# ---------------- Jsonify: json (whole document) ----------------
out["jsonify_json"] = {
    "throughput": throughput_series(rows_t, "xml_to_json", ["pygixml", "xmltodict", "xmljson"]),
    "time": series_for_chart(rows_t, "xml_to_json", ["pygixml", "xmltodict", "xmljson"]),
    "memory": series_for_chart(rows_m["xml_to_json"], None, ["pygixml", "xmltodict", "xmljson"], field="peak_rss_mb", from_="mem"),
    "e_time_xmltodict": e_ratio(rows_t, "xml_to_json", ref="xmltodict"),
    "e_time_xmljson": e_ratio(rows_t, "xml_to_json", ref="xmljson"),
    "e_mem_xmltodict": e_ratio(rows_m["xml_to_json"], None, ref="xmltodict", field="peak_rss_mb", from_="mem"),
    "e_mem_xmljson": e_ratio(rows_m["xml_to_json"], None, ref="xmljson", field="peak_rss_mb", from_="mem"),
}

# ---------------- Jsonify: jsonl (streaming, O(1) memory) ----------------
mem_points = memory["pygixml_stream_dump"]["points"]
out["jsonify_jsonl"] = {
    "memory_points": mem_points,  # n, peak_rss_mb, seconds -- flat regardless of n
    "scaling_records": scaling["pygixml_stream_dump"]["records_shape"],
    "scaling_interleaved": scaling["pygixml_stream_dump"]["interleaved_shape"],
}

# ---------------- CLI ----------------
out["cli"] = cli

out_path = HERE / "data.json"
json.dump(out, open(out_path, "w"), indent=2)
print(f"wrote {out_path}")
