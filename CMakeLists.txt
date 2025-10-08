cmake_minimum_required(VERSION 3.15)
project(pygixml)

# Set C++ standard
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find Python and Cython
find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)
find_package(Cython REQUIRED)

# Add pugixml
add_subdirectory(src/third_party/pugixml)

# Set Python module output directory
set(PYTHON_MODULE_OUTPUT_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/pygixml)

# Create the Cython module
cython_add_module(pygixml src/pygixml/pygixml.pyx)

# Link pugixml to our module
target_link_libraries(pygixml PRIVATE pugixml)

# Include directories
target_include_directories(pygixml PRIVATE 
    ${CMAKE_CURRENT_SOURCE_DIR}/src/third_party/pugixml/src
)

# Python include directories
target_include_directories(pygixml PRIVATE ${Python_INCLUDE_DIRS})

# Set output properties
set_target_properties(pygixml PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY ${PYTHON_MODULE_OUTPUT_DIRECTORY}
    PREFIX ""
    SUFFIX "${Python_SOABI}${CMAKE_SHARED_LIBRARY_SUFFIX}"
)

# Install the module
install(TARGETS pygixml
    LIBRARY DESTINATION pygixml
)
