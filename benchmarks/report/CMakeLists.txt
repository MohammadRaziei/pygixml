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
  COMMAND "${PYGIXML_BENCH_VENV_PYTHON}" "${CMAKE_CURRENT_SOURCE_DIR}/generate_report.py"
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
  pygixml_bench_system_info
  pygixml_bench_chartjs
)
