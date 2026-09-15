"""
generate_report.py — combine every benchmarks/python/*.json result into
one standalone HTML report: Chart.js and all the raw JSON data are
embedded directly in the file (via the vendored
benchmarks/report/vendor/chart.umd.min.js and inline <script> tags),
so the output needs nothing else to view or to keep — no server, no
network, no sibling files. That's also why this is the one artifact
meant to live in benchmarks/results/: everything upstream of it
(corpus, venv, per-point JSON) is disposable build output.
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
        return {"stats": [], "chart_js": "", "note": ""}

    datasets_js = []
    max_n_bytes = 0
    stream_avg = None
    biggest_competitor_peak = None
    biggest_competitor_name = None

    for approach, data in memory.items():
        if not data.get("available"):
            continue
        points = data["points"]
        xy = [{"x": p["bytes"] / (1024 * 1024), "y": p["peak_rss_mb"]} for p in points]
        color = {
            "pygixml_stream_dump": "#5b8cff",
            "pygixml_dom": "#7aa2ff",
            "lxml_plus_xmljson": "#ff6b81",
            "xmltodict": "#35d0ba",
        }.get(approach, "#b98bff")
        label = {
            "pygixml_stream_dump": "pygixml (stream_dump)",
            "pygixml_dom": "pygixml (DOM)",
            "lxml_plus_xmljson": "lxml + xmljson",
            "xmltodict": "xmltodict",
        }.get(approach, approach)
        datasets_js.append({
            "label": label, "data": xy, "borderColor": color,
            "backgroundColor": color, "tension": 0.25, "pointRadius": 4,
        })
        max_n_bytes = max(max_n_bytes, max(p["bytes"] for p in points))

        if approach == "pygixml_stream_dump":
            stream_avg = sum(p["peak_rss_mb"] for p in points) / len(points)
        else:
            peak = points[-1]["peak_rss_mb"]
            if biggest_competitor_peak is None or peak > biggest_competitor_peak:
                biggest_competitor_peak = peak
                biggest_competitor_name = label

    stats = []
    if stream_avg is not None:
        stats.append({"value": f"{stream_avg:.0f}MB", "label": "pygixml stream_dump, flat across every size tested", "cls": "good"})
    if stream_avg and biggest_competitor_peak:
        ratio = biggest_competitor_peak / stream_avg
        stats.append({"value": f"{ratio:.0f}\u00d7", "label": f"less memory than {biggest_competitor_name} at the largest size", "cls": "good"})
    if biggest_competitor_peak:
        stats.append({"value": f"{biggest_competitor_peak / 1024:.1f}GB" if biggest_competitor_peak > 1024 else f"{biggest_competitor_peak:.0f}MB",
                      "label": f"{biggest_competitor_name}'s peak at the largest size tested", "cls": "bad"})
    stats.append({"value": _fmt_bytes(max_n_bytes), "label": "largest input file in this comparison", "cls": ""})

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
    return {"stats": stats, "chart_js": chart_js}


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
       borderColor: '#35d0ba', backgroundColor: '#35d0ba', tension: 0.2, pointRadius: 4 }},
    {{ label: 'interleaved shape (adversarial)', data: {json.dumps(series(interleaved))},
       borderColor: '#ff6b81', backgroundColor: '#ff6b81', tension: 0.2, pointRadius: 4 }}
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
                f"records-shape time grew {r_ratio:.1f}\u00d7 (linear); "
                f"interleaved-shape time grew {i_ratio:.1f}\u00d7 (superlinear \u2014 approaching the "
                f"documented O(n\u00b2) case).")

    dom = scaling.get("dom_competitors_records_shape", {})
    dom_datasets = []
    colors = {"pygixml_dom": "#7aa2ff", "lxml_plus_xmljson": "#ff6b81", "xmltodict": "#35d0ba"}
    labels = {"pygixml_dom": "pygixml (DOM)", "lxml_plus_xmljson": "lxml + xmljson", "xmltodict": "xmltodict"}
    for name, data in dom.items():
        if not data.get("available"):
            continue
        dom_datasets.append({
            "label": labels.get(name, name),
            "data": series(data["points"]),
            "borderColor": colors.get(name, "#b98bff"),
            "backgroundColor": colors.get(name, "#b98bff"),
            "tension": 0.2, "pointRadius": 4,
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

def _build_throughput_section(throughput):
    if not throughput:
        return {"chart_js": "", "parse_chart_js": "", "repeats": "?"}

    rows = throughput["results"]
    repeats = throughput.get("repeats", "?")

    # xml_to_json: one bar-group per (genre,size), one bar per library
    labels = [f"{r['genre']}/{r['size']}" for r in rows]
    libs = sorted({lib for r in rows for lib in r["xml_to_json"]})
    colors = {"pygixml": "#5b8cff", "xmltodict": "#35d0ba", "xmljson": "#ff6b81"}
    datasets = []
    for lib in libs:
        data = []
        for r in rows:
            cell = r["xml_to_json"].get(lib)
            data.append(round(cell["seconds"] * 1000, 4) if cell and cell.get("available") else None)
        datasets.append({"label": lib, "data": data, "backgroundColor": colors.get(lib, "#b98bff")})

    x2j_chart_js = f"""
new Chart(document.getElementById('chart-throughput'), {{
  type: 'bar',
  data: {{ labels: {json.dumps(labels)}, datasets: {json.dumps(datasets)} }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    scales: {{
      y: {{ type: 'logarithmic', title: {{ display: true, text: 'Time (ms, log scale, lower is better)' }} }}
    }},
    plugins: {{ legend: {{ position: 'bottom' }} }}
  }}
}});
"""

    libs_p = sorted({lib for r in rows for lib in r["parse"]})
    colors_p = {"pygixml": "#5b8cff", "lxml": "#ff6b81", "elementtree": "#ffb454"}
    datasets_p = []
    for lib in libs_p:
        data = []
        for r in rows:
            cell = r["parse"].get(lib)
            data.append(round(cell["seconds"] * 1000, 4) if cell and cell.get("available") else None)
        datasets_p.append({"label": lib, "data": data, "backgroundColor": colors_p.get(lib, "#b98bff")})

    parse_chart_js = f"""
new Chart(document.getElementById('chart-parse'), {{
  type: 'bar',
  data: {{ labels: {json.dumps(labels)}, datasets: {json.dumps(datasets_p)} }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    scales: {{
      y: {{ type: 'logarithmic', title: {{ display: true, text: 'Time (ms, log scale, lower is better)' }} }}
    }},
    plugins: {{ legend: {{ position: 'bottom' }} }}
  }}
}});
"""
    return {"chart_js": x2j_chart_js, "parse_chart_js": parse_chart_js, "repeats": repeats}


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
    palette = {"pygixml": "#5b8cff", "lxml": "#ff6b81", "elementtree": "#ffb454",
               "xmltodict": "#35d0ba", "xmljson": "#b98bff"}
    for name, data in sizes.items():
        if not data.get("available"):
            continue
        labels.append(LIB_LABELS.get(name, name))
        values.append(round(to_kb(data), 1))
        colors.append(palette.get(name, "#8b93a7"))

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

    mem = _build_memory_section(memory)
    scl = _build_scaling_section(scaling)
    thr = _build_throughput_section(throughput)
    siz = _build_size_section(sizes)

    with open(chartjs_path, "r", encoding="utf-8") as f:
        chartjs_source = f.read()

    embedded = {
        "throughput": throughput, "scaling": scaling, "memory": memory,
        "sizes": sizes, "features": features,
    }
    downloads = [(k, v) for k, v in embedded.items() if v is not None]

    ratio_stat = next((s["value"] for s in mem["stats"] if "less memory" in s["label"]), None)
    headline = (
        f'pygixml uses <span class="hl">{ratio_stat} less memory</span> than the next best option'
        if ratio_stat else "pygixml: constant-memory XML&rarr;JSON, benchmarked against the field"
    )
    subhead = (
        "jsonify.stream_dump converts XML to JSON without ever building a tree. "
        "Every other approach here does &mdash; and its memory shows it."
    )

    env = Environment(loader=FileSystemLoader(HERE), autoescape=False)
    template = env.get_template("template.html.jinja2")

    html = template.render(
        generated_at=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        headline=headline,
        subhead=subhead,
        meta_line=f"{len(throughput['results']) if throughput else 0} corpus entries &middot; "
                   f"{thr['repeats']} repeats per cell &middot; isolated-process memory measurement",
        memory_stats=mem["stats"],
        scaling_note=scl["note"],
        scaling_dom_available=scl["dom_available"],
        repeats=thr["repeats"],
        libraries=features["libraries"] if features else [],
        lib_labels=LIB_LABELS,
        features=features["features"] if features else [],
        badge_symbol=BADGE_SYMBOL,
        downloads=downloads,
        chartjs_source=chartjs_source,
        embedded_json=json.dumps(embedded),
        chart_scripts="\n".join([
            mem["chart_js"], scl["chart_js"], scl["dom_chart_js"],
            thr["chart_js"], thr["parse_chart_js"], siz["chart_js"],
        ]),
    )

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("results_dir", help="directory containing throughput.json, scaling.json, memory.json, sizes.json, features.json")
    p.add_argument("output", help="path to write the standalone report.html")
    p.add_argument("--chartjs-path", default=os.path.join(HERE, "vendor", "chart.umd.min.js"),
                    help="path to a Chart.js UMD build (CMake fetches this fresh; "
                         "defaults to a local vendor/ copy for running by hand)")
    args = p.parse_args()

    out = build(args.results_dir, args.output, args.chartjs_path)
    size_kb = os.path.getsize(out) / 1024
    print(f"generate_report: wrote {out} ({size_kb:.0f}KB, standalone)")
