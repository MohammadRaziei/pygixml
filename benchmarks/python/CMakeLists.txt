set(PY_DIR "${CMAKE_CURRENT_SOURCE_DIR}")
set(VENV_DIR "${CMAKE_CURRENT_BINARY_DIR}/venv")
set(RESULTS_DIR "${CMAKE_CURRENT_BINARY_DIR}/results")
set(SCRATCH_DIR "${CMAKE_CURRENT_BINARY_DIR}/scratch")

if(WIN32)
  set(VENV_PYTHON "${VENV_DIR}/Scripts/python.exe")
else()
  set(VENV_PYTHON "${VENV_DIR}/bin/python")
endif()
# Every invocation below passes -W ignore::RuntimeWarning:site: CMake's
# Ninja generator relativizes absolute in-build-tree paths in generated
# build commands for portability (e.g. "report/../python/venv/bin/python"
# instead of the fully-resolved path) -- functionally identical, ".."
# resolves correctly, but it trips a sys.prefix/pyvenv.cfg consistency
# check Python 3.11+ added in the frozen `site` module. Scoped to that
# one module so it never hides a real RuntimeWarning from anything else.

file(MAKE_DIRECTORY "${RESULTS_DIR}")
file(MAKE_DIRECTORY "${SCRATCH_DIR}")

# ---------------------------------------------------------------- venv --
# Self-contained: pygixml itself is installed from a fresh git
# checkout (PYGIXML_BENCH_GITHUB_URL), not from the local ../../src --
# this directory never imports anything from the parent project.
#
# This runs at CONFIGURE time (execute_process, right here while
# CMakeLists.txt is being processed), not at build time -- so
# `cmake -S . -B build` alone leaves you with a ready venv, and
# `cmake --build build --target pygixml_benchmark` only has to run
# the actual benchmarks. The venv itself still lives under the build
# directory (${CMAKE_CURRENT_BINARY_DIR}/venv), it's just populated
# earlier than before.
#
# Guarded by a stamp file: reconfiguring (cmake -S . -B build again)
# does NOT reinstall unless the venv is missing. To force a rebuild
# (e.g. after changing requirements.txt or PYGIXML_BENCH_GITHUB_URL),
# delete the stamp file or the whole build directory.

set(VENV_STAMP "${CMAKE_CURRENT_BINARY_DIR}/.venv_ready")

if(NOT EXISTS "${VENV_STAMP}")
  message(STATUS "pygixml benchmarks: creating venv at ${VENV_DIR} (configure time)...")
  execute_process(
    COMMAND ${Python3_EXECUTABLE} -m venv "${VENV_DIR}"
    RESULT_VARIABLE _pygixml_venv_rc
  )
  if(NOT _pygixml_venv_rc EQUAL 0)
    message(FATAL_ERROR "pygixml benchmarks: failed to create venv at ${VENV_DIR}")
  endif()

  message(STATUS "pygixml benchmarks: installing competitors + pygixml from ${PYGIXML_BENCH_GITHUB_URL} (configure time)...")
  execute_process(
    COMMAND "${VENV_PYTHON}" -W "ignore::RuntimeWarning:site" -m pip install --upgrade pip --quiet
    RESULT_VARIABLE _pygixml_pip_upgrade_rc
  )
  if(NOT _pygixml_pip_upgrade_rc EQUAL 0)
    message(FATAL_ERROR "pygixml benchmarks: failed to upgrade pip in ${VENV_DIR}")
  endif()

  execute_process(
    COMMAND "${VENV_PYTHON}" -W "ignore::RuntimeWarning:site" -m pip install -r "${PY_DIR}/requirements.txt" --quiet
    RESULT_VARIABLE _pygixml_pip_req_rc
  )
  if(NOT _pygixml_pip_req_rc EQUAL 0)
    message(FATAL_ERROR "pygixml benchmarks: failed to install ${PY_DIR}/requirements.txt")
  endif()

  execute_process(
    COMMAND "${VENV_PYTHON}" -W "ignore::RuntimeWarning:site" -m pip install --force-reinstall --no-deps "${PYGIXML_BENCH_GITHUB_URL}" --quiet
    RESULT_VARIABLE _pygixml_pip_pkg_rc
  )
  if(NOT _pygixml_pip_pkg_rc EQUAL 0)
    message(FATAL_ERROR "pygixml benchmarks: failed to install pygixml from ${PYGIXML_BENCH_GITHUB_URL}")
  endif()

  file(TOUCH "${VENV_STAMP}")
else()
  message(STATUS "pygixml benchmarks: venv already present at ${VENV_DIR} -- skipping "
                  "(delete ${VENV_STAMP} to force recreation)")
endif()

add_custom_target(pygixml_bench_venv)

# -------------------------------------------------------------- corpus --

set(CORPUS_DIR "${SCRATCH_DIR}/corpus")
set(CORPUS_MANIFEST "${CORPUS_DIR}/manifest.json")

add_custom_command(
  OUTPUT "${CORPUS_MANIFEST}"
  COMMAND "${VENV_PYTHON}" -W "ignore::RuntimeWarning:site" "${PY_DIR}/corpus.py" "${CORPUS_DIR}"
  DEPENDS "${VENV_STAMP}" "${PY_DIR}/corpus.py"
  COMMENT "pygixml benchmarks: generating the synthetic corpus"
  USES_TERMINAL
)
add_custom_target(pygixml_bench_corpus DEPENDS "${CORPUS_MANIFEST}")

# --------------------------------------------------------- real corpus --
# PYGIXML_REAL_CORPUS_DIR comes from FetchRealCorpus.cmake (included by
# the parent CMakeLists.txt before add_subdirectory(python)) -- empty
# if the download failed, in which case this target is skipped and
# bench_throughput just runs on the synthetic corpus alone.

set(REAL_CORPUS_XML_DIR "${SCRATCH_DIR}/real_corpus")
set(REAL_CORPUS_MANIFEST "${REAL_CORPUS_XML_DIR}/manifest.json")
set(THROUGHPUT_MANIFESTS "${CORPUS_MANIFEST}")

if(PYGIXML_REAL_CORPUS_DIR)
  set(_giant_xml_arg "")
  set(_giant_xml_depend "")
  if(PYGIXML_REAL_GIANT_XML)
    set(_giant_xml_arg --giant-xml "${PYGIXML_REAL_GIANT_XML}")
    set(_giant_xml_depend "${PYGIXML_REAL_GIANT_XML}")
  endif()
  add_custom_command(
    OUTPUT "${REAL_CORPUS_MANIFEST}"
    COMMAND "${VENV_PYTHON}" -W "ignore::RuntimeWarning:site" "${PY_DIR}/real_corpus_manifest.py"
            "${PYGIXML_REAL_CORPUS_DIR}" "${REAL_CORPUS_XML_DIR}" "${REAL_CORPUS_MANIFEST}"
            ${_giant_xml_arg}
    DEPENDS "${VENV_STAMP}" "${PY_DIR}/real_corpus_manifest.py" ${_giant_xml_depend}
    COMMENT "pygixml benchmarks: indexing the real-world corpus (icons + Wikipedia, if available)"
    USES_TERMINAL
  )
  add_custom_target(pygixml_bench_real_corpus DEPENDS "${REAL_CORPUS_MANIFEST}")
  list(APPEND THROUGHPUT_MANIFESTS "${REAL_CORPUS_MANIFEST}")
else()
  add_custom_target(pygixml_bench_real_corpus
    COMMENT "pygixml benchmarks: real corpus unavailable (download failed) -- skipping"
  )
endif()

# ---------------------------------------------------------------- sizes --

set(SIZES_JSON "${RESULTS_DIR}/sizes.json")

add_custom_command(
  OUTPUT "${SIZES_JSON}"
  COMMAND "${VENV_PYTHON}" -W "ignore::RuntimeWarning:site" "${PY_DIR}/bench_sizes.py" "${SIZES_JSON}"
  DEPENDS "${VENV_STAMP}" "${PY_DIR}/bench_sizes.py"
  COMMENT "pygixml benchmarks: comparing install footprint (pip-size)"
  USES_TERMINAL
)
add_custom_target(pygixml_bench_sizes DEPENDS "${SIZES_JSON}")

# ----------------------------------------------------------- throughput --
# Repeats per (library, corpus entry, operation) cell -- best (min) of
# these is kept. Configurable because "how many repeats is enough" is a
# real tradeoff (noise vs. wall-clock CI time), not something to bake
# in; 7 is a reasonable default for a quiet machine.

set(PYGIXML_BENCH_REPEATS "7" CACHE STRING
    "Timed repeats per (library, corpus entry, operation) cell in bench_throughput.py; best (min) is kept")

set(THROUGHPUT_JSON "${RESULTS_DIR}/throughput.json")

add_custom_command(
  OUTPUT "${THROUGHPUT_JSON}"
  COMMAND "${VENV_PYTHON}" -W "ignore::RuntimeWarning:site" "${PY_DIR}/bench_throughput.py" ${THROUGHPUT_MANIFESTS} "${THROUGHPUT_JSON}"
          --repeats "${PYGIXML_BENCH_REPEATS}"
  DEPENDS "${VENV_STAMP}" "${PY_DIR}/bench_throughput.py" "${CORPUS_MANIFEST}"
          "$<$<BOOL:${PYGIXML_REAL_CORPUS_DIR}>:${REAL_CORPUS_MANIFEST}>"
  COMMENT "pygixml benchmarks: parse + xml-to-json throughput, all libraries (${PYGIXML_BENCH_REPEATS} repeats/cell)"
  USES_TERMINAL
)
add_custom_target(pygixml_bench_throughput DEPENDS "${THROUGHPUT_JSON}")
add_dependencies(pygixml_bench_throughput pygixml_bench_corpus pygixml_bench_real_corpus)

# ------------------------------------------------------- throughput memory --
# Memory alongside speed for the SAME four throughput.json operations
# (parse, dict_convert, to_object, xml_to_json) -- not just the
# separate stream_dump-vs-DOM story below. One driver script, not one
# CMake target per (entry, operation, library): the driver never opens
# the corpus files itself (only reads the manifest's metadata and hands
# each *path* to a freshly spawned child), so it's exempt from the
# ru_maxrss/execve gotcha explained below -- see
# bench_op_memory_driver.py's docstring for exactly why that's still
# safe.

set(THROUGHPUT_MEMORY_JSON "${RESULTS_DIR}/throughput_memory.json")

add_custom_command(
  OUTPUT "${THROUGHPUT_MEMORY_JSON}"
  COMMAND "${VENV_PYTHON}" -W "ignore::RuntimeWarning:site" "${PY_DIR}/bench_op_memory_driver.py" ${THROUGHPUT_MANIFESTS} "${THROUGHPUT_MEMORY_JSON}"
  DEPENDS "${VENV_STAMP}" "${PY_DIR}/bench_op_memory_driver.py" "${PY_DIR}/bench_op_memory_one.py" "${CORPUS_MANIFEST}"
          "$<$<BOOL:${PYGIXML_REAL_CORPUS_DIR}>:${REAL_CORPUS_MANIFEST}>"
  COMMENT "pygixml benchmarks: peak memory for parse/dictify/objectify/jsonify, all libraries"
  USES_TERMINAL
)
add_custom_target(pygixml_bench_throughput_memory DEPENDS "${THROUGHPUT_MEMORY_JSON}")
add_dependencies(pygixml_bench_throughput_memory pygixml_bench_corpus pygixml_bench_real_corpus)

# -------------------------------------------------------------- scaling --

set(SCALING_JSON "${RESULTS_DIR}/scaling.json")

add_custom_command(
  OUTPUT "${SCALING_JSON}"
  COMMAND "${VENV_PYTHON}" -W "ignore::RuntimeWarning:site" "${PY_DIR}/bench_scaling.py" "${SCALING_JSON}"
          --tmp-dir "${SCRATCH_DIR}/scaling"
  DEPENDS "${VENV_STAMP}" "${PY_DIR}/bench_scaling.py" "${PY_DIR}/corpus.py"
  COMMENT "pygixml benchmarks: time vs N (records shape vs interleaved shape)"
  USES_TERMINAL
)
add_custom_target(pygixml_bench_scaling DEPENDS "${SCALING_JSON}")

# --------------------------------------------------------------- memory --
# See bench_memory_gen.py's docstring for why this is three separate
# steps (generate, then one fresh process per data point, then
# aggregate) instead of one script with a loop: a long-running Python
# driver's own memory growth contaminates ru_maxrss for anything it
# later forks -- measurement processes must be spawned by something
# that's never touched the corpus, i.e. CMake/the shell, not Python.

set(MEMORY_SIZES 5000 20000 80000 320000)
set(MEMORY_APPROACHES pygixml_stream_dump pygixml_dom lxml_plus_xmljson xmltodict)

string(REPLACE ";" "," MEMORY_SIZES_CSV "${MEMORY_SIZES}")
set(MEMORY_GEN_DIR "${SCRATCH_DIR}/memory_inputs")
set(MEMORY_GEN_MANIFEST "${MEMORY_GEN_DIR}/manifest.json")

add_custom_command(
  OUTPUT "${MEMORY_GEN_MANIFEST}"
  COMMAND "${VENV_PYTHON}" -W "ignore::RuntimeWarning:site" "${PY_DIR}/bench_memory_gen.py" "${MEMORY_GEN_DIR}" --sizes "${MEMORY_SIZES_CSV}"
  DEPENDS "${VENV_STAMP}" "${PY_DIR}/bench_memory_gen.py" "${PY_DIR}/corpus.py"
  COMMENT "pygixml benchmarks: writing memory-benchmark input files (${MEMORY_SIZES_CSV} records)"
  USES_TERMINAL
)
add_custom_target(pygixml_bench_memory_gen DEPENDS "${MEMORY_GEN_MANIFEST}")

set(MEMORY_POINTS_DIR "${SCRATCH_DIR}/memory_points")
file(MAKE_DIRECTORY "${MEMORY_POINTS_DIR}")
set(MEMORY_POINT_JSONS "")

foreach(_n ${MEMORY_SIZES})
  foreach(_approach ${MEMORY_APPROACHES})
    set(_xml "${MEMORY_GEN_DIR}/records_${_n}.xml")
    set(_scratch_out "${SCRATCH_DIR}/memory_scratch_${_approach}_${_n}.json")
    set(_point_json "${MEMORY_POINTS_DIR}/${_approach}_${_n}.json")
    add_custom_command(
      OUTPUT "${_point_json}"
      COMMAND "${VENV_PYTHON}" -W "ignore::RuntimeWarning:site" "${PY_DIR}/bench_memory_one.py"
              "${_approach}" "${_xml}" "${_scratch_out}" "${_point_json}" --n "${_n}"
      DEPENDS "${VENV_STAMP}" "${PY_DIR}/bench_memory_one.py" "${MEMORY_GEN_MANIFEST}"
      COMMENT "pygixml benchmarks: memory, ${_approach}, n=${_n}"
      USES_TERMINAL
    )
    list(APPEND MEMORY_POINT_JSONS "${_point_json}")
  endforeach()
endforeach()

set(MEMORY_JSON "${RESULTS_DIR}/memory.json")

add_custom_command(
  OUTPUT "${MEMORY_JSON}"
  COMMAND "${VENV_PYTHON}" -W "ignore::RuntimeWarning:site" "${PY_DIR}/bench_memory_aggregate.py" "${MEMORY_POINTS_DIR}" "${MEMORY_JSON}"
  DEPENDS "${VENV_STAMP}" "${PY_DIR}/bench_memory_aggregate.py" ${MEMORY_POINT_JSONS}
  COMMENT "pygixml benchmarks: combining memory data points"
  USES_TERMINAL
)
add_custom_target(pygixml_bench_memory DEPENDS "${MEMORY_JSON}")

# Note: the "what each library can actually do" feature matrix used to
# be generated here (features.py -> features.json -> a table in the
# report). It's static, hand-curated content -- nothing to run, no
# JSON worth round-tripping -- so it now lives as a plain HTML table on
# the landing page instead (docs/landing/index.html.in), not as a
# benchmark pipeline step.

# --------------------------------------------------------- system info --
# What machine this actually ran on -- reported plainly in the report
# footer, not folded into any of the other JSON files above.

set(SYSTEM_INFO_JSON "${RESULTS_DIR}/system_info.json")

add_custom_command(
  OUTPUT "${SYSTEM_INFO_JSON}"
  COMMAND "${VENV_PYTHON}" -W "ignore::RuntimeWarning:site" "${PY_DIR}/system_info.py" "${SYSTEM_INFO_JSON}"
  DEPENDS "${VENV_STAMP}" "${PY_DIR}/system_info.py"
  COMMENT "pygixml benchmarks: recording machine specs (CPU/RAM/OS)"
  USES_TERMINAL
)
add_custom_target(pygixml_bench_system_info DEPENDS "${SYSTEM_INFO_JSON}")

# Expose to the parent scope (report/CMakeLists.txt needs these paths)
set(PYGIXML_BENCH_RESULTS_SCRATCH_DIR "${RESULTS_DIR}" PARENT_SCOPE)
set(PYGIXML_BENCH_VENV_PYTHON "${VENV_PYTHON}" PARENT_SCOPE)
set(PYGIXML_BENCH_VENV_STAMP "${VENV_STAMP}" PARENT_SCOPE)
set(PYGIXML_BENCH_ALL_RESULT_JSONS
    "${THROUGHPUT_JSON}" "${THROUGHPUT_MEMORY_JSON}" "${SCALING_JSON}" "${MEMORY_JSON}" "${SIZES_JSON}" "${SYSTEM_INFO_JSON}"
    PARENT_SCOPE)
