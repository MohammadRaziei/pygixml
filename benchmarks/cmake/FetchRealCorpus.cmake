# FetchRealCorpus.cmake
#
# Downloads a real-world XML corpus (Bootstrap Icons -- SVG is XML;
# real, production, MIT-licensed markup, not generated for this
# benchmark) via plain file(DOWNLOAD), no FetchContent needed since
# we just want the raw files, not to build anything from them.
#
# Where the extracted files end up depends on their total size:
#   - below PYGIXML_BENCH_CORPUS_SIZE_THRESHOLD_BYTES: the build
#     directory (ephemeral -- gone on a clean build, which is fine,
#     it's small enough to re-fetch quickly).
#   - at or above the threshold: benchmarks/corpus/ in the SOURCE
#     tree (persistent across clean builds, so it isn't re-downloaded
#     every time) -- but with a .gitignore containing `*` written
#     into it, so the actual downloaded files are never committed.
#
# Defines PYGIXML_REAL_CORPUS_DIR for the caller to use.

set(PYGIXML_BENCH_CORPUS_SIZE_THRESHOLD_BYTES 2000000 CACHE STRING
    "Real corpus total size (bytes) at/above which it's cached in a persistent, gitignored benchmarks/corpus/ instead of the build directory")

set(_pygixml_corpus_url "https://codeload.github.com/twbs/icons/tar.gz/refs/heads/main")
set(_pygixml_corpus_dl_dir "${CMAKE_CURRENT_BINARY_DIR}/_corpus_download")
set(_pygixml_corpus_archive "${_pygixml_corpus_dl_dir}/bootstrap-icons.tar.gz")
set(_pygixml_corpus_extracted "${_pygixml_corpus_dl_dir}/extracted")

file(MAKE_DIRECTORY "${_pygixml_corpus_dl_dir}")

if(NOT EXISTS "${_pygixml_corpus_archive}")
  message(STATUS "pygixml benchmarks: downloading real-world XML corpus (Bootstrap Icons SVGs)...")
  file(DOWNLOAD
    "${_pygixml_corpus_url}"
    "${_pygixml_corpus_archive}"
    STATUS _pygixml_dl_status
    TIMEOUT 60
  )
  list(GET _pygixml_dl_status 0 _pygixml_dl_code)
  if(NOT _pygixml_dl_code EQUAL 0)
    list(GET _pygixml_dl_status 1 _pygixml_dl_msg)
    message(WARNING "pygixml benchmarks: could not download the real-world corpus (${_pygixml_dl_msg}). "
                     "Throughput/parse benchmarks will run on the synthetic corpus only.")
    file(REMOVE "${_pygixml_corpus_archive}")
  endif()
endif()

set(PYGIXML_REAL_CORPUS_DIR "")

if(EXISTS "${_pygixml_corpus_archive}")
  if(NOT EXISTS "${_pygixml_corpus_extracted}")
    file(MAKE_DIRECTORY "${_pygixml_corpus_extracted}")
    file(ARCHIVE_EXTRACT
      INPUT "${_pygixml_corpus_archive}"
      DESTINATION "${_pygixml_corpus_extracted}"
    )
  endif()

  file(GLOB_RECURSE _pygixml_svg_files "${_pygixml_corpus_extracted}/*.svg")
  set(_pygixml_total_bytes 0)
  foreach(_f ${_pygixml_svg_files})
    file(SIZE "${_f}" _sz)
    math(EXPR _pygixml_total_bytes "${_pygixml_total_bytes} + ${_sz}")
  endforeach()

  list(LENGTH _pygixml_svg_files _pygixml_svg_count)
  message(STATUS "pygixml benchmarks: real corpus has ${_pygixml_svg_count} SVG files, "
                  "${_pygixml_total_bytes} bytes total")

  if(_pygixml_total_bytes GREATER_EQUAL PYGIXML_BENCH_CORPUS_SIZE_THRESHOLD_BYTES)
    set(PYGIXML_REAL_CORPUS_DIR "${CMAKE_CURRENT_SOURCE_DIR}/corpus")
    file(MAKE_DIRECTORY "${PYGIXML_REAL_CORPUS_DIR}")
    file(WRITE "${PYGIXML_REAL_CORPUS_DIR}/.gitignore" "*\n!.gitignore\n")
    message(STATUS "pygixml benchmarks: corpus is ${_pygixml_total_bytes} bytes (>= threshold) "
                    "-> caching persistently in ${PYGIXML_REAL_CORPUS_DIR} (gitignored)")
  else()
    set(PYGIXML_REAL_CORPUS_DIR "${CMAKE_CURRENT_BINARY_DIR}/corpus")
    file(MAKE_DIRECTORY "${PYGIXML_REAL_CORPUS_DIR}")
    message(STATUS "pygixml benchmarks: corpus is ${_pygixml_total_bytes} bytes (< threshold) "
                    "-> using ephemeral build-dir cache ${PYGIXML_REAL_CORPUS_DIR}")
  endif()

  if(_pygixml_svg_files)
    file(COPY ${_pygixml_svg_files} DESTINATION "${PYGIXML_REAL_CORPUS_DIR}")
  endif()
endif()
