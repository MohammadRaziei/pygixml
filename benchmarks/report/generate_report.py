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

LIB_LABELS = {
    "pygixml": "pygixml",
    "lxml": "lxml",
    "elementtree": "ElementTree",
    "xmltodict": "xmltodict",
    "xmljson": "xmljson",
}
LIB_COLORS = {
    "pygixml": "#e67225",
    "pygixml_stream_dump": "#e67225",
    "pygixml_dom": "#f2954f",
    "lxml": "#ff6b81",
    "lxml_plus_xmljson": "#ff6b81",
    "elementtree": "#5b8cff",
    "xmltodict": "#35d0ba",
    "xmljson": "#b98bff",
}
# Color is never the only way to tell two series apart here (colorblind
# readers can't rely on hue alone) -- every multi-series chart also
# varies point shape and/or line dash per library, keyed off this map.
LIB_POINT_STYLES = {
    "pygixml": "circle",
    "pygixml_stream_dump": "circle",
    "pygixml_dom": "rectRot",
    "lxml": "triangle",
    "lxml_plus_xmljson": "triangle",
    "elementtree": "rect",
    "xmltodict": "star",
    "xmljson": "crossRot",
}
LIB_DASH = {
    "pygixml": [],
    "pygixml_stream_dump": [],
    "pygixml_dom": [4, 2],
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
        return {"chart_js": "", "speed_chart_js": "", "lede_extra": "", "has_speed": False}

    datasets_js = []
    speed_datasets_js = []
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

        # Same isolated-process runs, same input files -- so the timing
        # they also recorded is a fair speed comparison for stream_dump
        # specifically (not the DOM-based xml_to_json operation in the
        # throughput section, which is a different code path).
        if all("seconds" in p and p["seconds"] is not None for p in points):
            sxy = [{"x": p["bytes"] / (1024 * 1024), "y": p["seconds"]} for p in points]
            speed_datasets_js.append({
                "label": label, "data": sxy, "borderColor": color,
                "backgroundColor": color, "tension": 0.25, "pointRadius": 5,
                "pointStyle": LIB_POINT_STYLES.get(approach, "circle"),
                "borderDash": LIB_DASH.get(approach, []),
            })

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

    speed_chart_js = ""
    if speed_datasets_js:
        speed_chart_js = f"""
new Chart(document.getElementById('chart-memory-speed'), {{
  type: 'line',
  data: {{ datasets: {json.dumps(speed_datasets_js)} }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    scales: {{
      x: {{ type: 'logarithmic', title: {{ display: true, text: 'Input file size (MB, log scale)' }} }},
      y: {{ type: 'logarithmic', title: {{ display: true, text: 'Time (seconds, log scale, lower is better)' }} }}
    }},
    plugins: {{ legend: {{ position: 'bottom' }} }}
  }}
}});
"""

    lede_extra = (
        f" Largest file in this comparison: {_fmt_bytes(max_n_bytes)}."
        if max_n_bytes else ""
    )
    return {"chart_js": chart_js, "speed_chart_js": speed_chart_js,
            "lede_extra": lede_extra, "has_speed": bool(speed_datasets_js)}


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


def _fmt_ms(x):
    if x < 1:
        return f"{x:.3f}ms"
    if x < 10:
        return f"{x:.2f}ms"
    return f"{x:.1f}ms"


def _build_throughput_section(throughput, throughput_memory):
    if not throughput:
        return {"ops": [], "repeats": "?"}

    rows = throughput["results"]
    repeats = throughput.get("repeats", "?")
    labels = [f"{r['genre']}/{r['size']}" for r in rows]
    throughput_memory = throughput_memory or {}

    ops_out = []
    for meta in OP_META:
        key = meta["key"]
        libs = sorted({lib for r in rows for lib in r.get(key, {})})
        if not libs:
            continue

        # Index this operation's memory rows by (genre, size) so they
        # line up with throughput.json's rows regardless of ordering.
        mem_by_entry = {}
        for mrow in throughput_memory.get(key, []):
            mem_by_entry[(mrow["genre"], mrow["size"])] = mrow.get("libraries", {})

        # One small, honest bar chart PER CORPUS ENTRY, not one chart
        # trying to hold all of them at once. Within a single entry, the
        # 2-3 competing libraries' times are within the same order of
        # magnitude, so a plain LINEAR, zero-baseline bar chart is
        # accurate (no log-scale trick needed) *and* instantly readable:
        # the shortest bar just wins, full stop -- no axis-reading
        # required. Small multiples, not one overloaded chart, is how
        # you compare many groups at once without hiding anything.
        entries = []
        wins = {lib: 0 for lib in libs}
        all_times = {lib: [] for lib in libs}
        all_mem = {lib: [] for lib in libs}
        mem_wins = {lib: 0 for lib in libs}
        time_trend_points = {lib: [] for lib in libs}
        mem_trend_points = {lib: [] for lib in libs}
        n_comparisons = 0
        n_mem_comparisons = 0

        for i, (label, r) in enumerate(zip(labels, rows)):
            cells = [(lib, r.get(key, {}).get(lib)) for lib in libs]
            cells = [(lib, c) for lib, c in cells if c and c.get("available")]
            if not cells:
                continue
            cells.sort(key=lambda lc: lc[1]["seconds"])  # fastest first
            n_comparisons += 1
            winner_lib = cells[0][0]
            wins[winner_lib] += 1
            for lib, c in cells:
                all_times[lib].append(c["seconds"])
                time_trend_points[lib].append({"x": round(r["bytes"] / (1024 * 1024), 4),
                                                "y": round(c["seconds"] * 1000, 4)})

            bar_labels = [LIB_LABELS.get(lib, lib) for lib, _ in cells]
            bar_ms = [round(c["seconds"] * 1000, 4) for _, c in cells]
            bar_colors = [LIB_COLORS.get(lib, "#8b93a7") for lib, _ in cells]
            values_text = "  \u00b7  ".join(
                f"{LIB_LABELS.get(lib, lib)} {_fmt_ms(c['seconds'] * 1000)}" for lib, c in cells
            )

            entry_mem = mem_by_entry.get((r["genre"], r["size"]), {})
            mem_cells = [(lib, entry_mem.get(lib)) for lib, _ in cells]
            mem_cells = [(lib, m) for lib, m in mem_cells if m and m.get("available")]
            mem_text = ""
            if mem_cells:
                mem_cells_sorted = sorted(mem_cells, key=lambda lm: lm[1]["peak_rss_mb"])
                n_mem_comparisons += 1
                mem_wins[mem_cells_sorted[0][0]] += 1
                for lib, m in mem_cells:
                    all_mem[lib].append(m["peak_rss_mb"])
                    mem_trend_points[lib].append({"x": round(r["bytes"] / (1024 * 1024), 4),
                                                   "y": round(m["peak_rss_mb"], 2)})
                mem_text = "  \u00b7  ".join(
                    f"{LIB_LABELS.get(lib, lib)} {m['peak_rss_mb']:.1f}MB" for lib, m in mem_cells_sorted
                )

            chart_js = f"""
new Chart(document.getElementById('chart-time-{key}-{i}'), {{
  type: 'bar',
  data: {{ labels: {json.dumps(bar_labels)}, datasets: [{{
    data: {json.dumps(bar_ms)}, backgroundColor: {json.dumps(bar_colors)}
  }}] }},
  options: {{
    indexAxis: 'y',
    responsive: true, maintainAspectRatio: false,
    scales: {{
      x: {{ title: {{ display: true, text: 'ms' }} }},
      y: {{ grid: {{ display: false }} }}
    }},
    plugins: {{ legend: {{ display: false }} }}
  }}
}});
"""
            mem_chart_js = ""
            if mem_cells:
                mem_bar_labels = [LIB_LABELS.get(lib, lib) for lib, _ in mem_cells_sorted]
                mem_bar_vals = [round(m["peak_rss_mb"], 2) for _, m in mem_cells_sorted]
                mem_bar_colors = [LIB_COLORS.get(lib, "#8b93a7") for lib, _ in mem_cells_sorted]
                mem_chart_js = f"""
new Chart(document.getElementById('chart-mem-{key}-{i}'), {{
  type: 'bar',
  data: {{ labels: {json.dumps(mem_bar_labels)}, datasets: [{{
    data: {json.dumps(mem_bar_vals)}, backgroundColor: {json.dumps(mem_bar_colors)}
  }}] }},
  options: {{
    indexAxis: 'y',
    responsive: true, maintainAspectRatio: false,
    scales: {{
      x: {{ title: {{ display: true, text: 'MB' }} }},
      y: {{ grid: {{ display: false }} }}
    }},
    plugins: {{ legend: {{ display: false }} }}
  }}
}});
"""
            entries.append({"id": f"chart-time-{key}-{i}", "label": label,
                             "chart_js": chart_js, "values_text": values_text,
                             "mem_id": f"chart-mem-{key}-{i}" if mem_cells else None,
                             "mem_chart_js": mem_chart_js, "mem_text": mem_text})

        winner_summary = ""
        if n_comparisons:
            medians = {}
            import statistics
            for lib in libs:
                if all_times[lib]:
                    medians[lib] = statistics.median(all_times[lib])
            ranked = sorted(medians.items(), key=lambda kv: kv[1])
            top_lib, top_median = ranked[0]
            rest = ", ".join(f"{LIB_LABELS.get(lib, lib)} {_fmt_ms(m * 1000)}" for lib, m in ranked[1:])
            winner_summary = (
                f"Fastest on {wins[top_lib]} of {n_comparisons} corpus entries: "
                f"<strong>{LIB_LABELS.get(top_lib, top_lib)}</strong> "
                f"(median {_fmt_ms(top_median * 1000)})"
                + (f" \u2014 {rest} median" if rest else "") + "."
            )

        memory_summary = ""
        if n_mem_comparisons:
            import statistics
            mem_medians = {lib: statistics.median(vals) for lib, vals in all_mem.items() if vals}
            ranked_mem = sorted(mem_medians.items(), key=lambda kv: kv[1])
            top_mem_lib, top_mem_median = ranked_mem[0]
            rest_mem = ", ".join(f"{LIB_LABELS.get(lib, lib)} {m:.1f}MB" for lib, m in ranked_mem[1:])
            memory_summary = (
                f"Lowest peak memory on {mem_wins[top_mem_lib]} of {n_mem_comparisons} corpus entries: "
                f"<strong>{LIB_LABELS.get(top_mem_lib, top_mem_lib)}</strong> "
                f"(median {top_mem_median:.1f}MB)"
                + (f" \u2014 {rest_mem} median" if rest_mem else "") + "."
            )

        # Time-vs-size and memory-vs-size: the same "does the trend hold
        # as files grow" question the throughput chart answers, just for
        # the two other metrics -- same treatment (connected lines, log
        # x, one line per library) for consistency.
        def _trend_chart(canvas_id, points_by_lib, y_title, y_log):
            datasets = []
            for lib in libs:
                pts = sorted(points_by_lib.get(lib, []), key=lambda p: p["x"])
                if not pts:
                    continue
                color = LIB_COLORS.get(lib, "#8b93a7")
                datasets.append({
                    "label": LIB_LABELS.get(lib, lib), "data": pts,
                    "borderColor": color, "backgroundColor": color,
                    "pointStyle": LIB_POINT_STYLES.get(lib, "circle"),
                    "borderDash": LIB_DASH.get(lib, []),
                    "showLine": True, "tension": 0.25,
                    "pointRadius": 5, "pointHoverRadius": 8,
                })
            if not datasets:
                return "", False
            y_scale = "'logarithmic'" if y_log else "'linear'"
            js = f"""
new Chart(document.getElementById('{canvas_id}'), {{
  type: 'line',
  data: {{ datasets: {json.dumps(datasets)} }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    scales: {{
      x: {{ type: 'logarithmic', title: {{ display: true, text: 'Input size (MB, log scale)' }} }},
      y: {{ type: {y_scale}, title: {{ display: true, text: '{y_title}' }} }}
    }},
    plugins: {{ legend: {{ position: 'bottom' }} }}
  }}
}});
"""
            return js, True

        time_trend_chart_js, has_time_trend = _trend_chart(
            f"chart-time-trend-{key}", time_trend_points,
            "Time (ms, log scale, lower is better)", True)
        mem_trend_chart_js, has_mem_trend = _trend_chart(
            f"chart-mem-trend-{key}", mem_trend_points,
            "Peak memory (MB, lower is better)", False)

        # Throughput (MB/s) vs input size: same treatment as the
        # memory/scaling charts above -- connected lines, not bare dots,
        # so both the TREND per library (does the rate rise, fall, or
        # hold flat as files grow) and the comparison BETWEEN libraries
        # (whose line sits on top) read at a glance from the same plot.
        tp_datasets = []
        for lib in libs:
            tp_points = []
            for r in rows:
                cell = r.get(key, {}).get(lib)
                if cell and cell.get("available") and cell["seconds"] > 0:
                    mb = r["bytes"] / (1024 * 1024)
                    tp_points.append({"x": round(mb, 4), "y": round(mb / cell["seconds"], 2)})
            tp_points.sort(key=lambda p: p["x"])
            if tp_points:
                color = LIB_COLORS.get(lib, "#8b93a7")
                tp_datasets.append({
                    "label": LIB_LABELS.get(lib, lib), "data": tp_points,
                    "borderColor": color, "backgroundColor": color,
                    "pointStyle": LIB_POINT_STYLES.get(lib, "circle"),
                    "borderDash": LIB_DASH.get(lib, []),
                    "showLine": True, "tension": 0.25,
                    "pointRadius": 5, "pointHoverRadius": 8,
                })

        tp_chart_js = f"""
new Chart(document.getElementById('chart-tp-{key}'), {{
  type: 'line',
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
            "winner_summary": winner_summary,
            "memory_summary": memory_summary,
            "entries": entries,
            "time_trend_chart_js": time_trend_chart_js, "has_time_trend": has_time_trend,
            "mem_trend_chart_js": mem_trend_chart_js, "has_mem_trend": has_mem_trend,
            "tp_chart_js": tp_chart_js,
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
    throughput_memory = _load(os.path.join(results_dir, "throughput_memory.json"))
    scaling = _load(os.path.join(results_dir, "scaling.json"))
    memory = _load(os.path.join(results_dir, "memory.json"))
    sizes = _load(os.path.join(results_dir, "sizes.json"))
    system_info = _load(os.path.join(results_dir, "system_info.json"))

    mem = _build_memory_section(memory)
    scl = _build_scaling_section(scaling)
    thr = _build_throughput_section(throughput, throughput_memory)
    siz = _build_size_section(sizes)

    with open(chartjs_path, "r", encoding="utf-8") as f:
        chartjs_source = f.read()

    embedded = {
        "throughput": throughput, "throughput_memory": throughput_memory, "scaling": scaling,
        "memory": memory, "sizes": sizes, "system_info": system_info,
    }

    headline = "pygixml, measured honestly"
    subhead = (
        "Every conversion layer pygixml ships &mdash; raw pugixml parsing, dictify, "
        "objectify, jsonify &mdash; benchmarked against lxml, ElementTree, xmltodict, "
        "and xmljson, on the same corpus, with the same methodology throughout."
    )

    chart_scripts = [mem["chart_js"], mem["speed_chart_js"], scl["chart_js"], scl["dom_chart_js"], siz["chart_js"]]
    for op in thr["ops"]:
        for entry in op["entries"]:
            chart_scripts.append(entry["chart_js"])
            chart_scripts.append(entry["mem_chart_js"])
        chart_scripts.append(op["time_trend_chart_js"])
        chart_scripts.append(op["mem_trend_chart_js"])
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
        memory_has_speed=mem["has_speed"],
        scaling_note=scl["note"],
        scaling_dom_available=scl["dom_available"],
        throughput_ops=thr["ops"],
        repeats=thr["repeats"],
        has_memory=bool(memory), has_scaling=bool(scaling), has_throughput=bool(throughput),
        has_throughput_memory=bool(throughput_memory),
        has_sizes=bool(sizes),
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
    p.add_argument("results_dir", help="directory containing throughput.json, scaling.json, memory.json, sizes.json, system_info.json")
    p.add_argument("output", help="path to write the standalone report.html")
    p.add_argument("--chartjs-path", default=os.path.join(HERE, "vendor", "chart.umd.min.js"),
                    help="path to a Chart.js UMD build (CMake fetches this fresh; "
                         "defaults to a local vendor/ copy for running by hand)")
    args = p.parse_args()

    out = build(args.results_dir, args.output, args.chartjs_path)
    size_kb = os.path.getsize(out) / 1024
    print(f"generate_report: wrote {out} ({size_kb:.0f}KB, standalone)")
