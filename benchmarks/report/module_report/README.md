# module_report (Core Module / Objectify / Dictify / Jsonify / CLI report)

An alternate report layout to `generate_report.py`'s standard
`report.html`, organized by *module* (Package Footprint, Core Module,
Objectify, Dictify, Jsonify, CLI, machine info) rather than by
competitor library.

Regenerate after a fresh `cmake --build build --target pygixml_benchmark`
run (which populates `../results/*.json`, including `cli.json` from
`benchmarks/python/bench_cli.py` -- not yet wired into the CMake target
itself, so run that one by hand first if you need fresh CLI numbers):

    python3 benchmarks/report/module_report/build_data.py

This reads `../results/*.json` and writes `data.json` next to itself,
then assemble the single self-contained report file -- the *only*
file `benchmarks/results/` should end up holding:

    python3 -c "
    from pathlib import Path
    here = Path('benchmarks/report/module_report')
    html = (here / 'template.html').read_text() \
        .replace('__DATA_JSON__', (here / 'data.json').read_text()) \
        .replace('__APP_JS__', (here / 'app.js').read_text())
    Path('benchmarks/results/report.html').write_text(html)
    "

`data.json` and the loose `*.json` files under `results/` are
intermediates -- useful while iterating on `app.js`/`template.html`,
but not meant to ship; only `results/report.html` is the deliverable.
