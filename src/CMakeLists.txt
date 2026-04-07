if(DEFINED SKBUILD)
    # Transpile Cython to C++
    find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)

    find_package(Cython MODULE REQUIRED VERSION 3.0)
    include(UseCython)

    cython_transpile(${CMAKE_CURRENT_SOURCE_DIR}/pygixml_cy.pyx 
                    LANGUAGE CXX 
                    OUTPUT_VARIABLE pygixml_cxx_file)

    # Create the Python extension module
    python_add_library(pygixml_cy MODULE "${pygixml_cxx_file}" WITH_SOABI)

    # Include directories
    target_include_directories(pygixml_cy PRIVATE 
        ${CMAKE_CURRENT_SOURCE_DIR}/third_party/pugixml/src
    )

    target_compile_definitions(pygixml_cy PRIVATE 
        PUGIXML_HEADER_ONLY 
        VERSION_INFO=${PROJECT_VERSION}
    )

    IF (NOT WIN32)
        # Generate .pyi stub file using stubgen after build
        add_custom_command(TARGET pygixml_cy POST_BUILD
            COMMAND ${Python3_EXECUTABLE} -m pybind11_stubgen pygixml_cy -o ${CMAKE_CURRENT_BINARY_DIR} 
            COMMAND ${Python3_EXECUTABLE} -c 
                    "import sys; f=sys.argv[1]; lines=[l for l in open(f, encoding='utf-8') if not l.startswith('__test__')]; open(f, 'w', encoding='utf-8').writelines(lines)"
                    "${CMAKE_CURRENT_BINARY_DIR}/pygixml_cy.pyi"
            BYPRODUCTS ${CMAKE_CURRENT_BINARY_DIR}/pygixml_cy.pyi
            COMMENT "Generating .pyi stubs with stubgen..."
            WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
            VERBATIM
        )
        install (FILES ${CMAKE_CURRENT_BINARY_DIR}/pygixml_cy.pyi
            DESTINATION ${MODULE_NAME}
        )
    endif()


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

include(ExternalProject)
ExternalProject_Add(build_python
    SOURCE_DIR ${CMAKE_SOURCE_DIR}
    BINARY_DIR ${CMAKE_BINARY_DIR}/python/build
    INSTALL_DIR ${PYTHON_INSTALL_DIR}
    
    # Pass configuration arguments to CMake
    CMAKE_ARGS --no-warn-unused-cli -DSKBUILD=2 -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=${PYTHON_INSTALL_DIR}
    
    # Ensure the build step runs the install command
    INSTALL_COMMAND ${CMAKE_COMMAND} --build . --target install --parallel 8
    
    # Build this target always, useful for testing workflows
    BUILD_ALWAYS 1
)
