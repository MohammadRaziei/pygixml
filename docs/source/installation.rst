Installation
============

For Users
---------

Just install from PyPI:

.. code-block:: bash

   pip install pygixml

That's it.  No build tools required — pre-compiled wheels are provided for
Windows, Linux, and macOS.

Verify the installation:

.. code-block:: python

   import pygixml
   print(f"pygixml version: {pygixml.__version__}")

For Developers
--------------

To contribute to pygixml or build from source, you need a C++ compiler,
CMake, and Cython.

1. **Clone the repository**

   .. code-block:: bash

      git clone https://github.com/MohammadRaziei/pygixml.git
      cd pygixml
      git submodule update --init --recursive

2. **Install dev dependencies**

   .. code-block:: bash

      pip install -r requirements-dev.txt

   This pulls in Cython, scikit-build-core, pytest, Sphinx, and the
   documentation toolchain.

3. **Configure and build**

   .. code-block:: bash

      cmake -S . -B build
      cmake --build build

   This compiles the Cython extension and installs it into
   ``build/python/install/``.

Available CMake Targets
~~~~~~~~~~~~~~~~~~~~~~~

Run ``cmake --build build --target help`` to see all available targets:

.. list-table::
   :header-rows: 1

   * - Target
     - Description
   * - ``build_python``
     - Build the pygixml Cython extension
   * - ``test_python``
     - Run the pytest test suite
   * - ``coverage_python``
     - Run tests with code coverage
   * - ``sphinx_docs``
     - Build the Sphinx documentation
   * - ``run_benchmarks``
     - Run the parsing benchmark suite
   * - ``run_full_benchmarks``
     - Run the full benchmark (parsing + memory + package size)
   * - ``gen_benchmark_charts``
     - Run benchmarks and generate chart visualizations

Examples:

.. code-block:: bash

   # Build
   cmake --build build

   # Run tests
   cmake --build build --target test_python

   # Build documentation
   cmake --build build --target sphinx_docs

   # Run benchmarks
   cmake --build build --target run_full_benchmarks

Platform Prerequisites
----------------------

**Ubuntu / Debian**

.. code-block:: bash

   sudo apt-get install build-essential cmake python3-dev

**CentOS / RHEL**

.. code-block:: bash

   sudo yum groupinstall "Development Tools"
   sudo yum install cmake python3-devel

**macOS**

.. code-block:: bash

   xcode-select --install
   brew install cmake

**Windows**

Install `Visual Studio Build Tools
<https://visualstudio.microsoft.com/downloads/>`_ with the "Desktop
development with C++" workload, or install CMake from
https://cmake.org/download/.
