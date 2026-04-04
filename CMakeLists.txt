cmake_minimum_required(VERSION 3.15)
cmake_policy(SET CMP0116 NEW)


# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)


list(APPEND CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}/cmake")
include(PyProject)

project(${PyProject_NAME} VERSION ${PyProject_VERSION})
message(STATUS "Project: ${PROJECT_NAME}@v${PROJECT_VERSION}")
# Set Python module name (should match the .pyx filename)
string(REPLACE "-" "_" MODULE_NAME ${PROJECT_NAME})
include(Startup)
include(Optimize)


# Find Python and Cython
find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)

add_subdirectory(${PROJECT_SOURCE_DIR}/src)
if(DEFINED SKBUILD)
    return() 
endif()



