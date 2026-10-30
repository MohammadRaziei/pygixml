# ------------------------------------------------------------- results --
# The benchmark suite's only committed output is results/*.json: one raw
# JSON file per benchmark (throughput.json, html.json, scaling.json, ...),
# not one big merged file. The HTML page is NOT built here: the
# documentation build (root project, `cmake --build build --target
# sphinx_docs`) reads this directory and renders docs/benchmarks/index.html
# (docs/site/benchmarks/render_benchmarks.py).

file(MAKE_DIRECTORY "${PYGIXML_BENCH_RESULTS_DIR}")

set(RESULT_COPIES "")
foreach(_json IN LISTS PYGIXML_BENCH_ALL_RESULT_JSONS)
  get_filename_component(_name "${_json}" NAME)
  list(APPEND RESULT_COPIES "${PYGIXML_BENCH_RESULTS_DIR}/${_name}")
  add_custom_command(
    OUTPUT "${PYGIXML_BENCH_RESULTS_DIR}/${_name}"
    COMMAND ${CMAKE_COMMAND} -E copy "${_json}" "${PYGIXML_BENCH_RESULTS_DIR}/${_name}"
    DEPENDS "${_json}"
    COMMENT "pygixml benchmarks: results/${_name}"
  )
endforeach()

add_custom_target(pygixml_bench_report DEPENDS ${RESULT_COPIES})
add_dependencies(pygixml_bench_report
  pygixml_bench_throughput
  pygixml_bench_throughput_memory
  pygixml_bench_scaling
  pygixml_bench_memory
  pygixml_bench_sizes
  pygixml_bench_cli
  pygixml_bench_html
  pygixml_bench_system_info
)
