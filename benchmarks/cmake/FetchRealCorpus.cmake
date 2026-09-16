# FetchRealCorpus.cmake
#
# Downloads a real-world XML corpus (Bootstrap Icons -- SVG is XML;
# real, production, MIT-licensed markup, not generated for this
# benchmark) via plain file(DOWNLOAD), no FetchContent needed since
# we just want the raw files, not to build anything from them.
#
# Always lands in benchmarks/corpus/ in the SOURCE tree (persistent
# across clean `build/` wipes, so it isn't re-downloaded every time)
# -- with a .gitignore containing `*` written into it, so the actual
# downloaded files are never committed, only the folder structure.
# This runs at CONFIGURE time (this file is include()'d directly by
# the top-level CMakeLists.txt, before add_subdirectory()), so
# `cmake -S . -B build` alone is enough to have the corpus ready.
#
# Defines PYGIXML_REAL_CORPUS_DIR for the caller to use.

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

  set(PYGIXML_REAL_CORPUS_DIR "${CMAKE_CURRENT_SOURCE_DIR}/corpus")
  file(MAKE_DIRECTORY "${PYGIXML_REAL_CORPUS_DIR}")
  file(WRITE "${PYGIXML_REAL_CORPUS_DIR}/.gitignore" "*\n!.gitignore\n")
  message(STATUS "pygixml benchmarks: caching real corpus persistently in "
                  "${PYGIXML_REAL_CORPUS_DIR} (gitignored, not re-downloaded on a clean build/ wipe)")

  if(_pygixml_svg_files)
    file(COPY ${_pygixml_svg_files} DESTINATION "${PYGIXML_REAL_CORPUS_DIR}")
  endif()
endif()

# ----------------------------------------------------- a genuinely giant --
# ----------------------------------------- real-world XML, best-effort --
#
# The icon set above is real XML, but it's still small (a few MB). This
# is the corpus that actually matches pygixml's headline use case: one
# real, giant, XML document. Simple English Wikipedia's "abstracts"
# dump (a stable, non-dated "latest" URL) is a real, public, tens-of-MB
# XML file. Best-effort only: some networks (sandboxed CI, corporate
# proxies) can't reach dumps.wikimedia.org at all, so a failure here is
# a warning, not a build error -- the rest of the corpus (and the whole
# benchmark suite) works fine without it. This part was not testable
# from the environment this benchmark suite was originally built in
# (a network allowlist that doesn't include dumps.wikimedia.org) --
# verify it fetches successfully in your own environment before relying
# on it; if it doesn't, everything downstream degrades gracefully to
# the icon corpus alone.

set(PYGIXML_BENCH_WIKIPEDIA_URL
    "https://dumps.wikimedia.org/simplewiki/latest/simplewiki-latest-abstract.xml.gz"
    CACHE STRING "A real, giant XML document to add to the corpus (best-effort; set to an empty string to skip entirely)")

set(PYGIXML_REAL_GIANT_XML "")

if(PYGIXML_BENCH_WIKIPEDIA_URL)
  set(_wiki_dl_dir "${CMAKE_CURRENT_BINARY_DIR}/_corpus_download")
  set(_wiki_gz "${_wiki_dl_dir}/wikipedia-abstracts.xml.gz")
  set(_wiki_xml "${_wiki_dl_dir}/wikipedia-abstracts.xml")

  if(NOT EXISTS "${_wiki_gz}" AND NOT EXISTS "${_wiki_xml}")
    message(STATUS "pygixml benchmarks: attempting to download a real giant XML "
                    "(Simple English Wikipedia abstracts) -- best-effort, see FetchRealCorpus.cmake")
    file(DOWNLOAD "${PYGIXML_BENCH_WIKIPEDIA_URL}" "${_wiki_gz}"
         STATUS _wiki_dl_status TIMEOUT 120)
    list(GET _wiki_dl_status 0 _wiki_dl_code)
    if(NOT _wiki_dl_code EQUAL 0)
      list(GET _wiki_dl_status 1 _wiki_dl_msg)
      message(WARNING "pygixml benchmarks: could not download the Wikipedia XML corpus "
                       "(${_wiki_dl_msg}) -- this is expected on a restricted network; "
                       "throughput benchmarks will run on the icon corpus + synthetic corpus only.")
      file(REMOVE "${_wiki_gz}")
    endif()
  endif()

  if(EXISTS "${_wiki_gz}" AND NOT EXISTS "${_wiki_xml}")
    file(ARCHIVE_EXTRACT INPUT "${_wiki_gz}" DESTINATION "${_wiki_dl_dir}")
    # a plain .gz (not .tar.gz) extracts to a file named after the
    # archive minus its .gz suffix, inside DESTINATION
    if(NOT EXISTS "${_wiki_xml}")
      file(GLOB _wiki_extracted_candidates "${_wiki_dl_dir}/*.xml")
      if(_wiki_extracted_candidates)
        list(GET _wiki_extracted_candidates 0 _wiki_extracted_first)
        file(RENAME "${_wiki_extracted_first}" "${_wiki_xml}")
      endif()
    endif()
  endif()

  if(EXISTS "${_wiki_xml}")
    file(SIZE "${_wiki_xml}" _wiki_bytes)
    message(STATUS "pygixml benchmarks: real giant XML available, ${_wiki_bytes} bytes -> ${_wiki_xml}")
    set(PYGIXML_REAL_GIANT_XML "${_wiki_xml}")
  endif()
endif()
