cmake_minimum_required(VERSION 3.15)
project(${SKBUILD_PROJECT_NAME})
cmake_policy(SET CMP0144 NEW)

# Set Python module name (should match the .pyx filename)
string(REPLACE "-" "_" MODULE_NAME ${SKBUILD_PROJECT_NAME})

# Set C++ standard
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

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

# Set build type to Release for better performance
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

list(APPEND CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}/cmake")

# Find Python and Cython
find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)
find_package(Cython MODULE REQUIRED VERSION 3.0)
include(UseCython)

# Add pugixml
add_subdirectory(src/third_party/pugixml)

# Set Python module output directory
set(PYTHON_MODULE_OUTPUT_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/pygixml)

# Transpile Cython to C++
cython_transpile(src/${MODULE_NAME}/${MODULE_NAME}.pyx LANGUAGE CXX OUTPUT_VARIABLE pygixml_cpp_file)

# Create the Python extension module
python_add_library(${MODULE_NAME} MODULE "${pygixml_cpp_file}" WITH_SOABI)

# Link pugixml to our module
target_link_libraries(${MODULE_NAME} PRIVATE pugixml)

# Include directories
target_include_directories(${MODULE_NAME} PRIVATE 
    ${CMAKE_CURRENT_SOURCE_DIR}/src/third_party/pugixml/src
)

# Install the module
install(TARGETS ${MODULE_NAME}
    DESTINATION ${SKBUILD_PROJECT_NAME}
)
