const DATA = JSON.parse(document.getElementById('report-data').textContent);

const COLORS = {
  pygixml: '#e6772a', lxml: '#5b8cff', elementtree: '#35d0ba',
  xmltodict: '#ffb454', xmljson: '#ff6b81', yq: '#b18aff', untangle: '#7fd858',
  pygixml_cli: '#e6772a',
};
const NAMES = {
  pygixml: 'pygixml', lxml: 'lxml', elementtree: 'ElementTree (stdlib)',
  xmltodict: 'xmltodict', xmljson: 'xmljson', yq: 'yq (xq)', untangle: 'untangle',
  pygixml_cli: 'pygixml (CLI)',
};
const CAPS = {
  pygixml: ['DOM parse', 'stream parse', 'objectify', 'dictify', 'jsonify (json)', 'jsonify (jsonl, O(1) mem)', 'CLI'],
  lxml: ['DOM parse', 'stream parse', 'objectify', 'XPath / XSLT'],
  elementtree: ['DOM parse', 'stream parse'],
  xmltodict: ['dictify (whole + stream)'],
  xmljson: ['jsonify (from a parsed tree)'],
  yq: ['CLI (query via jq syntax, convert XML/YAML/TOML/JSON)'],
  untangle: ['objectify-style attribute access'],
};

function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }

let chartSeq = 0, secSeq = 0;

function el(html) {
  const t = document.createElement('template');
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
}

function fmtSec(s) {
  if (s == null) return '—';
  if (s < 0.001) return (s * 1e6).toFixed(1) + ' µs';
  if (s < 1) return (s * 1000).toFixed(2) + ' ms';
  return s.toFixed(3) + ' s';
}
function fmtMB(m) { return m == null ? '—' : m.toFixed(1) + ' MB'; }
function fmtRatio(r) { return r == null ? '—' : r.toFixed(2) + '×'; }

// ---------------------------------------------------------------------
// download-as-JSON link
// ---------------------------------------------------------------------
function downloadLink(container, filename, obj) {
  const blob = new Blob([JSON.stringify(obj, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = el(`<a class="dl" href="${url}" download="${filename}">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3v12m0 0l-4-4m4 4l4-4M5 21h14"/></svg>
    download raw JSON for this ${container}
  </a>`);
  return a;
}

// ---------------------------------------------------------------------
// chart helper
// ---------------------------------------------------------------------
function makeChart(parent, { labels, series, order, yTitle, direction, xLabel }) {
  const id = 'c' + (chartSeq++);
  const box = el(`<div class="chart-box"><canvas id="${id}"></canvas></div>`);
  parent.appendChild(box);
  const gridColor = css('--line');
  const textColor = css('--ink-dim');
  const keys = order || Object.keys(series);
  const datasets = keys.filter(k => series[k]).map(k => ({
    label: NAMES[k] || k,
    data: series[k],
    backgroundColor: COLORS[k] || '#999',
    borderRadius: 3,
  }));
  new Chart(document.getElementById(id), {
    type: 'bar',
    data: { labels, datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        x: { ticks: { color: textColor, font: { size: 10 } }, grid: { color: gridColor }, title: { display: !!xLabel, text: xLabel, color: textColor } },
        y: {
          type: 'linear',
          ticks: { color: textColor },
          grid: { color: gridColor },
          title: { display: true, text: yTitle, color: textColor },
        },
      },
      plugins: {
        legend: { display: keys.length > 1, labels: { color: textColor, font: { size: 11 } } },
        tooltip: { mode: 'index', intersect: false },
      },
    },
  });
}

// single series where each *bar* (not each dataset) gets its own color --
// used for the one package-per-bar chart (package sizes) where the x-axis
// categories themselves are the things being compared/colored.
function makeColoredBarChart(parent, { labels, values, colors, yTitle, xLabel }) {
  const id = 'c' + (chartSeq++);
  const box = el(`<div class="chart-box"><canvas id="${id}"></canvas></div>`);
  parent.appendChild(box);
  const gridColor = css('--line');
  const textColor = css('--ink-dim');
  new Chart(document.getElementById(id), {
    type: 'bar',
    data: { labels, datasets: [{ data: values, backgroundColor: colors, borderRadius: 3 }] },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        x: { ticks: { color: textColor, font: { size: 10 } }, grid: { color: gridColor }, title: { display: !!xLabel, text: xLabel, color: textColor } },
        y: { type: 'linear', ticks: { color: textColor }, grid: { color: gridColor }, title: { display: true, text: yTitle, color: textColor } },
      },
      plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false } },
    },
  });
}

function lineChart(parent, { labels, series, order, yTitle, xLabel, logScaleY, logScaleX }) {
  const id = 'c' + (chartSeq++);
  const box = el(`<div class="chart-box"><canvas id="${id}"></canvas></div>`);
  parent.appendChild(box);
  const gridColor = css('--line');
  const textColor = css('--ink-dim');
  const datasets = (order || Object.keys(series)).filter(k => series[k]).map(k => ({
    label: NAMES[k] || k,
    data: series[k],
    borderColor: COLORS[k] || '#999',
    backgroundColor: (COLORS[k] || '#999') + '33',
    tension: 0.25,
    pointRadius: 3,
  }));
  new Chart(document.getElementById(id), {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        x: { type: logScaleX ? 'logarithmic' : 'category', ticks: { color: textColor, font: { size: 10 } }, grid: { color: gridColor }, title: { display: !!xLabel, text: xLabel, color: textColor } },
        y: { type: logScaleY ? 'logarithmic' : 'linear', ticks: { color: textColor }, grid: { color: gridColor }, title: { display: true, text: yTitle, color: textColor } },
      },
      plugins: { legend: { labels: { color: textColor, font: { size: 11 } } } },
    },
  });
}

// ---------------------------------------------------------------------
// panel / e-ratio / note builders
// ---------------------------------------------------------------------
function detailsBlock(parent, summaryText) {
  const d = el(`<details class="mini-details"><summary>${summaryText}</summary><div class="mini-details-body"></div></details>`);
  parent.appendChild(d);
  d.addEventListener('toggle', function () {
    if (!d.open) return;
    d.querySelectorAll('canvas').forEach(function (canvas) {
      const chart = Chart.getChart(canvas);
      if (chart) chart.resize();
    });
  });
  return d.querySelector('.mini-details-body');
}

function panel(parent, title, direction) {
  const p = el(`<div class="panel">
    <div class="panel-head">
      <div class="panel-title">${title}</div>
      <div class="direction">${direction}</div>
    </div>
  </div>`);
  parent.appendChild(p);
  return p;
}

function eratios(parent, items) {
  const wrap = el(`<div class="eratios"></div>`);
  for (const it of items) {
    if (!it.data) continue;
    wrap.appendChild(el(`<div class="eratio">
      <div class="val">${fmtRatio(it.data.mean)}</div>
      <div class="lbl">E[pygixml / ${it.ref}] · ${it.metric}, averaged over ${it.data.n} files</div>
    </div>`));
  }
  if (wrap.children.length) parent.appendChild(wrap);
}

function note(parent, html) {
  parent.appendChild(el(`<div class="note">${html}</div>`));
}

// ---------------------------------------------------------------------
// section / subsection scaffolding
// ---------------------------------------------------------------------
function topSection(rootEl, id, title, introHtml) {
  secSeq++;
  const sec = el(`<section class="top" id="${id}">
    <hr>
    <div class="sec-head"><span class="sec-num">${String(secSeq).padStart(2,'0')}</span><h2>${title}</h2></div>
    <p class="sec-intro">${introHtml}</p>
  </section>`);
  rootEl.appendChild(sec);
  document.getElementById('toc').appendChild(el(`<a href="#${id}">${title}</a>`));
  return sec;
}

function subSection(sec, title, tag, descHtml) {
  const s = el(`<div class="subsec">
    <h3>${title} ${tag ? `<span class="tag">${tag}</span>` : ''}</h3>
    <p class="desc">${descHtml}</p>
  </div>`);
  sec.appendChild(s);
  return s;
}

// =======================================================================
const root = document.getElementById('sections');

// ---------------------------------------------------------------------
// 0. Package footprint
// ---------------------------------------------------------------------
(function () {
  const sec = topSection(root, 'sizes', 'Package Footprint',
    'Before any code runs: what does it cost to <span class="mono">pip install</span> each of these in the first place? pygixml bundles parsing, streaming, object/dict/JSON conversion and a CLI in one wheel — the comparison here is that one download against pulling in a narrower, single-purpose package for the same job.');

  const p = panel(sec, 'Installed footprint, current release on PyPI (own wheel + dependencies)', 'lower is better');
  const order = ['pygixml', 'lxml', 'xmltodict', 'xmljson', 'yq', 'untangle', 'elementtree'];
  const toKB = (s) => {
    if (!s || !s.available) return null;
    const m = /([\d.]+)\s*(KB|MB|B)/.exec(s.total_size);
    if (!m) return null;
    const n = parseFloat(m[1]);
    return m[2] === 'MB' ? n * 1024 : (m[2] === 'B' ? n / 1024 : n);
  };
  makeColoredBarChart(p, {
    labels: order.map(k => NAMES[k] || k),
    values: order.map(k => toKB(DATA.sizes[k])),
    colors: order.map(k => COLORS[k] || '#999'),
    yTitle: 'KB',
  });
  note(sec, 'ElementTree ships in the Python standard library — 0 extra bytes, already present on every install. It is the one entry in this chart that costs nothing to add. Every other bar is the <b>total</b> installed size including that package\'s own dependencies (e.g. yq pulls in argcomplete, pyyaml, tomlkit and xmltodict — its own wheel is a small fraction of what actually lands on disk). Sizes measured with <a href="https://github.com/MohammadRaziei/pip-size" target="_blank" rel="noopener" class="mono">pip-size</a>, resolving each package\'s real dependency tree against a fresh wheel cache rather than an already-populated environment.');

  const tbl = el(`<div class="scrollx"><table><thead><tr>
    <th>package</th><th>version</th><th class="num">wheel size</th><th>capabilities</th>
  </tr></thead><tbody></tbody></table></div>`);
  sec.appendChild(tbl);
  const tbody = tbl.querySelector('tbody');
  for (const k of order) {
    const s = DATA.sizes[k];
    if (!s || !s.available) continue;
    const caps = (CAPS[k] || []).map(c => `<span class="cap-tag">${c}</span>`).join('');
    tbody.appendChild(el(`<tr${k === 'pygixml' ? ' class="own-row"' : ''}>
      <td>${k === 'pygixml' ? '<span class="dot"></span>' : ''}<b>${NAMES[k] || k}</b></td>
      <td class="mono">${s.version}</td>
      <td class="num mono">${s.total_size}</td>
      <td><div class="cap-tags">${caps}</div></td>
    </tr>`));
  }
  note(sec, 'Also worth knowing, even though it is not a <span class="mono">pip</span> package so it is left out of the chart above: <b>xmlstarlet</b> (a system binary, installed via the OS package manager) — command-line XPath querying, XSLT transforms, and in-place editing.');
  sec.appendChild(downloadLink('section', 'package_sizes.json', DATA.sizes));
})();

// ---------------------------------------------------------------------
// 1. Core Module
// ---------------------------------------------------------------------
(function () {
  const sec = topSection(root, 'core', 'Core Module',
    'The two ways to read an XML document: build the whole thing into an in-memory tree at once, or stream through it and only keep the piece you currently care about.');

  // -- parse --
  const s1 = subSection(sec, 'Parsing a whole document', 'parse_string / parse_file',
    'Read the file, build a complete in-memory tree, throw it away. All three approaches here end up holding the same kind of structure, so a direct ratio is meaningful.');
  const p1x = panel(s1, 'Throughput', 'higher is better');
  makeChart(p1x, { labels: DATA.core_parse.throughput.labels, series: DATA.core_parse.throughput.series, order: ['pygixml', 'lxml', 'elementtree'], yTitle: 'MB/s' });
  const p1t = panel(s1, 'Time to parse', 'lower is better');
  makeChart(p1t, { labels: DATA.core_parse.time.labels, series: DATA.core_parse.time.series, order: ['pygixml', 'lxml', 'elementtree'], yTitle: 'seconds' });
  const p1m = panel(s1, 'Peak resident memory', 'lower is better');
  makeChart(p1m, { labels: DATA.core_parse.memory.labels, series: DATA.core_parse.memory.series, order: ['pygixml', 'lxml', 'elementtree'], yTitle: 'MB' });
  eratios(s1, [
    { ref: 'lxml', metric: 'time', data: DATA.core_parse.e_time_lxml },
    { ref: 'elementtree', metric: 'time', data: DATA.core_parse.e_time_et },
    { ref: 'lxml', metric: 'memory', data: DATA.core_parse.e_mem_lxml },
    { ref: 'elementtree', metric: 'memory', data: DATA.core_parse.e_mem_et },
  ]);
  s1.appendChild(downloadLink('subsection', 'core_parse.json', DATA.core_parse));

  // -- iterparse --
  const s2 = subSection(sec, 'Streaming a document', 'iterparse',
    'Walk the file and only materialize the elements matching a given tag, one at a time, instead of holding the whole tree — meant for files too large (or too numerous) to fully load.');
  const p2x = panel(s2, 'Throughput', 'higher is better');
  makeChart(p2x, { labels: DATA.core_iterparse.throughput.labels, series: DATA.core_iterparse.throughput.series, order: ['pygixml', 'lxml', 'elementtree'], yTitle: 'MB/s' });
  const p2t = panel(s2, 'Time to stream every matching element', 'lower is better');
  makeChart(p2t, { labels: DATA.core_iterparse.time.labels, series: DATA.core_iterparse.time.series, order: ['pygixml', 'lxml', 'elementtree'], yTitle: 'seconds' });
  const p2m = panel(s2, 'Peak resident memory while streaming', 'lower is better');
  makeChart(p2m, { labels: DATA.core_iterparse.memory.labels, series: DATA.core_iterparse.memory.series, order: ['pygixml', 'lxml', 'elementtree'], yTitle: 'MB' });
  eratios(s2, [
    { ref: 'lxml', metric: 'time', data: DATA.core_iterparse.e_time_lxml },
    { ref: 'elementtree', metric: 'time', data: DATA.core_iterparse.e_time_et },
    { ref: 'lxml', metric: 'memory', data: DATA.core_iterparse.e_mem_lxml },
    { ref: 'elementtree', metric: 'memory', data: DATA.core_iterparse.e_mem_et },
  ]);
  note(s2, `An E[pygixml/ref] below 1× means pygixml is the slower (or heavier) side of that ratio — that is the case for streaming time here. This is a known, real gap: building a per-element object for the part of the document being streamed carries more per-element overhead in this library than the competitors' streaming paths do, independent of anything the parsing core itself is good or bad at.`);
  s2.appendChild(downloadLink('subsection', 'core_iterparse.json', DATA.core_iterparse));
})();

// ---------------------------------------------------------------------
// 2. Objectify
// ---------------------------------------------------------------------
(function () {
  const sec = topSection(root, 'objectify', 'Objectify',
    'XML in, attribute-style Python object out — read a value with <span class="mono">doc.channel.item.title</span> instead of tree-walking calls.');
  const px = panel(sec, 'Throughput', 'higher is better');
  makeChart(px, { labels: DATA.objectify.throughput.labels, series: DATA.objectify.throughput.series, order: ['pygixml', 'lxml'], yTitle: 'MB/s' });
  const pt = panel(sec, 'Time to build the object view', 'lower is better');
  makeChart(pt, { labels: DATA.objectify.time.labels, series: DATA.objectify.time.series, order: ['pygixml', 'lxml'], yTitle: 'seconds' });
  const pm = panel(sec, 'Peak resident memory', 'lower is better');
  makeChart(pm, { labels: DATA.objectify.memory.labels, series: DATA.objectify.memory.series, order: ['pygixml', 'lxml'], yTitle: 'MB' });
  eratios(sec, [
    { ref: 'lxml', metric: 'time', data: DATA.objectify.e_time_lxml },
    { ref: 'lxml', metric: 'memory', data: DATA.objectify.e_mem_lxml },
  ]);
  sec.appendChild(downloadLink('section', 'objectify.json', DATA.objectify));
})();

// ---------------------------------------------------------------------
// 3. Dictify
// ---------------------------------------------------------------------
(function () {
  const sec = topSection(root, 'dictify', 'Dictify',
    'XML in, a plain Python <span class="mono">dict</span> out (the usual <span class="mono">@attr</span> / <span class="mono">#text</span> convention), either for the whole document at once or one record at a time.');

  const s1 = subSection(sec, 'Whole document', 'dict', 'Convert the entire document to a nested dict in one call.');
  const p1x = panel(s1, 'Throughput', 'higher is better');
  makeChart(p1x, { labels: DATA.dictify_convert.throughput.labels, series: DATA.dictify_convert.throughput.series, order: ['pygixml', 'xmltodict'], yTitle: 'MB/s' });
  const p1 = panel(s1, 'Time to convert', 'lower is better');
  makeChart(p1, { labels: DATA.dictify_convert.time.labels, series: DATA.dictify_convert.time.series, order: ['pygixml', 'xmltodict'], yTitle: 'seconds' });
  const p1m = panel(s1, 'Peak resident memory', 'lower is better');
  makeChart(p1m, { labels: DATA.dictify_convert.memory.labels, series: DATA.dictify_convert.memory.series, order: ['pygixml', 'xmltodict'], yTitle: 'MB' });
  eratios(s1, [
    { ref: 'xmltodict', metric: 'time', data: DATA.dictify_convert.e_time_xmltodict },
    { ref: 'xmltodict', metric: 'memory', data: DATA.dictify_convert.e_mem_xmltodict },
  ]);
  s1.appendChild(downloadLink('subsection', 'dictify_convert.json', DATA.dictify_convert));

  const s2 = subSection(sec, 'Streaming', 'dict_stream', 'Same conversion, but yielded one record dict at a time for a repeated tag, instead of building the whole document as one dict first.');
  const p2x = panel(s2, 'Throughput', 'higher is better');
  makeChart(p2x, { labels: DATA.dictify_stream.throughput.labels, series: DATA.dictify_stream.throughput.series, order: ['pygixml', 'xmltodict'], yTitle: 'MB/s' });
  const p2t = panel(s2, 'Time to stream-convert every record', 'lower is better');
  makeChart(p2t, { labels: DATA.dictify_stream.time.labels, series: DATA.dictify_stream.time.series, order: ['pygixml', 'xmltodict'], yTitle: 'seconds' });
  const p2m = panel(s2, 'Peak resident memory', 'lower is better');
  makeChart(p2m, { labels: DATA.dictify_stream.memory.labels, series: DATA.dictify_stream.memory.series, order: ['pygixml', 'xmltodict'], yTitle: 'MB' });
  eratios(s2, [
    { ref: 'xmltodict', metric: 'time', data: DATA.dictify_stream.e_time_xmltodict },
    { ref: 'xmltodict', metric: 'memory', data: DATA.dictify_stream.e_mem_xmltodict },
  ]);
  s2.appendChild(downloadLink('subsection', 'dictify_stream.json', DATA.dictify_stream));
})();

// ---------------------------------------------------------------------
// 4. Jsonify
// ---------------------------------------------------------------------
(function () {
  const sec = topSection(root, 'jsonify', 'Jsonify',
    'XML in, JSON out — either the whole document as one JSON value, or one JSON object per record streamed out as it is read.');

  const s1 = subSection(sec, 'Whole document', 'json', 'Produce one JSON string holding the full document, end to end — parse plus serialize, compared against the same job done with a separate parser and a separate JSON-conversion step.');
  const p1x = panel(s1, 'Throughput', 'higher is better');
  makeChart(p1x, { labels: DATA.jsonify_json.throughput.labels, series: DATA.jsonify_json.throughput.series, order: ['pygixml', 'xmltodict', 'xmljson'], yTitle: 'MB/s' });
  const p1t = panel(s1, 'Time, parse + convert to JSON', 'lower is better');
  makeChart(p1t, { labels: DATA.jsonify_json.time.labels, series: DATA.jsonify_json.time.series, order: ['pygixml', 'xmltodict', 'xmljson'], yTitle: 'seconds' });
  const p1m = panel(s1, 'Peak resident memory', 'lower is better');
  makeChart(p1m, { labels: DATA.jsonify_json.memory.labels, series: DATA.jsonify_json.memory.series, order: ['pygixml', 'xmltodict', 'xmljson'], yTitle: 'MB' });
  eratios(s1, [
    { ref: 'xmltodict', metric: 'time', data: DATA.jsonify_json.e_time_xmltodict },
    { ref: 'xmljson', metric: 'time', data: DATA.jsonify_json.e_time_xmljson },
    { ref: 'xmltodict', metric: 'memory', data: DATA.jsonify_json.e_mem_xmltodict },
    { ref: 'xmljson', metric: 'memory', data: DATA.jsonify_json.e_mem_xmljson },
  ]);
  s1.appendChild(downloadLink('subsection', 'jsonify_json.json', DATA.jsonify_json));

  const s2 = subSection(sec, 'Streaming (JSON Lines)', 'jsonl', 'Write one JSON object per record as it is read, never holding the full result in memory. Nothing else in this suite streams JSON output the same way, so there is no like-for-like competitor to take a ratio against — this is reported on its own instead.');
  note(s2, `<b>Memory does not grow with input size.</b> Peak memory stayed within a few hundred KB across a 64× range of input (5,000 → 320,000 records) — the number below is essentially flat, which is the point of a streaming writer: memory is bounded by the current record, not by the document.`);
  const jl = DATA.jsonify_jsonl;
  const detBody = detailsBlock(s2, `Record-count scaling detail (${jl.memory_points.length} sizes, 5,000 → 320,000 records)`);
  const p2m = panel(detBody, 'Peak resident memory vs. record count', 'flat is the goal — lower still is better');
  lineChart(p2m, {
    labels: jl.memory_points.map(p => p.n.toLocaleString()),
    series: { pygixml: jl.memory_points.map(p => p.peak_rss_mb) },
    order: ['pygixml'], yTitle: 'MB', xLabel: 'records in the document',
  });
  const p2t = panel(detBody, 'Time vs. record count, two document shapes', 'lower is better');
  lineChart(p2t, {
    labels: jl.scaling_records.map(p => p.n.toLocaleString()),
    series: {
      pygixml: jl.scaling_records.map(p => p.seconds),
    },
    order: ['pygixml'],
    yTitle: 'seconds', xLabel: 'records (flat, repeated-sibling shape)',
  });
  note(s2, `That first shape (records as flat, repeated siblings) scales close to linearly with record count — each record costs about the same to stream regardless of how many came before it. A second, adversarial shape — records nested inside alternating wrapper tags rather than as flat siblings — does <b>not</b> share that scaling: time grew super-linearly as record count increased (see the downloadable data for the raw numbers), because tracking alternating nesting costs more per record as depth increases. Different growth curve, so it is called out here rather than folded into the chart above.`);
  s2.appendChild(downloadLink('subsection', 'jsonify_jsonl.json', DATA.jsonify_jsonl));
})();

// ---------------------------------------------------------------------
// 5. CLI
// ---------------------------------------------------------------------
(function () {
  const sec = topSection(root, 'cli', 'CLI',
    'Same XML→JSON job, but invoked as a command-line tool rather than a library call — full process startup included in every timing, since that is what actually happens when you run one of these from a shell or a script.');
  note(sec, `<b>pygixml</b> — <span class="cap-tag">query</span> <span class="cap-tag">jsonify</span> <span class="cap-tag">stream</span> <span class="cap-tag">cat</span> <span class="cap-tag">convert</span> · <b>yq</b> (its <span class="mono">xq</span> command) — <span class="cap-tag">query via jq syntax</span> <span class="cap-tag">convert XML ⇄ JSON/YAML/TOML</span> · also worth knowing, not measured here since it is a system binary rather than a Python CLI: <b>xmlstarlet</b> — <span class="cap-tag">XPath query</span> <span class="cap-tag">XSLT transform</span> <span class="cap-tag">in-place edit</span>.`);
  const p = panel(sec, 'Wall-clock time, XML file in → JSON on stdout', 'lower is better');
  const labels = DATA.cli.results.map(r => `${r.genre} / ${r.size}`);
  makeChart(p, {
    labels,
    series: {
      pygixml_cli: DATA.cli.results.map(r => r.pygixml_cli.available ? r.pygixml_cli.seconds : null),
      yq: DATA.cli.results.map(r => r.xq.available ? r.xq.seconds : null),
    },
    order: ['pygixml_cli', 'yq'],
    yTitle: 'seconds',
  });
  // E ratio for CLI
  (function () {
    const ratios = [];
    for (const r of DATA.cli.results) {
      if (r.pygixml_cli.available && r.xq.available) ratios.push(r.xq.seconds / r.pygixml_cli.seconds);
    }
    if (ratios.length) {
      const mean = ratios.reduce((a, b) => a + b, 0) / ratios.length;
      eratios(sec, [{ ref: 'yq', metric: 'time (process startup included)', data: { mean, n: ratios.length } }]);
    }
  })();
  sec.appendChild(downloadLink('section', 'cli.json', DATA.cli));
})();

// ---------------------------------------------------------------------
// System info (last, as requested)
// ---------------------------------------------------------------------
(function () {
  const sec = topSection(root, 'machine', 'Machine', 'Every number on this page came from a single run on this machine, back to back, no other load — not a claim about any other environment.');
  const si = DATA.system_info;
  const grid = el(`<div class="sysinfo-grid"></div>`);
  const rows = [
    ['CPU', si.cpu_model], ['Logical cores', si.logical_cores],
    ['RAM', si.ram_gib + ' GiB'], ['OS', si.os],
    ['Python', si.python_implementation + ' ' + si.python_version],
    ['Repeats per point', DATA.repeats + ' (best of)'],
  ];
  for (const [k, v] of rows) grid.appendChild(el(`<div><div class="v">${v}</div><div class="k">${k}</div></div>`));
  sec.appendChild(grid);
  sec.appendChild(downloadLink('section', 'system_info.json', si));
})();

document.getElementById('footer-note').innerHTML =
  'Numbers are best-of-N wall-clock time / peak RSS on the machine above; nothing here is a claim about any other machine. ' +
  'All figures were produced by this project\'s own benchmark scripts, run end to end for this report.';
