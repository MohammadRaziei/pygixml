# ------------------------------------------------------------- Chart.js --
# Fetched fresh via plain file(DOWNLOAD) from the npm registry (a tarball,
# same as `npm pack` would give you) -- nothing vendored in the source
# tree, matching the "downloads live in the build dir, not git" rule
# this whole benchmark suite follows.

set(CHARTJS_VERSION "4.5.1" CACHE STRING "Chart.js version to embed in the report")
set(CHARTJS_DL_DIR "${CMAKE_CURRENT_BINARY_DIR}/_chartjs")
set(CHARTJS_ARCHIVE "${CHARTJS_DL_DIR}/chart.js-${CHARTJS_VERSION}.tgz")
set(CHARTJS_EXTRACTED "${CHARTJS_DL_DIR}/extracted")
set(CHARTJS_UMD_MIN "${CHARTJS_EXTRACTED}/package/dist/chart.umd.min.js")

file(MAKE_DIRECTORY "${CHARTJS_DL_DIR}")
file(MAKE_DIRECTORY "${CHARTJS_EXTRACTED}")

add_custom_command(
  OUTPUT "${CHARTJS_UMD_MIN}"
  COMMAND ${CMAKE_COMMAND} -DURL=https://registry.npmjs.org/chart.js/-/chart.js-${CHARTJS_VERSION}.tgz
                            -DDEST=${CHARTJS_ARCHIVE}
                            -P "${CMAKE_CURRENT_SOURCE_DIR}/../cmake/Download.cmake"
  COMMAND ${CMAKE_COMMAND} -E tar xzf "${CHARTJS_ARCHIVE}"
          WORKING_DIRECTORY "${CHARTJS_EXTRACTED}"
  COMMENT "pygixml benchmarks: fetching Chart.js ${CHARTJS_VERSION} (for the standalone report)"
  USES_TERMINAL
)
add_custom_target(pygixml_bench_chartjs DEPENDS "${CHARTJS_UMD_MIN}")

# ------------------------------------------------------------- report --

set(REPORT_HTML "${PYGIXML_BENCH_RESULTS_DIR}/report.html")

file(MAKE_DIRECTORY "${PYGIXML_BENCH_RESULTS_DIR}")

add_custom_command(
  OUTPUT "${REPORT_HTML}"
  # -W ignore::RuntimeWarning:site -- see the comment on VENV_PYTHON in
  # python/CMakeLists.txt for why every venv-python invocation carries this.
  COMMAND "${PYGIXML_BENCH_VENV_PYTHON}" -W "ignore::RuntimeWarning:site"
          "${CMAKE_CURRENT_SOURCE_DIR}/generate_report.py"
          "${PYGIXML_BENCH_RESULTS_SCRATCH_DIR}" "${REPORT_HTML}"
          --chartjs-path "${CHARTJS_UMD_MIN}"
  DEPENDS
    "${PYGIXML_BENCH_VENV_STAMP}"
    "${CHARTJS_UMD_MIN}"
    "${CMAKE_CURRENT_SOURCE_DIR}/generate_report.py"
    "${CMAKE_CURRENT_SOURCE_DIR}/template.html.jinja2"
    ${PYGIXML_BENCH_ALL_RESULT_JSONS}
  COMMENT "pygixml benchmarks: rendering the standalone HTML report"
  USES_TERMINAL
)
add_custom_target(pygixml_bench_report DEPENDS "${REPORT_HTML}")
add_dependencies(pygixml_bench_report
  pygixml_bench_throughput
  pygixml_bench_throughput_memory
  pygixml_bench_scaling
  pygixml_bench_memory
  pygixml_bench_sizes
  pygixml_bench_cli
  pygixml_bench_system_info
  pygixml_bench_chartjs
)

# ------------------------------------------------------- docs deploy --
# The one target in this whole directory that breaks the "fully
# self-contained, copyable elsewhere" rule on purpose: it reaches into
# ../../docs/, which only exists inside a full pygixml checkout, not a
# standalone copy of benchmarks/ elsewhere -- refreshing the docs
# site's embedded copy of the report IS a full-checkout operation.
#
#   cmake --build build --target pygixml_benchmark_report
#
# depends on pygixml_bench_report by name (same target-dependency style
# as pygixml_benchmark below -- a file-level OUTPUT dependency on
# REPORT_HTML across the python/ <-> report/ directory boundary hits a
# Unix-Makefiles-generator quirk where the cross-directory rule isn't
# always visible from a build invoked directly at this target), which
# in turn already depends on the entire suite. So this one target runs
# everything and then copies the freshly generated report straight into
# docs/source/_static/benchmark-report.html -- no separate manual
# script invocation afterward.
set(DOCS_UPDATE_SCRIPT "${CMAKE_CURRENT_SOURCE_DIR}/../../docs/update_benchmark_report.py")

if(EXISTS "${DOCS_UPDATE_SCRIPT}")
  add_custom_target(pygixml_benchmark_report
    COMMAND "${PYGIXML_BENCH_VENV_PYTHON}" -W "ignore::RuntimeWarning:site" "${DOCS_UPDATE_SCRIPT}"
    DEPENDS pygixml_bench_report
    COMMENT "pygixml benchmarks: copying report.html into docs/source/_static/"
    USES_TERMINAL
  )
else()
  message(STATUS "pygixml benchmarks: ${DOCS_UPDATE_SCRIPT} not found -- "
                  "skipping the pygixml_benchmark_report target (this looks like a "
                  "standalone copy of benchmarks/, not a full pygixml checkout)")
endif()
