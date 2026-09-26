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
# (`cmake --build build --target help` lists them all). One target
# reaches outside this directory on purpose: pygixml_benchmark_report
# (see report/CMakeLists.txt) additionally copies the result into
# ../docs/source/_static/ -- that one only works inside a full pygixml
# checkout, not a standalone copy of benchmarks/ elsewhere.
#
# To benchmark a local, not-yet-published patch instead of whatever is
# on GitHub, override this at configure time rather than editing it
# here, e.g.:
#   cmake -S . -B build -DPYGIXML_BENCH_GITHUB_URL=/path/to/local/checkout
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
