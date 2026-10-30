# ------------------------------------------------------------- results --
# The benchmark suite's only committed output is one JSON file with the
# raw numbers. The HTML page is NOT built here: the documentation build
# (root project, `cmake --build build --target sphinx_docs`) loads this
# JSON and renders docs/benchmarks/index.html from it
# (docs/site/benchmarks/render_benchmarks.py).

set(RESULTS_JSON "${PYGIXML_BENCH_RESULTS_DIR}/benchmarks.json")

file(MAKE_DIRECTORY "${PYGIXML_BENCH_RESULTS_DIR}")

add_custom_command(
  OUTPUT "${RESULTS_JSON}"
  # -W ignore::RuntimeWarning:site -- see the comment on VENV_PYTHON in
  # python/CMakeLists.txt for why every venv-python invocation carries this.
  COMMAND "${PYGIXML_BENCH_VENV_PYTHON}" -W "ignore::RuntimeWarning:site"
          "${CMAKE_CURRENT_SOURCE_DIR}/bundle_results.py"
          "${PYGIXML_BENCH_RESULTS_SCRATCH_DIR}" "${RESULTS_JSON}"
  DEPENDS
    "${PYGIXML_BENCH_VENV_STAMP}"
    "${CMAKE_CURRENT_SOURCE_DIR}/bundle_results.py"
    ${PYGIXML_BENCH_ALL_RESULT_JSONS}
  COMMENT "pygixml benchmarks: bundling every result into results/benchmarks.json"
  USES_TERMINAL
)
add_custom_target(pygixml_bench_report DEPENDS "${RESULTS_JSON}")
add_dependencies(pygixml_bench_report
  pygixml_bench_throughput
  pygixml_bench_throughput_memory
  pygixml_bench_scaling
  pygixml_bench_memory
  pygixml_bench_sizes
  pygixml_bench_cli
  pygixml_bench_system_info
)
