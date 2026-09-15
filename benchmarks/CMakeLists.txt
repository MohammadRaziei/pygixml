cmake_minimum_required(VERSION 3.18)
project(PygixmlBenchmarks LANGUAGES NONE)

# This whole directory is self-contained and independent of the parent
# pygixml source tree: it installs pygixml itself from GitHub
# (pip install git+https://...), not from ../src, so it can be copied
# out and run on its own -- same convention as
# https://github.com/MohammadRaziei/ctoon/tree/main/benchmarks.
#
#   cmake -S . -B build
#   cmake --build build --target pygixml_benchmark
#
# See README.md in this directory for the full rundown, and every
# individual target below for what it does on its own
# (`cmake --build build --target help` lists them all).

set(PYGIXML_BENCH_GITHUB_URL
    "git+https://github.com/MohammadRaziei/pygixml.git"
    CACHE STRING "Where to install pygixml itself from (a fresh git checkout, not the local source tree)")

set(PYGIXML_BENCH_RESULTS_DIR "${CMAKE_CURRENT_SOURCE_DIR}/results"
    CACHE PATH "Where the final standalone report.html is written -- the one artifact meant to be committed")

find_package(Python3 COMPONENTS Interpreter REQUIRED)

include("${CMAKE_CURRENT_SOURCE_DIR}/cmake/FetchRealCorpus.cmake")

add_subdirectory(python)
add_subdirectory(report)

add_custom_target(pygixml_benchmark
  COMMENT "pygixml_benchmark: running the full benchmark suite and building the report"
)
add_dependencies(pygixml_benchmark pygixml_bench_report)
