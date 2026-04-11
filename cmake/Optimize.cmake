# Optimize.cmake
#
# Cross-platform optimization flags for maximum runtime performance.
# Supports GCC, Clang, and MSVC on all operating systems.
#
# Usage:
#   include(Optimize)

# Default to Release if no build type was specified
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

# ── Compiler-specific optimization flags ──────────────────────────

# GCC / Clang
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    # Base Release optimizations
    set(OPT_FLAGS_RELEASE
        -O3
        -DNDEBUG
        -fomit-frame-pointer
        -fno-stack-protector
    )

    # -march=native gives the best performance but:
    #   • doesn't work on Apple Silicon cross-builds
    #   • breaks reproducible builds in CI
    # Skip it in those environments
    if(NOT APPLE AND NOT DEFINED ENV{CI} AND NOT DEFINED ENV{GITHUB_ACTIONS})
        list(APPEND OPT_FLAGS_RELEASE -march=native -mtune=native)
    endif()

# MSVC (Windows)
elseif(MSVC)
    set(OPT_FLAGS_RELEASE
        /O2          # Maximum optimization for speed
        /DNDEBUG     # Disable assert()
        /GL          # Whole-program optimization
    )

# Unknown compiler — use conservative defaults
else()
    message(STATUS "Optimize: unknown compiler '${CMAKE_CXX_COMPILER_ID}', using safe defaults")
    set(OPT_FLAGS_RELEASE -O2 -DNDEBUG)
endif()

# ── Apply flags to Release builds ─────────────────────────────────

list(JOIN OPT_FLAGS_RELEASE " " OPT_FLAGS_RELEASE_STR)

if(CMAKE_BUILD_TYPE STREQUAL "Release")
    string(APPEND CMAKE_CXX_FLAGS " ${OPT_FLAGS_RELEASE_STR}")
    string(APPEND CMAKE_C_FLAGS   " ${OPT_FLAGS_RELEASE_STR}")
else()
    # Non-Release builds still get basic optimization
    if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
        string(APPEND CMAKE_CXX_FLAGS " -O2")
        string(APPEND CMAKE_C_FLAGS   " -O2")
    elseif(MSVC)
        string(APPEND CMAKE_CXX_FLAGS " /O2")
        string(APPEND CMAKE_C_FLAGS   " /O2")
    endif()
endif()
