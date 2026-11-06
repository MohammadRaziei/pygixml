"""
render_benchmarks.py: render the public benchmarks page from the JSON files
the benchmark suite commits (benchmarks/results/*.json, one per benchmark).

Called by the documentation build (`cmake --build build --target
sphinx_docs`), which writes docs/benchmarks/index.html. The output is a
single HTML file: the raw data is embedded and Chart.js / KaTeX come from a
CDN (pinned version + SRI), so it needs no server and no sibling files.

What this file deliberately does NOT contain: how the corpus was
generated, why timing uses best-of-N, or the ru_maxrss/execve bug we
hit measuring memory. That's methodology and war stories for people
reading the source, not benchmark results for someone skimming a
report -- it lives in benchmarks/README.md instead. This file also
never computes an "N times better/less" ratio between an O(1) and an
O(n) approach: pygixml's stream_dump and its DOM-building competitors
are on different complexity curves in the memory/scaling story, so any
single ratio is only true at the one input size it was computed from;
the log-log chart shows that honestly.
"""
import argparse
import datetime
import json
import math
import os

from jinja2 import Environment, FileSystemLoader

HERE = os.path.dirname(os.path.abspath(__file__))

LIB_LABELS = {
    "pygixml": "pygixml",
    "lxml": "lxml",
    "elementtree": "ElementTree",
    "xmltodict": "xmltodict",
    "xmljson": "xmljson",
    "yq": "yq",
    "untangle": "untangle",
    "bs4_html_parser": "BeautifulSoup (html.parser)",
    "bs4_lxml": "BeautifulSoup (lxml)",
    "html5lib": "html5lib",
    "selectolax": "selectolax",
}
LIB_COLORS = {
    "pygixml": "#e67225",
    "pygixml_stream_dump": "#e67225",
    "pygixml_dom": "#f2954f",
    "pygixml_cli": "#e67225",
    "lxml": "#ff6b81",
    "lxml_plus_xmljson": "#ff6b81",
    "elementtree": "#5b8cff",
    "xmltodict": "#35d0ba",
    "xmljson": "#b98bff",
    "yq": "#ffb454",
    "untangle": "#6ee7b7",
    "bs4_html_parser": "#b98bff",
    "bs4_lxml": "#8f6bd6",
    "html5lib": "#5b8cff",
    "selectolax": "#35d0ba",
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
    "bs4_html_parser": "crossRot",
    "bs4_lxml": "cross",
    "html5lib": "rect",
    "selectolax": "star",
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
    "bs4_html_parser": [1, 3],
    "bs4_lxml": [4, 4],
    "html5lib": [2, 2],
    "selectolax": [8, 3, 2, 3],
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
        return {"chart_js": "", "speed_chart_js": "", "lede_extra": "", "has_speed": False,
                "complexity_note": "", "o1_note": ""}

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
                    f"(uses the least memory most consistently across the sizes tested); on average "
                    f"({_tex_e('other', _mlabel(ref_on), 'm')}, mean of each size's own ratio): {parts} as much."
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
    {{ label: 'interleaved shape (two tags alternating)', data: {json.dumps(series(interleaved))},
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
                f"records-shape time grew {r_ratio:.1f}\u00d7, "
                f"interleaved-shape time grew {i_ratio:.1f}\u00d7. "
                f"A curve parallel to N (slope 1 on these log axes) is linear; "
                f"the slope, not a single ratio, is the finding.")

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
        "title": "parse: build a tree from the XML string, discard it",
        "note": "Directly building an in-memory tree from the XML text. xmltodict/xmljson have "
                "no separate \u201cparse to a "
                "tree\u201d step distinct from \u201cparse straight to dict\u201d, so they don't appear here.",
    },
    {
        "key": "iterparse",
        "title": "iterparse: stream every element, never hold the whole document",
        "note": "Streamed via pygixml.iterfind, against lxml's and ElementTree's own "
                "iterparse -- real streaming APIs on both sides. Only runs on corpus entries "
                "with one uniformly repeated element (a config-tree genre genuinely has none, "
                "so it's absent here, not skipped by oversight).",
    },
    {
        "key": "xml_to_json",
        "title": "JSON: pygixml.jsonify vs the field, one document out",
        "note": "XML string in, one JSON document out. ElementTree has no built-in dict/JSON "
                "conversion at all -- a real gap for it, not an oversight in this chart.",
    },
    {
        "key": "xml_to_jsonl",
        "title": "JSON Lines: one JSON object per record, streamed",
        "note": "The streaming sibling of the panel above: instead of one JSON value for the "
                "whole document, one JSON object per matching element, read one at a time. "
                "xmltodict's own item_depth/item_callback streaming mode is the fair reference "
                "here too -- json.dumps happens per callback, same as pygixml emits per element. "
                "Same uniformly-repeated-tag restriction as streaming/iterparse above.",
    },
    {
        "key": "to_object",
        "title": "objectify: pygixml.objectify vs lxml.objectify",
        "note": "Lazy attribute-style access (root.child.grandchild), matched against lxml's "
                "own objectify submodule -- a real feature both libraries ship, not an "
                "improvised comparison.",
    },
    {
        "key": "dict_convert",
        "title": "dictify (DOM mode): pygixml.dictify.parse vs xmltodict.parse",
        "note": "Both sides use the same convention (@-prefixed attributes, #text for mixed "
                "content) so the dicts they produce are structurally identical, not just "
                "\u201cboth happen to be a dict.\u201d",
    },
    {
        "key": "dict_stream",
        "title": "dictify (streaming mode): pygixml.dictify.iterdict vs xmltodict's own item_depth streaming",
        "note": "xmltodict genuinely supports streaming too (item_depth + item_callback), not "
                "just a DOM-only tool being compared unfairly against a streaming one. Same "
                "record-tag restriction as iterparse.",
    },
]


HTML_OP_META = [
    {
        "key": "html_parse",
        "title": "parse: HTML string in, tree out, tree discarded",
        "note": "pygixml.parse_html against lxml.html, BeautifulSoup (both of its common backends), \n"
                "html5lib and selectolax (Lexbor). The pages are deliberately messy: unclosed \n"
                "p/li/td/tr, void tags, entities, valueless attributes. No memory numbers here yet.",
    },
    {
        "key": "html_extract_links",
        "title": "extract links: parse, then collect (href, text) of every <a>",
        "note": "The same parse plus a real query on the result, with each library's own idiom "
                "(XPath, find_all, CSS selector). The run warns if the libraries disagree on the "
                "number of links found.",
    },
]


def _tex_text(s):
    """Escape the TeX specials a library label could contain, for \\text{...}."""
    for ch in "_&%#$":
        s = s.replace(ch, "\\" + ch)
    return s


def _tex_e(num, den, q="t"):
    """The "mean of each entry's own ratio" in KaTeX (the page renders \\(...\\)):
    E[q_num / q_den], q = "t" (time) or "m" (memory)."""
    return (r"\(\mathbb{E}\left[\frac{%s_{\text{%s}}}{%s_{\text{%s}}}\right]\)"
            % (q, _tex_text(num), q, _tex_text(den)))


def _fmt_ms(x):
    if x < 1:
        return f"{x:.3f}ms"
    if x < 10:
        return f"{x:.2f}ms"
    return f"{x:.1f}ms"


def _collapse_sizes(points):
    """One point per size label: mean x, geometric mean y. For corpora whose genres
    share the same sizes (the HTML pages), joining every entry in x order would draw
    vertical zigzags between genres of the same size."""
    groups = {}
    for p in points:
        groups.setdefault(p["size"], []).append(p)
    out = []
    for g in groups.values():
        g = [p for p in g if p["y"] > 0]
        if g:
            out.append({"x": round(sum(p["x"] for p in g) / len(g), 4),
                        "y": round(math.exp(sum(math.log(p["y"]) for p in g) / len(g)), 4)})
    return out


# Chart.js labels every 1..9 x 10^n on a log axis and the labels collide
# ("0.90.00"); keep 1, 2 and 5 of each decade.
_LOG_TICKS_JS = """function (v) {
  var m = v / Math.pow(10, Math.floor(Math.log10(v)));
  return [1, 2, 5].some(function (k) { return Math.abs(m - k) < 1e-6; }) ? String(Number(v.toPrecision(2))) : '';
}"""


def _build_throughput_section(throughput, throughput_memory, op_meta=None, collapse_genres=False):
    if not throughput:
        return {"ops": [], "repeats": "?"}

    rows = throughput["results"]
    repeats = throughput.get("repeats", "?")
    labels = [f"{r['genre']}/{r['size']}" for r in rows]
    throughput_memory = throughput_memory or {}

    ops_out = []
    for meta in (op_meta or OP_META):
        key = meta["key"]
        libs = sorted({lib for r in rows for lib in r.get(key, {})})
        if not libs:
            continue

        # Index this operation's memory rows by (genre, size) so they
        # line up with throughput.json's rows regardless of ordering.
        mem_by_entry = {}
        for mrow in throughput_memory.get(key, []):
            mem_by_entry[(mrow["genre"], mrow["size"])] = mrow.get("libraries", {})

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
                                                "y": round(c["seconds"] * 1000, 4),
                                                **({"size": r["size"]} if collapse_genres else {})})

            entry_mem = mem_by_entry.get((r["genre"], r["size"]), {})
            mem_cells = [(lib, entry_mem.get(lib)) for lib, _ in cells]
            mem_cells = [(lib, m) for lib, m in mem_cells if m and m.get("available")]
            if mem_cells:
                mem_cells_sorted = sorted(mem_cells, key=lambda lm: lm[1]["peak_rss_mb"])
                n_mem_comparisons += 1
                mem_wins[mem_cells_sorted[0][0]] += 1
                for lib, m in mem_cells:
                    mem_trend_points[lib].append({"x": round(r["bytes"] / (1024 * 1024), 4),
                                                   "y": round(m["peak_rss_mb"], 2),
                                                   **({"size": r["size"]} if collapse_genres else {})})

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
                f"(fastest most consistently across the corpus). "
                f"On average ({_tex_e('other', LIB_LABELS.get(ref_lib, ref_lib), 't')})"
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
                f"most consistently across the corpus. "
                f"On average ({_tex_e('other', LIB_LABELS.get(mem_ref_lib, mem_ref_lib), 'm')})"
                + (f": {rest_mem} as much." if rest_mem else ".")
            )

        # Time-vs-size and memory-vs-size: the same "does the trend hold
        # as files grow" question the throughput chart answers, just for
        # the two other metrics -- same treatment (connected lines, log
        # x, one line per library) for consistency.
        def _trend_chart(canvas_id, points_by_lib, y_title, y_log):
            datasets = []
            for lib in libs:
                pts = points_by_lib.get(lib, [])
                if collapse_genres:
                    pts = _collapse_sizes(pts)
                pts = sorted(pts, key=lambda p: p["x"])
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
            y_ticks = f"ticks: {{ callback: {_LOG_TICKS_JS} }}," if y_log else ""
            js = f"""
new Chart(document.getElementById('{canvas_id}'), {{
  type: 'line',
  data: {{ datasets: {json.dumps(datasets)} }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    scales: {{
      x: {{ type: 'logarithmic', title: {{ display: true, text: 'Input size (MB, log scale)' }},
            ticks: {{ callback: {_LOG_TICKS_JS} }} }},
      y: {{ type: {y_scale}, {y_ticks} title: {{ display: true, text: '{y_title}' }} }}
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
                    tp_points.append({"x": round(mb, 4), "y": round(mb / cell["seconds"], 2),
                                      **({"size": r["size"]} if collapse_genres else {})})
            if collapse_genres:
                tp_points = _collapse_sizes(tp_points)
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
      x: {{ type: 'logarithmic', title: {{ display: true, text: 'Input size (MB, log scale)' }},
            ticks: {{ callback: {_LOG_TICKS_JS} }} }},
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
            f"({_tex_e('xmljson', 'pygixml', 't')}, mean of each small entry's own ratio)"
        )
    parts.append(". ")
    if mem_ratio is not None:
        parts.append(
            f"Even on memory -- where this is the DOM path, not <code>stream_dump</code>, so "
            f"both sides are genuinely O(n) here, a fair same-complexity-class comparison -- "
            f"pygixml still uses on average <strong>{mem_ratio:.1f}\u00d7 less</strong> memory than "
            f"xmljson on these same small files ({_tex_e('xmljson', 'pygixml', 'm')}). "
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
        return {"chart_js": "", "rows": []}

    def to_kb(data):
        s = data.get("total_size", "0 B")
        num, unit = s.split()
        num = float(num)
        return {"B": num / 1024, "KB": num, "MB": num * 1024, "GB": num * 1024 * 1024}.get(unit, 0)

    labels, values, colors, borders = [], [], [], []
    rows = []
    for name, data in sizes.items():
        if not data.get("available"):
            continue
        label = LIB_LABELS.get(name, name)
        kb = round(to_kb(data), 1)
        is_self = name == "pygixml"
        labels.append(label)
        values.append(kb)
        colors.append(LIB_COLORS.get(name, "#5a6274") if not is_self else LIB_COLORS["pygixml"])
        # pygixml's own bar gets a visible border the rest don't, so it
        # doesn't rely on hue alone to stand out from the pack.
        borders.append("#ffffff" if is_self else "rgba(0,0,0,0)")
        rows.append({
            "label": label, "is_self": is_self, "kb": kb,
            "version": data.get("version", "?"),
            "capability": data.get("capability", ""),
            "n_deps": len(data.get("dependencies", [])),
        })
    rows.sort(key=lambda r: r["kb"])

    chart_js = f"""
new Chart(document.getElementById('chart-size'), {{
  type: 'bar',
  data: {{ labels: {json.dumps(labels)}, datasets: [{{
    label: 'Installed size (KB, lower is better)', data: {json.dumps(values)},
    backgroundColor: {json.dumps(colors)}, borderColor: {json.dumps(borders)}, borderWidth: 2
  }}] }},
  options: {{
    indexAxis: 'y',
    responsive: true, maintainAspectRatio: false,
    scales: {{ x: {{ title: {{ display: true, text: 'KB, real wheel size incl. dependencies -- lower is better' }} }} }},
    plugins: {{ legend: {{ display: false }} }}
  }}
}});
"""
    return {"chart_js": chart_js, "rows": rows}


# ------------------------------------------------------------------- cli --
# pygixml's own command-line tool against `xq` (from the `yq` PyPI
# package) -- real subprocess invocations end to end, not in-process
# calls, since that's how both are actually used at a shell.

def _build_cli_section(cli):
    if not cli or not cli.get("results"):
        return {"chart_js": "", "trend_chart_js": "", "summary": "", "repeats": "?", "commands": {}}

    rows = cli["results"]
    repeats = cli.get("repeats", "?")
    commands = cli.get("commands", {})

    pairs = []
    trend_pyg, trend_xq = [], []
    for r in rows:
        p = r.get("pygixml_cli", {})
        x = r.get("xq", {})
        if p.get("available") and x.get("available"):
            pairs.append((p["seconds"], x["seconds"]))
            mb = round(r["bytes"] / (1024 * 1024), 4)
            trend_pyg.append({"x": mb, "y": round(p["seconds"] * 1000, 4)})
            trend_xq.append({"x": mb, "y": round(x["seconds"] * 1000, 4)})

    # pairs are (pygixml, xq); E[xq/pygixml] is the ratio the sentence names.
    e_ratio = _e_ratio([(x, p) for p, x in pairs])
    summary = ""
    if e_ratio is not None:
        summary = (
            f"On average ({_tex_e('xq', 'pygixml', 't')}, mean of each corpus "
            f"entry's own ratio): <strong>xq</strong> takes <strong>{e_ratio:.1f}\u00d7</strong> "
            f"as long as <strong>pygixml</strong>'s CLI, across {len(pairs)} corpus entries."
        )

    trend_pyg.sort(key=lambda p: p["x"])
    trend_xq.sort(key=lambda p: p["x"])
    trend_chart_js = ""
    if trend_pyg and trend_xq:
        trend_chart_js = f"""
new Chart(document.getElementById('chart-cli-trend'), {{
  type: 'line',
  data: {{ datasets: [
    {{ label: 'pygixml jsonify', data: {json.dumps(trend_pyg)},
       borderColor: '{LIB_COLORS["pygixml"]}', backgroundColor: '{LIB_COLORS["pygixml"]}',
       pointStyle: 'circle', borderDash: [], showLine: true, tension: 0.25, pointRadius: 5, pointHoverRadius: 8 }},
    {{ label: 'xq .', data: {json.dumps(trend_xq)},
       borderColor: '#b98bff', backgroundColor: '#b98bff',
       pointStyle: 'star', borderDash: [8, 3, 2, 3], showLine: true, tension: 0.25, pointRadius: 5, pointHoverRadius: 8 }}
  ] }},
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

    return {"trend_chart_js": trend_chart_js, "summary": summary, "repeats": repeats,
            "commands": commands}


# KaTeX and Chart.js come from a CDN (pinned version + SRI hashes, so a changed file is
# refused), not embedded. Only the data stays embedded.
CHARTJS_VERSION = "4.5.1"
CHARTJS_URL = "https://cdn.jsdelivr.net/npm/chart.js@" + CHARTJS_VERSION + "/dist/chart.umd.min.js"
CHARTJS_SRI = "sha384-jb8JQMbMoBUzgWatfe6COACi2ljcDdZQ2OxczGA3bGNeWe+6DChMTBJemed7ZnvJ"
KATEX_VERSION = "0.19.0"
KATEX_CDN = "https://cdn.jsdelivr.net/npm/katex@" + KATEX_VERSION + "/dist/"
KATEX_SRI = {
    "css": "sha384-3rdsX6e5mueWyoweR9NIVmtEsUkokpBT/0ALqKKIBMr9j4qhHkaIkAcGgsE6uVlp",
    "js": "sha384-QFFtAGzvvj+bfgCGxXJlNZZR1nXEZgvG8tDLCCY1F19xl20WlfTYgguB4VcNdxYk",
    "auto": "sha384-bjyGPfbij8/NDKJhSGZNP/khQVgtHUE5exjm4Ydllo42FwIgYsdLO2lXGmRBf5Mz",
}


# -------------------------------------------------------------- abstract --

def _ratio(rows, op, other, ref="pygixml"):
    """E[other/ref] over the entries where both libraries ran."""
    pairs = []
    for r in rows:
        o, p = r.get(op, {}).get(other), r.get(op, {}).get(ref)
        if o and p and o.get("available") and p.get("available"):
            pairs.append((o["seconds"], p["seconds"]))
    return _e_ratio(pairs)


def _build_abstract(throughput, html, memory, cli, html_memory=None):
    """The paper-style summary at the top of the page. Every number comes from
    the result JSONs; a claim is only printed if the data shows pygixml
    winning, and every loss the data shows goes into the closing caveat."""
    wins, loses = [], {}
    # (op, what it measures, competitors); ratios are E[competitor/pygixml].
    specs = [
        (throughput, "parse", "building a tree", ["lxml", "elementtree"]),
        (throughput, "dict_convert", "XML to a dict (dictify)", ["xmltodict"]),
        (throughput, "xml_to_json", "XML to JSON (jsonify.dumps)", ["xmltodict", "xmljson"]),
        (throughput, "dict_stream", "streaming dicts (dictify.iterdict)", ["xmltodict"]),
        (throughput, "xml_to_jsonl", "streaming JSON Lines (jsonify.iterjsonl)", ["xmltodict"]),
        (throughput, "to_object", "attribute-style access (objectify)", ["lxml"]),
        (throughput, "iterparse", "iterparse", ["lxml", "elementtree"]),
        (html, "html_parse", "parsing messy HTML (parse_html)",
         ["lxml", "bs4_html_parser", "bs4_lxml", "html5lib", "selectolax"]),
    ]
    for data, op, what, libs in specs:
        rows = (data or {}).get("results", [])
        faster = []
        for lib in libs:
            r = _ratio(rows, op, lib)
            if r is None:
                continue
            label = LIB_LABELS.get(lib, lib)
            if r >= 1.05:
                faster.append(f"{r:.1f}\u00d7 faster than {label}")
            elif r <= 0.95:
                loses.setdefault(what, []).append(f"{label} is {1 / r:.1f}\u00d7 faster")
        if faster:
            wins.append(f"<strong>{what}</strong>: " + ", ".join(faster))

    if cli and cli.get("results"):
        r = _e_ratio([(x["xq"]["seconds"], x["pygixml_cli"]["seconds"]) for x in cli["results"]
                      if x.get("xq", {}).get("available") and x.get("pygixml_cli", {}).get("available")])
        if r and r >= 1.05:
            wins.append(f"<strong>command line</strong> (process startup included): {r:.1f}\u00d7 faster than xq")
        elif r and r <= 0.95:
            loses.setdefault("command line", []).append(f"xq is {1 / r:.1f}\u00d7 faster")

    hm_rows = (html_memory or {}).get("html_parse", [])
    hm_wins = []
    for lib in ("lxml", "bs4_html_parser", "bs4_lxml", "html5lib", "selectolax"):
        pairs = [(r["libraries"][lib]["peak_rss_mb"], r["libraries"]["pygixml"]["peak_rss_mb"]) for r in hm_rows
                 if r.get("libraries", {}).get(lib, {}).get("available")
                 and r["libraries"].get("pygixml", {}).get("available")]
        ratio = _e_ratio(pairs)
        if ratio is None:
            continue
        label = LIB_LABELS.get(lib, lib)
        if ratio >= 1.05:
            hm_wins.append(f"{ratio:.1f}\u00d7 less than {label}")
        elif ratio <= 0.95:
            loses.setdefault("HTML memory", []).append(f"{label} uses {1 / ratio:.1f}\u00d7 less")
    if hm_wins:
        wins.append("<strong>HTML memory</strong> (peak RSS of <code>parse_html</code>): " + ", ".join(hm_wins))

    def pts(key):
        return sorted((p for p in (memory or {}).get(key, {}).get("points", []) if p.get("available")),
                      key=lambda p: p["n"])

    sd, dom, xd = pts("pygixml_stream_dump"), pts("pygixml_dom"), pts("xmltodict")
    if len(sd) >= 2:
        lo, hi = min(p["peak_rss_mb"] for p in sd), max(p["peak_rss_mb"] for p in sd)
        level = f"about {sum(p['peak_rss_mb'] for p in sd) / len(sd):.0f}\u00a0MB" if hi < lo * 1.15 \
            else f"{lo:.0f}\u2013{hi:.0f}\u00a0MB"
        text = (f"<strong>constant memory</strong>: <code>jsonify.stream_dump</code> converts XML to JSON with a "
                f"peak RSS of {level} while the input grows from {_fmt_bytes(sd[0]['bytes'])} to "
                f"{_fmt_bytes(sd[-1]['bytes'])}")
        rivals = []
        for key, label in (("xmltodict", "xmltodict"), ("lxml_plus_xmljson", "lxml + xmljson")):
            rp = pts(key)
            if len(rp) >= 2 and rp[-1]["n"] == sd[-1]["n"]:
                rivals.append((label, rp[0]["peak_rss_mb"], rp[-1]["peak_rss_mb"]))
        if rivals:
            text += "; on the largest input " + " and ".join(f"{l} peaks at {b:.0f}\u00a0MB" for l, a, b in rivals)
            if all(b >= 2 * a for l, a, b in rivals):
                text += ", and their peak grows with the input"
        wins.insert(0, text)
        # What constant memory costs, and where the DOM mode stands, on the largest input.
        if dom and dom[-1]["n"] == sd[-1]["n"] and sd[-1]["seconds"] > 1.5 * dom[-1]["seconds"]:
            loses.setdefault("constant memory", []).append(f"<code>stream_dump</code> needs {sd[-1]['seconds']:.1f}\u00a0s on the "
                         f"largest input, pygixml's own DOM mode {dom[-1]['seconds']:.1f}\u00a0s")
        if dom and xd and dom[-1]["n"] == xd[-1]["n"] and dom[-1]["peak_rss_mb"] > xd[-1]["peak_rss_mb"]:
            loses.setdefault("DOM mode", []).append(f"peak memory on the largest input ({dom[-1]['peak_rss_mb']:.0f}\u00a0MB) is "
                         f"above xmltodict's ({xd[-1]['peak_rss_mb']:.0f}\u00a0MB)")

    if not wins:
        return None
    n_entries = len((throughput or {}).get("results", []))
    repeats = (throughput or {}).get("repeats", "?")
    return {
        "lead": ("pygixml puts pugixml's C++ DOM, an inlined streaming parser and dictify / objectify / jsonify / a CLI "
                 "into one Python extension with no runtime dependencies. This report measures each of those on its own "
                 "against the tool people actually use for the job "
                 f"({n_entries} corpus entries, {repeats} repeats per cell, one machine; "
                 "ratios are each entry's own time ratio, averaged)."),
        "points": wins,
        "caveat": ("<strong>Where it does not win.</strong> "
                   + "; ".join(f"{k}: {', '.join(v)}" for k, v in loses.items()) + ".") if loses else "",
    }


def _project_version():
    """The package version from pyproject.toml, or "" if it cannot be read."""
    try:
        import tomllib
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "pyproject.toml")
        with open(path, "rb") as f:
            return tomllib.load(f)["project"]["version"]
    except Exception:
        return ""


def build(results_dir, output_path, version=None):
    """results_dir holds one JSON per benchmark (throughput.json, html.json, ...)."""
    if not os.path.isdir(results_dir):
        raise SystemExit(f"render_benchmarks: {results_dir} is not a directory")
    throughput, throughput_memory, scaling, memory, sizes, cli, system_info, html, html_memory = (
        _load(os.path.join(results_dir, n + ".json"))
        for n in ("throughput", "throughput_memory", "scaling", "memory", "sizes", "cli", "system_info", "html",
                  "html_memory"))

    mem = _build_memory_section(memory)
    scl = _build_scaling_section(scaling)
    thr = _build_throughput_section(throughput, throughput_memory)
    siz = _build_size_section(sizes)
    cli_sec = _build_cli_section(cli)
    html_sec = _build_throughput_section(html, html_memory, HTML_OP_META, collapse_genres=True)

    ops_by_key = thr["ops_by_key"]
    jsonify_narrative = _build_jsonify_narrative(ops_by_key.get("xml_to_json"), mem["o1_note"])
    dictify_mode_chart_js, has_dictify_mode_chart = _build_dictify_mode_chart(
        ops_by_key.get("dict_convert"), ops_by_key.get("dict_stream"))

    embedded = {
        "throughput": throughput, "throughput_memory": throughput_memory, "scaling": scaling,
        "memory": memory, "sizes": sizes, "cli": cli, "system_info": system_info, "html": html,
        "html_memory": html_memory,
    }

    abstract = _build_abstract(throughput, html, memory, cli, html_memory)
    headline = "pygixml, measured honestly"
    subhead = (
        "Every independent way to work with XML this library offers &mdash; the core module, "
        "objectify, dictify, jsonify (both JSON and JSON Lines), and the command-line tool "
        "&mdash; each measured on its own against its real, direct competitor."
    )

    chart_scripts = [mem["chart_js"], mem["speed_chart_js"], scl["chart_js"], scl["dom_chart_js"], siz["chart_js"],
                      dictify_mode_chart_js, cli_sec["trend_chart_js"]]
    for op in thr["ops"]:
        chart_scripts.append(op["time_trend_chart_js"])
        chart_scripts.append(op["mem_trend_chart_js"])
        chart_scripts.append(op["tp_chart_js"])

    for op in html_sec["ops"]:
        chart_scripts.append(op["time_trend_chart_js"])
        chart_scripts.append(op["tp_chart_js"])

    env = Environment(loader=FileSystemLoader(HERE), autoescape=False)
    template = env.get_template("template.html.jinja2")

    html = template.render(
        generated_at=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        headline=headline,
        abstract=abstract,
        version=version or _project_version(),
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
        op_jsonl=ops_by_key.get("xml_to_jsonl"),
        has_html=bool(html_sec["ops"]), html_ops=html_sec["ops"],
        op_objectify=ops_by_key.get("to_object"),
        op_dictify_dom=ops_by_key.get("dict_convert"),
        op_dictify_stream=ops_by_key.get("dict_stream"),
        jsonify_narrative=jsonify_narrative,
        dictify_mode_chart_js=dictify_mode_chart_js,
        has_dictify_mode_chart=has_dictify_mode_chart,
        repeats=thr["repeats"],
        has_memory=bool(memory), has_scaling=bool(scaling), has_throughput=bool(throughput),
        has_throughput_memory=bool(throughput_memory),
        has_sizes=bool(sizes), size_rows=siz["rows"],
        has_cli=bool(cli_sec["trend_chart_js"] or cli_sec["summary"]), cli=cli_sec,
        system_info=system_info,
        chartjs_url=CHARTJS_URL, chartjs_sri=CHARTJS_SRI,
        katex_cdn=KATEX_CDN, katex_sri=KATEX_SRI,
        embedded_json=json.dumps(embedded),
        chart_scripts="\n".join(chart_scripts),
    )

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("results_dir", help="benchmarks/results/ (one JSON per benchmark: throughput.json, html.json, ...)")
    p.add_argument("output", help="path to write the standalone benchmarks page (index.html)")
    p.add_argument("--version", default=None, help="package version for the navbar badge (default: read pyproject.toml)")
    args = p.parse_args()

    out = build(args.results_dir, args.output, args.version)
    size_kb = os.path.getsize(out) / 1024
    print(f"render_benchmarks: wrote {out} ({size_kb:.0f}KB)")
