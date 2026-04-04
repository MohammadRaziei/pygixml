# GSPOptimize.cmake
#
# Aggressive optimization flags for maximum runtime performance.
# Works with GCC, Clang, and MSVC.
#
# Usage:
#   include(GSPOptimize)
#   set_default_optimizations()
#   enable_optimizations(<target>)


# Set build type to Release for better performance
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

# Optimize for performance
if(CMAKE_BUILD_TYPE STREQUAL "Release")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3 -DNDEBUG")
else()
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O2")
endif()

# Additional optimization flags for GCC/Clang
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    set(SAFE_FLAGS "-fomit-frame-pointer -fno-stack-protector")
    if(NOT APPLE AND NOT DEFINED ENV{CI})
        set(SAFE_FLAGS "${SAFE_FLAGS} -march=native -mtune=native")
    endif()

    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${SAFE_FLAGS}")
endif()


option(ARCH_NATIVE "Enable -march=native (tune to local CPU)" ON)
option(FAST_MATH  "Enable fast-math (unsafe for strict IEEE compliance)" ON)

# --- Helper: enable IPO/LTO if available ---
function(__enable_ipo target)
    include(CheckIPOSupported)
    check_ipo_supported(RESULT _ipo_ok OUTPUT _ipo_msg)
    if(_ipo_ok)
        set_property(TARGET ${target} PROPERTY INTERPROCEDURAL_OPTIMIZATION TRUE)
    else()
        message(STATUS "IPO not supported for ${target}: ${_ipo_msg}")
    endif()
endfunction()

# --- Apply optimization flags per target ---
function(enable_optimizations target)
    target_compile_definitions(${target} PRIVATE
            $<$<CONFIG:Release,RelWithDebInfo,MinSizeRel>:NDEBUG>
    )

    if(MSVC)
        target_compile_options(${target} PRIVATE
                $<$<CONFIG:Release,RelWithDebInfo,MinSizeRel>:/O2 /GL /Oi /Ot /Ob3 /DNDEBUG>
                $<$<BOOL:${FAST_MATH}>:/fp:fast>
        )
        target_link_options(${target} PRIVATE
                $<$<CONFIG:Release,RelWithDebInfo,MinSizeRel>:/LTCG>
        )
    else()
        target_compile_options(${target} PRIVATE
                $<$<CONFIG:Release,RelWithDebInfo,MinSizeRel>:-O3 -fno-plt -funroll-loops -finline-functions -fstrict-aliasing>
                $<$<BOOL:${ARCH_NATIVE}>:-march=native>
                $<$<BOOL:${FAST_MATH}>:-ffast-math>
        )
        target_link_options(${target} PRIVATE
                $<$<CONFIG:Release,RelWithDebInfo,MinSizeRel>:-flto>
        )
    endif()

    _enable_ipo(${target})
endfunction()

# --- Apply global defaults ---
function(set_default_optimizations)
    set(CMAKE_POSITION_INDEPENDENT_CODE ON)

    if(NOT CMAKE_CONFIGURATION_TYPES AND NOT CMAKE_BUILD_TYPE)
        set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
    endif()

    include(CheckIPOSupported)
    check_ipo_supported(RESULT _ipo_ok OUTPUT _ipo_msg)
    if(_ipo_ok)
        set(CMAKE_INTERPROCEDURAL_OPTIMIZATION TRUE)
    endif()

    if(MSVC AND NOT DEFINED CMAKE_MSVC_RUNTIME_LIBRARY)
        set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL")
    endif()
endfunction()
