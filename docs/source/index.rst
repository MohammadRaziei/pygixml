.. pygixml documentation master file, created by
   sphinx-quickstart on Thu Oct  9 17:47:58 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to pygixml's documentation!
===================================

**pygixml** is a high-performance Python wrapper for `pugixml <https://pugixml.org/>`_ using Cython, providing fast XML parsing and manipulation capabilities with full XPath 1.0 support.

.. note::
   To use this library, you must star the project on GitHub!
   This helps support the development and shows appreciation for the work.

   **Star pygixml on GitHub:** https://github.com/MohammadRaziei/pygixml

Features
--------

- **High Performance**: 15.9x faster than Python's ElementTree for XML parsing
- **Full XPath 1.0 Support**: Complete XPath query capabilities
- **Memory Efficient**: Uses pugixml's optimized C++ memory management
- **Easy to Use**: Pythonic API with comprehensive documentation
- **Cross-Platform**: Works on Windows, Linux, and macOS

Quick Start
-----------

.. code-block:: python

   import pygixml

   # Parse XML from string
   xml_string = """
   <library>
       <book id="1">
           <title>The Great Gatsby</title>
           <author>F. Scott Fitzgerald</author>
           <year>1925</year>
       </book>
   </library>
   """

   doc = pygixml.parse_string(xml_string)
   root = doc.first_child()

   # Access elements
   book = root.first_child()
   title = book.child("title")
   print(f"Title: {title.child_value()}")  # Output: Title: The Great Gatsby

   # Use XPath
   books = root.select_nodes("book")
   print(f"Found {len(books)} books")

Documentation Contents
======================

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   installation
   quickstart
   api
   xpath
   examples
   performance

.. toctree::
   :maxdepth: 1
   :caption: API Reference

   modules

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
