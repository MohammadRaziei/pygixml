find_package(Cython MODULE REQUIRED VERSION 3.0)
include(UseCython)

if(DEFINED SKBUILD)
    # Transpile Cython to C++
    cython_transpile(${CMAKE_CURRENT_SOURCE_DIR}/pygixml_cy.pyx 
                    LANGUAGE CXX 
                    OUTPUT_VARIABLE pygixml_cxx_file)

    # Create the Python extension module
    python_add_library(pygixml_cy MODULE "${pygixml_cxx_file}" WITH_SOABI)

    # Include directories
    target_include_directories(pygixml_cy PRIVATE 
        ${CMAKE_CURRENT_SOURCE_DIR}/third_party/pugixml/src
    )

    target_compile_definitions(pygixml_cy PRIVATE PUGIXML_HEADER_ONLY)
    # Install the module
    install(TARGETS pygixml_cy
        DESTINATION ${MODULE_NAME}
    )

    install(DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/pygixml/
        DESTINATION ${MODULE_NAME}
        FILES_MATCHING PATTERN "*.py"
    )

    return()
endif()


# Include the ExternalProject module
set(PYTHON_INSTALL_DIR ${CMAKE_BINARY_DIR}/python/install)

include(ExternalProject)
ExternalProject_Add(build_python
    SOURCE_DIR ${CMAKE_SOURCE_DIR}
    BINARY_DIR ${CMAKE_BINARY_DIR}/python/build
    INSTALL_DIR ${PYTHON_INSTALL_DIR}
    
    # Pass configuration arguments to CMake
    CMAKE_ARGS  
        --no-warn-unused-cli
        -DSKBUILD=2
        -DCMAKE_INSTALL_PREFIX=${CMAKE_BINARY_DIR}/python/install
    
    # Ensure the build step runs the install command
    INSTALL_COMMAND ${CMAKE_COMMAND} --build . --target install --parallel 8
    
    # Build this target always, useful for testing workflows
    BUILD_ALWAYS 1
)
