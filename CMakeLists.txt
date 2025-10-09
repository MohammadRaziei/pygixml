cmake_minimum_required(VERSION 3.15)
project(pygixml)

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
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -march=native -mtune=native -fomit-frame-pointer -fno-stack-protector")
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
cython_transpile(src/pygixml/pygixml.pyx LANGUAGE CXX OUTPUT_VARIABLE pygixml_cpp_file)

# Create the Python extension module
python_add_library(pygixml MODULE "${pygixml_cpp_file}" WITH_SOABI)

# Link pugixml to our module
target_link_libraries(pygixml PRIVATE pugixml)

# Include directories
target_include_directories(pygixml PRIVATE 
    ${CMAKE_CURRENT_SOURCE_DIR}/src/third_party/pugixml/src
)

# Install the module
install(TARGETS pygixml
    DESTINATION .
)
