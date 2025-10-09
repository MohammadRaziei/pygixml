Installation
============

pygixml can be installed using pip from the GitHub repository.

Prerequisites
-------------

- Python 3.7 or higher
- Cython 3.0+
- CMake 3.15+
- C++ compiler (GCC, Clang, or MSVC)

Installation Methods
--------------------

From PyPI (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pip install pygixml

From GitHub
~~~~~~~~~~~

.. code-block:: bash

   pip install git+https://github.com/MohammadRaziei/pygixml.git

Verification
------------

To verify the installation, run:

.. code-block:: python

   import pygixml
   print(f"pygixml version: {pygixml.__version__}")

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

1. **CMake not found**: Install CMake from https://cmake.org/download/
2. **C++ compiler not found**: Install build tools for your platform
3. **Cython not found**: Install Cython with ``pip install cython``

Platform-Specific Instructions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Windows**
^^^^^^^^^^^^

Install Visual Studio Build Tools or use the Visual Studio installer.

**Linux**
^^^^^^^^^

Install build essentials:

.. code-block:: bash

   # Ubuntu/Debian
   sudo apt-get install build-essential cmake

   # CentOS/RHEL
   sudo yum groupinstall "Development Tools"
   sudo yum install cmake

**macOS**
^^^^^^^^^

Install Xcode command line tools:

.. code-block:: bash

   xcode-select --install

Dependencies
------------

- **pugixml**: Included as submodule, automatically built
- **Cython**: Required for building the wrapper
- **scikit-build-core**: Used for the build system
- **CMake**: Required for building pugixml and the wrapper
