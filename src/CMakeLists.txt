find_package(Cython MODULE REQUIRED VERSION 3.0)
include(UseCython)

if(DEFINED SKBUILD)
    # Add pugixml
    add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/third_party/pugixml)

    # Transpile Cython to C++
    cython_transpile(${CMAKE_CURRENT_SOURCE_DIR}/${MODULE_NAME}.pyx 
                    LANGUAGE CXX 
                    OUTPUT_VARIABLE pygixml_cxx_file)

    # Create the Python extension module
    python_add_library(${MODULE_NAME} MODULE "${pygixml_cxx_file}" WITH_SOABI)

    # Link pugixml to our module
    target_link_libraries(${MODULE_NAME} PRIVATE pugixml)

    # Include directories
    target_include_directories(${MODULE_NAME} PRIVATE 
        ${CMAKE_CURRENT_SOURCE_DIR}/third_party/pugixml/src
    )

    # Install the module
    install(TARGETS ${MODULE_NAME}
        DESTINATION ${MODULE_NAME}
    )

    install(DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/pygixml/
        DESTINATION ${MODULE_NAME}
        FILES_MATCHING PATTERN "*.py"
    )

    return()
endif()


# Include the ExternalProject module
include(ExternalProject)


set(PYTHON_INSTALL_DIR ${CMAKE_BINARY_DIR}/python/install)
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
