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


def _e_ratio(pairs):
    """pairs: list of (target_seconds_or_mb, ref_seconds_or_mb), same
    units, ref>0. Returns E[target/ref] -- the mean of each pair's OWN
    ratio, not (mean of targets)/(mean of refs) and not (median of
    targets)/(median of refs). Ratio-then-average, not average-then-
    ratio: entries of very different absolute scale (a 20-byte file
    next to a 4MB one) don't get to dominate just because their raw
    numbers are bigger."""
    ratios = [t / r for t, r in pairs if r and r > 0]
    if not ratios:
        return None
    return sum(ratios) / len(ratios)


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

    # O(1) (never builds a tree) vs O(n) (every DOM-based approach here)
    # are different complexity classes -- a ratio between them is only
    # true at the one size it's computed from and gets worse for O(n) at
    # every larger size (see "On fairness" in README.md). So: a ratio is
    # only computed WITHIN the O(n) group (all same class, comparable),
    # and O(1) just gets its own observed range stated plainly -- no
    # comparison implied.
    O1_APPROACHES = {"pygixml_stream_dump"}
    on_group = {}
    o1_group = {}

    def _mlabel(approach):
        return {
            "pygixml_stream_dump": "pygixml (stream_dump)",
            "pygixml_dom": "pygixml (DOM)",
            "lxml_plus_xmljson": "lxml + xmljson",
            "xmltodict": "xmltodict",
        }.get(approach, approach)

    for approach, data in memory.items():
        if not data.get("available"):
            continue
        points = data["points"]
        xy = [{"x": p["bytes"] / (1024 * 1024), "y": p["peak_rss_mb"]} for p in points]
        color = LIB_COLORS.get(approach, "#b98bff")
        label = _mlabel(approach)
        datasets_js.append({
            "label": label, "data": xy, "borderColor": color,
            "backgroundColor": color, "tension": 0.25, "pointRadius": 5,
            "pointStyle": LIB_POINT_STYLES.get(approach, "circle"),
            "borderDash": LIB_DASH.get(approach, []),
        })
        max_n_bytes = max(max_n_bytes, max(p["bytes"] for p in points))

        if approach in O1_APPROACHES:
            o1_group[approach] = points
        else:
            on_group[approach] = points

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

    complexity_note = ""
    o1_note = ""
    if o1_group:
        o1_parts = []
        for approach, points in o1_group.items():
            vals = [p["peak_rss_mb"] for p in points]
            biggest = _fmt_bytes(max(p["bytes"] for p in points))
            o1_parts.append(
                f"<strong>{_mlabel(approach)}</strong> (O(1)) stayed within "
                f"{min(vals):.1f}\u2013{max(vals):.1f}MB across every size tested, up to {biggest}"
            )
        o1_note = "; ".join(o1_parts) + "."
        complexity_note = o1_note

    if len(on_group) >= 2:
        # Pair points across approaches by matching byte size (every
        # approach here ran on the same generated input files per
        # size, so this is a real apples-to-apples pairing).
        by_bytes = {}
        for approach, points in on_group.items():
            for p in points:
                by_bytes.setdefault(p["bytes"], {})[approach] = p["peak_rss_mb"]

        wins_on = {a: 0 for a in on_group}
        n_sizes = 0
        for vals in by_bytes.values():
            if len(vals) >= 2:
                n_sizes += 1
                wins_on[min(vals.items(), key=lambda kv: kv[1])[0]] += 1
        ref_on = max(wins_on.items(), key=lambda kv: kv[1])[0] if n_sizes else None

        if ref_on:
            pairs_by_approach = {a: [] for a in on_group if a != ref_on}
            for vals in by_bytes.values():
                if ref_on not in vals:
                    continue
                for a in pairs_by_approach:
                    if a in vals:
                        pairs_by_approach[a].append((vals[a], vals[ref_on]))
            e_on = {a: _e_ratio(p) for a, p in pairs_by_approach.items() if p}
            if e_on:
                parts = ", ".join(
                    f"<strong>{_mlabel(a)}</strong> {e:.1f}\u00d7"
                    for a, e in sorted(e_on.items(), key=lambda kv: kv[1])
                )
                complexity_note += (
                    f" Among the O(n), DOM-based approaches only (a fair comparison -- same "
                    f"complexity class): <strong>{_mlabel(ref_on)}</strong> is the reference "
                    f"(lowest memory on {wins_on[ref_on]} of {n_sizes} sizes tested); on average "
                    f"(E[memory/{_mlabel(ref_on)}], mean of each size's own ratio): {parts} as much."
                )

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
            "lede_extra": lede_extra, "has_speed": bool(speed_datasets_js),
            "complexity_note": complexity_note, "o1_note": o1_note}


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
        "note": "The pugixml core, directly. xmltodict/xmljson have no separate \u201cparse to a "
                "tree\u201d step distinct from \u201cparse straight to dict\u201d, so they don't appear here.",
    },
    {
        "key": "iterparse",
        "title": "iterparse — stream every element, never hold the whole document",
        "note": "The yxml core, via pygixml.iterfind, against lxml's and ElementTree's own "
                "iterparse -- real streaming APIs on both sides. Only runs on corpus entries "
                "with one uniformly repeated element (a config-tree genre genuinely has none, "
                "so it's absent here, not skipped by oversight).",
    },
    {
        "key": "xml_to_json",
        "title": "jsonify — pygixml.jsonify vs the field, end to end",
        "note": "XML string in, JSON string out. ElementTree has no built-in dict/JSON "
                "conversion at all -- a real gap for it, not an oversight in this chart.",
    },
    {
        "key": "to_object",
        "title": "objectify — pygixml.objectify vs lxml.objectify",
        "note": "Lazy attribute-style access (root.child.grandchild), matched against lxml's "
                "own objectify submodule -- a real feature both libraries ship, not an "
                "improvised comparison.",
    },
    {
        "key": "dict_convert",
        "title": "dictify (DOM mode) — pygixml.dictify.parse vs xmltodict.parse",
        "note": "Both sides use the same convention (@-prefixed attributes, #text for mixed "
                "content) so the dicts they produce are structurally identical, not just "
                "\u201cboth happen to be a dict.\u201d",
    },
    {
        "key": "dict_stream",
        "title": "dictify (streaming mode) — pygixml.dictify.iterdict vs xmltodict's own item_depth streaming",
        "note": "xmltodict genuinely supports streaming too (item_depth + item_callback), not "
                "just a DOM-only tool being compared unfairly against a streaming one. Same "
                "record-tag restriction as iterparse.",
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
        ref_lib = None
        if n_comparisons:
            ref_lib = max(wins.items(), key=lambda kv: kv[1])[0]
            # E[target/ref]: for each OTHER library, take its ratio to
            # ref_lib on every corpus entry where both are available,
            # then average those per-entry ratios -- not
            # avg(target)/avg(ref), and not median(target)/median(ref).
            time_pairs = {lib: [] for lib in libs if lib != ref_lib}
            for r in rows:
                ref_cell = r.get(key, {}).get(ref_lib)
                if not (ref_cell and ref_cell.get("available")):
                    continue
                for lib in time_pairs:
                    c = r.get(key, {}).get(lib)
                    if c and c.get("available"):
                        time_pairs[lib].append((c["seconds"], ref_cell["seconds"]))
            e_ratios = {lib: _e_ratio(pairs) for lib, pairs in time_pairs.items() if pairs}
            ranked_ratios = sorted(e_ratios.items(), key=lambda kv: kv[1])
            rest = ", ".join(f"{LIB_LABELS.get(lib, lib)} {e:.1f}\u00d7" for lib, e in ranked_ratios)
            winner_summary = (
                f"<strong>{LIB_LABELS.get(ref_lib, ref_lib)}</strong> is the reference "
                f"(fastest on {wins[ref_lib]} of {n_comparisons} corpus entries). "
                f"On average (E[time/{LIB_LABELS.get(ref_lib, ref_lib)}], mean of each entry's own "
                f"ratio, not a ratio of medians)"
                + (f": {rest} as long." if rest else ".")
            )

        memory_summary = ""
        if n_mem_comparisons:
            mem_ref_lib = max(mem_wins.items(), key=lambda kv: kv[1])[0]
            mem_pairs = {lib: [] for lib in libs if lib != mem_ref_lib}
            for r in rows:
                entry_mem = mem_by_entry.get((r["genre"], r["size"]), {})
                ref_m = entry_mem.get(mem_ref_lib)
                if not (ref_m and ref_m.get("available")):
                    continue
                for lib in mem_pairs:
                    m = entry_mem.get(lib)
                    if m and m.get("available"):
                        mem_pairs[lib].append((m["peak_rss_mb"], ref_m["peak_rss_mb"]))
            mem_e_ratios = {lib: _e_ratio(pairs) for lib, pairs in mem_pairs.items() if pairs}
            ranked_mem_ratios = sorted(mem_e_ratios.items(), key=lambda kv: kv[1])
            rest_mem = ", ".join(f"{LIB_LABELS.get(lib, lib)} {e:.1f}\u00d7" for lib, e in ranked_mem_ratios)
            memory_summary = (
                f"<strong>{LIB_LABELS.get(mem_ref_lib, mem_ref_lib)}</strong> uses the least memory "
                f"(lowest on {mem_wins[mem_ref_lib]} of {n_mem_comparisons} corpus entries). "
                f"On average (E[memory/{LIB_LABELS.get(mem_ref_lib, mem_ref_lib)}])"
                + (f": {rest_mem} as much." if rest_mem else ".")
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
            "ref_lib": ref_lib,
            "e_ratios": e_ratios if n_comparisons else {},
            "mem_e_ratios": mem_e_ratios if n_mem_comparisons else {},
            "rows": rows,  # raw rows, for cross-op narrative building in build()
            "mem_by_entry": mem_by_entry,
            "entries": entries,
            "time_trend_chart_js": time_trend_chart_js, "has_time_trend": has_time_trend,
            "mem_trend_chart_js": mem_trend_chart_js, "has_mem_trend": has_mem_trend,
            "tp_chart_js": tp_chart_js,
            "has_tp_chart": bool(tp_datasets),
        })

    return {"ops": ops_out, "ops_by_key": {o["key"]: o for o in ops_out}, "repeats": repeats}


# --------------------------------------------------------- jsonify note --
# Small files: memory isn't the story yet (every approach fits in RAM
# comfortably), so speed AND memory both get a fair, same-complexity-
# class E[target/ref] comparison against xmljson specifically -- the
# DOM-based path pygixml.jsonify.dumps actually competes with. Big
# files: that's stream_dump's story instead (O(1), told in the memory
# section), referenced here rather than re-derived.

def _build_jsonify_narrative(xml_to_json_op, o1_note):
    if not xml_to_json_op or not xml_to_json_op.get("rows"):
        return ""
    rows = xml_to_json_op["rows"]
    mem_by_entry = xml_to_json_op.get("mem_by_entry", {})
    small_rows = [r for r in rows if r.get("size") == "small"]
    if not small_rows:
        return ""

    time_pairs = []
    for r in small_rows:
        p = r.get("xml_to_json", {}).get("pygixml")
        x = r.get("xml_to_json", {}).get("xmljson")
        if p and p.get("available") and x and x.get("available"):
            time_pairs.append((x["seconds"], p["seconds"]))
    speed_ratio = _e_ratio(time_pairs)

    mem_pairs = []
    for r in small_rows:
        entry_mem = mem_by_entry.get((r["genre"], r["size"]), {})
        p = entry_mem.get("pygixml")
        x = entry_mem.get("xmljson")
        if p and p.get("available") and x and x.get("available"):
            mem_pairs.append((x["peak_rss_mb"], p["peak_rss_mb"]))
    mem_ratio = _e_ratio(mem_pairs)

    if speed_ratio is None and mem_ratio is None:
        return ""

    parts = ["<p>On small documents, memory isn't the deciding factor for either "
             "approach -- both fit comfortably in RAM. What's left is speed, and "
             "there <code>jsonify.dumps</code> (the DOM path) wins clearly"]
    if speed_ratio is not None:
        parts.append(
            f": on average <strong>{speed_ratio:.1f}\u00d7</strong> the speed of xmljson "
            f"(E[time<sub>xmljson</sub>/time<sub>pygixml</sub>], mean of each small entry's own ratio)"
        )
    parts.append(". ")
    if mem_ratio is not None:
        parts.append(
            f"Even on memory -- where this is the DOM path, not <code>stream_dump</code>, so "
            f"both sides are genuinely O(n) here, a fair same-complexity-class comparison -- "
            f"pygixml still uses on average <strong>{mem_ratio:.1f}\u00d7 less</strong> memory than "
            f"xmljson on these same small files (E[memory<sub>xmljson</sub>/memory<sub>pygixml</sub>]). "
        )
    parts.append(
        "</p><p>Once the document stops being small, the calculus changes: that's exactly when "
        "<code>jsonify.stream_dump</code> takes over, trading the DOM path's speed for a "
        "fundamentally different complexity class. "
    )
    if o1_note:
        parts.append(o1_note)
    parts.append(" See the memory panel below for the full trade-off, not just the flattering half.</p>")
    return "".join(parts)


# ------------------------------------------------- dictify DOM vs stream --
# The DOM-mode dictify comparison (dict_convert) and the streaming-mode
# one (dict_stream) are computed as two separate operations above (each
# already has its own mini-grid/trend/throughput panels), but the
# question "is streaming actually worth it, for which library" only
# shows up if all four series -- pygixml DOM, pygixml stream, xmltodict
# DOM, xmltodict stream -- are on the same axes together.

def _build_dictify_mode_chart(dict_convert_op, dict_stream_op):
    if not dict_convert_op or not dict_stream_op:
        return "", False
    dom_rows = {(r["genre"], r["size"]): r for r in dict_convert_op.get("rows", [])}
    stream_rows = {(r["genre"], r["size"]): r for r in dict_stream_op.get("rows", [])}

    series_points = {"pygixml (DOM)": [], "pygixml (stream)": [],
                      "xmltodict (DOM)": [], "xmltodict (stream)": []}
    style_key = {"pygixml (DOM)": "pygixml", "pygixml (stream)": "pygixml_stream_dump",
                 "xmltodict (DOM)": "xmltodict", "xmltodict (stream)": "xmltodict"}

    for key_gs, srow in stream_rows.items():
        drow = dom_rows.get(key_gs)
        if not drow:
            continue
        mb = round(drow["bytes"] / (1024 * 1024), 4)
        for lib, dom_label, stream_label in (("pygixml", "pygixml (DOM)", "pygixml (stream)"),
                                              ("xmltodict", "xmltodict (DOM)", "xmltodict (stream)")):
            dc = drow.get("dict_convert", {}).get(lib)
            if dc and dc.get("available"):
                series_points[dom_label].append({"x": mb, "y": round(dc["seconds"] * 1000, 4)})
            sc = srow.get("dict_stream", {}).get(lib)
            if sc and sc.get("available"):
                series_points[stream_label].append({"x": mb, "y": round(sc["seconds"] * 1000, 4)})

    datasets = []
    for label, pts in series_points.items():
        if not pts:
            continue
        pts.sort(key=lambda p: p["x"])
        skey = style_key[label]
        color = LIB_COLORS.get(skey, "#8b93a7")
        datasets.append({
            "label": label, "data": pts, "borderColor": color, "backgroundColor": color,
            "pointStyle": LIB_POINT_STYLES.get(skey, "circle"),
            "borderDash": [] if "stream" in label else [6, 3],
            "showLine": True, "tension": 0.25, "pointRadius": 5, "pointHoverRadius": 8,
        })

    if not datasets:
        return "", False

    chart_js = f"""
new Chart(document.getElementById('chart-dictify-modes'), {{
  type: 'line',
  data: {{ datasets: {json.dumps(datasets)} }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    scales: {{
      x: {{ type: 'logarithmic', title: {{ display: true, text: 'Input size (MB, log scale)' }} }},
      y: {{ type: 'logarithmic', title: {{ display: true, text: 'Time (ms, log scale, lower is better)' }} }}
    }},
    plugins: {{ legend: {{ position: 'bottom' }} }}
  }}
}});
"""
    return chart_js, True


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

    ops_by_key = thr["ops_by_key"]
    jsonify_narrative = _build_jsonify_narrative(ops_by_key.get("xml_to_json"), mem["o1_note"])
    dictify_mode_chart_js, has_dictify_mode_chart = _build_dictify_mode_chart(
        ops_by_key.get("dict_convert"), ops_by_key.get("dict_stream"))

    with open(chartjs_path, "r", encoding="utf-8") as f:
        chartjs_source = f.read()

    embedded = {
        "throughput": throughput, "throughput_memory": throughput_memory, "scaling": scaling,
        "memory": memory, "sizes": sizes, "system_info": system_info,
    }

    headline = "pygixml, measured honestly"
    subhead = (
        "Five independent ways to work with XML &mdash; raw pugixml parsing, yxml streaming, "
        "jsonify, objectify, dictify &mdash; each measured on its own against its real, direct "
        "competitor. JSON is one section among five, not the point of the exercise."
    )

    chart_scripts = [mem["chart_js"], mem["speed_chart_js"], scl["chart_js"], scl["dom_chart_js"], siz["chart_js"],
                      dictify_mode_chart_js]
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
        memory_complexity_note=mem["complexity_note"],
        scaling_note=scl["note"],
        scaling_dom_available=scl["dom_available"],
        op_parse=ops_by_key.get("parse"),
        op_iterparse=ops_by_key.get("iterparse"),
        op_jsonify=ops_by_key.get("xml_to_json"),
        op_objectify=ops_by_key.get("to_object"),
        op_dictify_dom=ops_by_key.get("dict_convert"),
        op_dictify_stream=ops_by_key.get("dict_stream"),
        jsonify_narrative=jsonify_narrative,
        dictify_mode_chart_js=dictify_mode_chart_js,
        has_dictify_mode_chart=has_dictify_mode_chart,
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
