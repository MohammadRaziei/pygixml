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
find_package(Python3 COMPONENTS Interpreter REQUIRED)

set(PYTHON_INSTALL_DIR ${CMAKE_BINARY_DIR}/python/install)
add_subdirectory(${PROJECT_SOURCE_DIR}/src)
if(DEFINED SKBUILD OR NOT TARGET build_python) 
    return() 
endif()


set(TEST_SOURCE_DIR ${PROJECT_SOURCE_DIR}/tests)

set(TEST_BINARY_DIR ${CMAKE_BINARY_DIR}/tests)
set(COVERAGE_BINARY_DIR ${CMAKE_BINARY_DIR}/coverage)


enable_testing()
set(CMAKE_CTEST_ARGUMENTS "--output-on-failure" "-V")
# Check for pytest
execute_process(
    COMMAND ${Python3_EXECUTABLE} -m pytest --version
    OUTPUT_QUIET
    ERROR_QUIET
    RESULT_VARIABLE PYTEST_CHECK_RESULT
)

if(NOT PYTEST_CHECK_RESULT EQUAL 0)
    message(WARNING "pytest is not installed. Python tests will be skipped.")
    message(WARNING "Please install it using: pip install pytest")
else()
    # Define the test executable target (conceptually)
    add_test(NAME python_tests 
                COMMAND ${Python3_EXECUTABLE} -m pytest ${CMAKE_CURRENT_SOURCE_DIR}
                WORKING_DIRECTORY ${PYTHON_INSTALL_DIR}
    )

    # In reality, we run pytest via the Python interpreter found above.
    add_custom_target(test_python
        COMMAND ${CMAKE_COMMAND} -E echo "-- Running python tests..."
        COMMAND ${Python3_EXECUTABLE} -m pytest ${CMAKE_CURRENT_SOURCE_DIR}
        WORKING_DIRECTORY ${PYTHON_INSTALL_DIR}
        USES_TERMINAL
    )

    # Ensure tests are run after the custom build is complete
    add_dependencies(test_python build_python)
    # add_dependencies(test test_python)
endif()

# Check for pytest-cov (coverage tool)
execute_process(
    COMMAND ${Python3_EXECUTABLE} -m coverage --version
    OUTPUT_QUIET
    ERROR_QUIET
    RESULT_VARIABLE COVERAGE_CHECK_RESULT
)

if(COVERAGE_CHECK_RESULT EQUAL 0)
    # Enable coverage for the python test target
    # We define a custom target to generate the coverage report.
    add_custom_target(coverage_python
        # Clean previous coverage data
        COMMAND ${CMAKE_COMMAND} -E remove_directory ${COVERAGE_BINARY_DIR}
        COMMAND ${CMAKE_COMMAND} -E make_directory ${COVERAGE_BINARY_DIR}/html
        
        # Run tests with coverage enabled
        # We run from the install directory so Python can find the installed package.
        COMMAND ${CMAKE_COMMAND} -E echo "-- Capturing coverage..."
        COMMAND ${Python3_EXECUTABLE} -m coverage run 
                --source=${PYTHON_INSTALL_DIR} 
                --omit="*/tests/*" 
                -m pytest ${CMAKE_CURRENT_SOURCE_DIR}
                
        # Generate lcov file
        COMMAND ${CMAKE_COMMAND} -E echo "-- Generating coverage.lcov file..."
        COMMAND ${Python3_EXECUTABLE} -m coverage lcov -o ${COVERAGE_BINARY_DIR}/coverage.lcov

        # COMMAND ${CMAKE_COMMAND} 
                # -DCOV_FILE=${COVERAGE_BINARY_DIR}/coverage.lcov
                # -DSOURCE_PATH=${PROJECT_SOURCE_DIR}/
                # -P ${PROJECT_SOURCE_DIR}/cmake/FixLCovPaths.cmake

        # Generate HTML report
        COMMAND ${CMAKE_COMMAND} -E echo "-- Generating HTML report..."
        COMMAND ${Python3_EXECUTABLE} -m coverage html -d ${COVERAGE_BINARY_DIR}/html

        # Summary
        COMMAND ${CMAKE_COMMAND} -E echo "-- HTML entry point created here: ${COVERAGE_BINARY_DIR}/html/index.html"
        COMMAND ${CMAKE_COMMAND} -E echo "-- Coverage summary:"
        COMMAND ${Python3_EXECUTABLE} -m coverage report
        
        # Changed working directory to the install directory
        WORKING_DIRECTORY ${PYTHON_INSTALL_DIR}
        USES_TERMINAL            
    )
            # Ensure coverage runs after the build is complete
    add_dependencies(coverage_python build_python)
    
    # Add this python coverage target to the main 'coverage' target
    # add_dependencies(coverage coverage_python)
else()
    message(WARNING "coverage module is not installed. Python coverage target will be skipped.")
    message(WARNING "Please install it using: pip install coverage")
endif()



# Create output directory for Sphinx documentation
file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/docs)

# Define a custom target for building Sphinx documentation
add_custom_target(sphinx_docs
    # Generate API RST from installed module (which includes .pyi stub)
    COMMAND ${Python3_EXECUTABLE} -m sphinx.ext.apidoc
            -o ${CMAKE_CURRENT_SOURCE_DIR}/docs/source/api
            ${CMAKE_CURRENT_BINARY_DIR}/python/install
            -f -M -e --no-toc

    # Build HTML docs with PYTHONPATH set
    COMMAND ${CMAKE_COMMAND} -E env
            PYTHONPATH=${CMAKE_CURRENT_BINARY_DIR}/python/install
            ${Python3_EXECUTABLE} -m sphinx -b html ${CMAKE_CURRENT_SOURCE_DIR}/docs/source ${CMAKE_CURRENT_BINARY_DIR}/docs
    COMMENT "Building documentation with Sphinx..."
    USES_TERMINAL
    DEPENDS build_python
)
