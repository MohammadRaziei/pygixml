"""
generate_report.py — combine every benchmarks/python/*.json result into
one standalone HTML report: Chart.js and all the raw JSON data are
embedded directly in the file (via the vendored
benchmarks/report/vendor/chart.umd.min.js and inline <script> tags),
so the output needs nothing else to view or to keep -- no server, no
network, no sibling files. That's also why this is the one artifact
meant to live in benchmarks/results/: everything upstream of it
(corpus, venv, per-point JSON) is disposable build output.

What this file deliberately does NOT contain: how the corpus was
generated, why timing uses best-of-N, or the ru_maxrss/execve bug we
hit measuring memory. That's methodology and war stories for people
reading the source, not benchmark results for someone skimming a
report -- it lives in benchmarks/README.md instead. This file also
never computes an "N times better/less" ratio: pygixml and its
DOM-building competitors are on different complexity curves in the
memory/scaling story (O(1) vs O(n)), so any single ratio is only true
at the one input size it was computed from, and gets worse (in
pygixml's favor) as input grows -- the log-log chart shows that
honestly; a ratio badge would understate it.
"""
import argparse
import datetime
import json
import os

from jinja2 import Environment, FileSystemLoader

HERE = os.path.dirname(os.path.abspath(__file__))

BADGE_SYMBOL = {"yes": "\u2713", "no": "\u2715", "partial": "~"}
LIB_LABELS = {
    "pygixml": "pygixml",
    "lxml": "lxml",
    "elementtree": "ElementTree",
    "xmltodict": "xmltodict",
    "xmljson": "xmljson",
}
LIB_COLORS = {
    "pygixml": "#5b8cff",
    "pygixml_stream_dump": "#5b8cff",
    "pygixml_dom": "#7aa2ff",
    "lxml": "#ff6b81",
    "lxml_plus_xmljson": "#ff6b81",
    "elementtree": "#ffb454",
    "xmltodict": "#35d0ba",
    "xmljson": "#b98bff",
}
# Color is never the only way to tell two series apart here (colorblind
# readers can't rely on hue alone) -- every multi-series chart also
# varies point shape and/or line dash per library, keyed off this map.
LIB_POINT_STYLES = {
    "pygixml": "circle",
    "pygixml_stream_dump": "circle",
    "pygixml_dom": "circle",
    "lxml": "triangle",
    "lxml_plus_xmljson": "triangle",
    "elementtree": "rect",
    "xmltodict": "rectRot",
    "xmljson": "star",
}
LIB_DASH = {
    "pygixml": [],
    "pygixml_stream_dump": [],
    "pygixml_dom": [],
    "lxml": [6, 3],
    "lxml_plus_xmljson": [6, 3],
    "elementtree": [2, 2],
    "xmltodict": [8, 3, 2, 3],
    "xmljson": [1, 3],
}


def _fmt_bytes(n):
    for unit in ["B", "KB", "MB", "GB"]:
        if abs(n) < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def _load(path):
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


# ---------------------------------------------------------------- memory --

def _build_memory_section(memory):
    if not memory:
        return {"chart_js": "", "lede_extra": ""}

    datasets_js = []
    max_n_bytes = 0

    for approach, data in memory.items():
        if not data.get("available"):
            continue
        points = data["points"]
        xy = [{"x": p["bytes"] / (1024 * 1024), "y": p["peak_rss_mb"]} for p in points]
        color = LIB_COLORS.get(approach, "#b98bff")
        label = {
            "pygixml_stream_dump": "pygixml (stream_dump)",
            "pygixml_dom": "pygixml (DOM)",
            "lxml_plus_xmljson": "lxml + xmljson",
            "xmltodict": "xmltodict",
        }.get(approach, approach)
        datasets_js.append({
            "label": label, "data": xy, "borderColor": color,
            "backgroundColor": color, "tension": 0.25, "pointRadius": 5,
            "pointStyle": LIB_POINT_STYLES.get(approach, "circle"),
            "borderDash": LIB_DASH.get(approach, []),
        })
        max_n_bytes = max(max_n_bytes, max(p["bytes"] for p in points))

    chart_js = f"""
new Chart(document.getElementById('chart-memory'), {{
  type: 'line',
  data: {{ datasets: {json.dumps(datasets_js)} }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    scales: {{
      x: {{ type: 'logarithmic', title: {{ display: true, text: 'Input file size (MB, log scale)' }} }},
      y: {{ type: 'logarithmic', title: {{ display: true, text: 'Peak RSS (MB, log scale)' }} }}
    }},
    plugins: {{ legend: {{ position: 'bottom' }} }}
  }}
}});
"""
    lede_extra = (
        f" Largest file in this comparison: {_fmt_bytes(max_n_bytes)}."
        if max_n_bytes else ""
    )
    return {"chart_js": chart_js, "lede_extra": lede_extra}


# --------------------------------------------------------------- scaling --

def _build_scaling_section(scaling):
    if not scaling:
        return {"chart_js": "", "dom_chart_js": "", "dom_available": False, "note": ""}

    sd = scaling.get("pygixml_stream_dump", {})
    records = sd.get("records_shape", [])
    interleaved = sd.get("interleaved_shape", [])

    def series(points):
        return [{"x": p["n"], "y": p["seconds"]} for p in points]

    chart_js = f"""
new Chart(document.getElementById('chart-scaling'), {{
  type: 'line',
  data: {{ datasets: [
    {{ label: 'records shape (realistic)', data: {json.dumps(series(records))},
       borderColor: '#35d0ba', backgroundColor: '#35d0ba', tension: 0.2, pointRadius: 5,
       pointStyle: 'circle', borderDash: [] }},
    {{ label: 'interleaved shape (adversarial)', data: {json.dumps(series(interleaved))},
       borderColor: '#ff6b81', backgroundColor: '#ff6b81', tension: 0.2, pointRadius: 5,
       pointStyle: 'triangle', borderDash: [6, 3] }}
  ]}},
  options: {{
    responsive: true, maintainAspectRatio: false,
    scales: {{
      x: {{ type: 'logarithmic', title: {{ display: true, text: 'N (elements, log scale)' }} }},
      y: {{ type: 'logarithmic', title: {{ display: true, text: 'Time (seconds, log scale)' }} }}
    }},
    plugins: {{ legend: {{ position: 'bottom' }} }}
  }}
}});
"""

    note = ""
    if len(records) >= 2 and len(interleaved) >= 2:
        r_ratio = records[-1]["seconds"] / records[0]["seconds"]
        n_ratio = records[-1]["n"] / records[0]["n"]
        i_ratio = interleaved[-1]["seconds"] / interleaved[0]["seconds"]
        note = (f"N grew {n_ratio:.0f}\u00d7 ({records[0]['n']:,} \u2192 {records[-1]['n']:,}): "
                f"records-shape time grew {r_ratio:.1f}\u00d7 (linear, tracks N); "
                f"interleaved-shape time grew {i_ratio:.1f}\u00d7 (superlinear \u2014 approaching the "
                f"documented O(n\u00b2) case). The slope, not a single ratio, is the finding.")

    dom = scaling.get("dom_competitors_records_shape", {})
    dom_datasets = []
    for name, data in dom.items():
        if not data.get("available"):
            continue
        dom_datasets.append({
            "label": {"pygixml_dom": "pygixml (DOM)", "lxml_plus_xmljson": "lxml + xmljson",
                      "xmltodict": "xmltodict"}.get(name, name),
            "data": series(data["points"]),
            "borderColor": LIB_COLORS.get(name, "#b98bff"),
            "backgroundColor": LIB_COLORS.get(name, "#b98bff"),
            "tension": 0.2, "pointRadius": 5,
            "pointStyle": LIB_POINT_STYLES.get(name, "circle"),
            "borderDash": LIB_DASH.get(name, []),
        })

    dom_chart_js = ""
    if dom_datasets:
        dom_chart_js = f"""
new Chart(document.getElementById('chart-scaling-dom'), {{
  type: 'line',
  data: {{ datasets: {json.dumps(dom_datasets)} }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    scales: {{
      x: {{ type: 'logarithmic', title: {{ display: true, text: 'N (elements, log scale)' }} }},
      y: {{ type: 'logarithmic', title: {{ display: true, text: 'Time (seconds, log scale)' }} }}
    }},
    plugins: {{ legend: {{ position: 'bottom' }} }}
  }}
}});
"""

    return {"chart_js": chart_js, "dom_chart_js": dom_chart_js,
            "dom_available": bool(dom_datasets), "note": note}


# ------------------------------------------------------------ throughput --
# pygixml is not "a JSON library" -- every one of its independent
# conversion layers gets its own panel here: raw DOM (parse), dict
# (dictify, vs xmltodict), lazy object (objectify, vs lxml.objectify),
# and end-to-end JSON (jsonify, vs the field). Each panel gets both a
# per-corpus-entry TIME chart and a size-vs-THROUGHPUT (MB/s) chart --
# two different questions ("how long did this take" vs "does the rate
# hold up as files get bigger") deserve two chart types, not one
# doing double duty.

OP_META = [
    {
        "key": "parse",
        "title": "parse — build a tree from the XML string, discard it",
        "note": "xmltodict/xmljson have no separate \u201cparse to a tree\u201d step "
                "distinct from \u201cparse straight to dict\u201d, so they don't appear here.",
    },
    {
        "key": "dict_convert",
        "title": "dict_convert — pygixml.dictify vs xmltodict",
        "note": "Both sides use the same convention (@-prefixed attributes, #text for mixed "
                "content) so the dicts they produce are structurally identical, not just "
                "\u201cboth happen to be a dict.\u201d",
    },
    {
        "key": "to_object",
        "title": "to_object — pygixml.objectify vs lxml.objectify",
        "note": "Lazy attribute-style access (root.child.grandchild), matched against lxml's "
                "own objectify submodule -- a real feature both libraries ship, not an "
                "improvised comparison.",
    },
    {
        "key": "xml_to_json",
        "title": "xml_to_json — pygixml.jsonify vs the field, end to end",
        "note": "ElementTree has no built-in dict/JSON conversion at all -- a real gap for it, "
                "not an oversight in this chart.",
    },
]


def _build_throughput_section(throughput):
    if not throughput:
        return {"ops": [], "repeats": "?"}

    rows = throughput["results"]
    repeats = throughput.get("repeats", "?")
    labels = [f"{r['genre']}/{r['size']}" for r in rows]

    ops_out = []
    for meta in OP_META:
        key = meta["key"]
        libs = sorted({lib for r in rows for lib in r.get(key, {})})
        if not libs:
            continue

        # Dot plot (Cleveland-style), not a bar chart: times here span
        # multiple orders of magnitude (a few ms for a small file to
        # hundreds of ms for a large one), and a bar's LENGTH only means
        # anything on a linear, zero-based scale. Force that same data
        # into a log-scaled bar and the bar lengths stop being
        # comparable to each other -- exactly the "non-zero baseline /
        # distorted length" anti-pattern. A dot plot encodes each value
        # as a POSITION instead, so a log x-axis stays honest: position
        # is the single most perceptually accurate encoding there is
        # (Cleveland & McGill, 1984), and works at any scale.
        dot_datasets = []
        tp_datasets = []
        for lib in libs:
            dot_points = []
            tp_points = []
            for label, r in zip(labels, rows):
                cell = r.get(key, {}).get(lib)
                if cell and cell.get("available"):
                    secs = cell["seconds"]
                    dot_points.append({"x": round(secs * 1000, 4), "y": label})
                    mb = r["bytes"] / (1024 * 1024)
                    tp_points.append({"x": round(mb, 4), "y": round(mb / secs, 2) if secs > 0 else None})
            color = LIB_COLORS.get(lib, "#8b93a7")
            style = LIB_POINT_STYLES.get(lib, "circle")
            if dot_points:
                dot_datasets.append({
                    "label": LIB_LABELS.get(lib, lib), "data": dot_points,
                    "backgroundColor": color, "borderColor": color,
                    "pointStyle": style, "pointRadius": 7, "pointHoverRadius": 9,
                    "showLine": False,
                })
            if tp_points:
                tp_datasets.append({
                    "label": LIB_LABELS.get(lib, lib), "data": tp_points,
                    "borderColor": color, "backgroundColor": color,
                    "pointStyle": style, "showLine": False,
                    "pointRadius": 6, "pointHoverRadius": 8,
                })

        dot_chart_js = f"""
new Chart(document.getElementById('chart-time-{key}'), {{
  type: 'scatter',
  data: {{ datasets: {json.dumps(dot_datasets)} }},
  options: {{
    indexAxis: 'y',
    responsive: true, maintainAspectRatio: false,
    scales: {{
      x: {{ type: 'logarithmic', title: {{ display: true, text: 'Time (ms, log scale, lower is better)' }} }},
      y: {{ type: 'category', labels: {json.dumps(labels)}, offset: true,
            grid: {{ color: 'rgba(255,255,255,0.04)' }} }}
    }},
    plugins: {{ legend: {{ position: 'bottom' }} }}
  }}
}});
"""
        tp_chart_js = f"""
new Chart(document.getElementById('chart-tp-{key}'), {{
  type: 'scatter',
  data: {{ datasets: {json.dumps(tp_datasets)} }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    scales: {{
      x: {{ type: 'logarithmic', title: {{ display: true, text: 'Input size (MB, log scale)' }} }},
      y: {{ title: {{ display: true, text: 'Throughput (MB/s, higher is better)' }} }}
    }},
    plugins: {{ legend: {{ position: 'bottom' }} }}
  }}
}});
""" if tp_datasets else ""

        ops_out.append({
            "key": key, "title": meta["title"], "note": meta["note"],
            "time_chart_js": dot_chart_js, "tp_chart_js": tp_chart_js,
            "has_tp_chart": bool(tp_datasets),
        })

    return {"ops": ops_out, "repeats": repeats}


# ------------------------------------------------------------------ size --

def _build_size_section(sizes):
    if not sizes:
        return {"chart_js": ""}

    def to_kb(data):
        s = data.get("total_size", "0 B")
        num, unit = s.split()
        num = float(num)
        return {"B": num / 1024, "KB": num, "MB": num * 1024, "GB": num * 1024 * 1024}.get(unit, 0)

    labels, values, colors = [], [], []
    for name, data in sizes.items():
        if not data.get("available"):
            continue
        labels.append(LIB_LABELS.get(name, name))
        values.append(round(to_kb(data), 1))
        colors.append(LIB_COLORS.get(name, "#8b93a7"))

    chart_js = f"""
new Chart(document.getElementById('chart-size'), {{
  type: 'bar',
  data: {{ labels: {json.dumps(labels)}, datasets: [{{
    label: 'Install size (KB)', data: {json.dumps(values)}, backgroundColor: {json.dumps(colors)}
  }}] }},
  options: {{
    indexAxis: 'y',
    responsive: true, maintainAspectRatio: false,
    scales: {{ x: {{ title: {{ display: true, text: 'KB (real wheel size, incl. deps)' }} }} }},
    plugins: {{ legend: {{ display: false }} }}
  }}
}});
"""
    return {"chart_js": chart_js}


def build(results_dir, output_path, chartjs_path):
    throughput = _load(os.path.join(results_dir, "throughput.json"))
    scaling = _load(os.path.join(results_dir, "scaling.json"))
    memory = _load(os.path.join(results_dir, "memory.json"))
    sizes = _load(os.path.join(results_dir, "sizes.json"))
    features = _load(os.path.join(results_dir, "features.json"))
    system_info = _load(os.path.join(results_dir, "system_info.json"))

    mem = _build_memory_section(memory)
    scl = _build_scaling_section(scaling)
    thr = _build_throughput_section(throughput)
    siz = _build_size_section(sizes)

    with open(chartjs_path, "r", encoding="utf-8") as f:
        chartjs_source = f.read()

    embedded = {
        "throughput": throughput, "scaling": scaling, "memory": memory,
        "sizes": sizes, "features": features, "system_info": system_info,
    }

    headline = "pygixml, measured honestly"
    subhead = (
        "Every conversion layer pygixml ships &mdash; raw pugixml parsing, dictify, "
        "objectify, jsonify &mdash; benchmarked against lxml, ElementTree, xmltodict, "
        "and xmljson, on the same corpus, with the same methodology throughout."
    )

    chart_scripts = [mem["chart_js"], scl["chart_js"], scl["dom_chart_js"], siz["chart_js"]]
    for op in thr["ops"]:
        chart_scripts.append(op["time_chart_js"])
        chart_scripts.append(op["tp_chart_js"])

    env = Environment(loader=FileSystemLoader(HERE), autoescape=False)
    template = env.get_template("template.html.jinja2")

    html = template.render(
        generated_at=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        headline=headline,
        subhead=subhead,
        meta_line=f"{len(throughput['results']) if throughput else 0} corpus entries &middot; "
                   f"{thr['repeats']} repeats per cell",
        memory_available=bool(memory),
        memory_lede_extra=mem["lede_extra"],
        scaling_note=scl["note"],
        scaling_dom_available=scl["dom_available"],
        throughput_ops=thr["ops"],
        repeats=thr["repeats"],
        libraries=features["libraries"] if features else [],
        lib_labels=LIB_LABELS,
        features=features["features"] if features else [],
        badge_symbol=BADGE_SYMBOL,
        has_memory=bool(memory), has_scaling=bool(scaling), has_throughput=bool(throughput),
        has_sizes=bool(sizes), has_features=bool(features),
        system_info=system_info,
        chartjs_source=chartjs_source,
        embedded_json=json.dumps(embedded),
        chart_scripts="\n".join(chart_scripts),
    )

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("results_dir", help="directory containing throughput.json, scaling.json, memory.json, sizes.json, features.json, system_info.json")
    p.add_argument("output", help="path to write the standalone report.html")
    p.add_argument("--chartjs-path", default=os.path.join(HERE, "vendor", "chart.umd.min.js"),
                    help="path to a Chart.js UMD build (CMake fetches this fresh; "
                         "defaults to a local vendor/ copy for running by hand)")
    args = p.parse_args()

    out = build(args.results_dir, args.output, args.chartjs_path)
    size_kb = os.path.getsize(out) / 1024
    print(f"generate_report: wrote {out} ({size_kb:.0f}KB, standalone)")
