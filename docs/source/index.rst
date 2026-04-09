.. pygixml documentation master file, created by
   sphinx-quickstart on Thu Oct  9 17:47:58 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to pygixml
==================

**pygixml** is a high-performance XML parser for Python built on Cython and
`pugixml <https://pugixml.org/>`_.  It delivers fast parsing, full XPath 1.0
support, and a clean Pythonic API for reading, writing, and transforming XML.

New to XML?  Start with :doc:`xml_basics` for a primer on the format, its
structure, and real-world applications.

.. note::
   Enjoy pygixml?  Star the project on GitHub to support the development:
   https://github.com/MohammadRaziei/pygixml

Why pygixml?
------------

**Speed** — pugixml is one of the fastest XML parsers available.  pygixml
brings that speed directly to Python:

+-------------------------+----------------+------------------------+
| Library                 | Parsing Time   | Speedup vs ElementTree |
+=========================+================+========================+
| **pygixml**             | 0.0009 s       | **8.6× faster**        |
+-------------------------+----------------+------------------------+
| **lxml**                | 0.0041 s       | 1.9× faster            |
+-------------------------+----------------+------------------------+
| **ElementTree**         | 0.0076 s       | 1.0× (baseline)        |
+-------------------------+----------------+------------------------+

*(Benchmark: parsing a document with 5 000 elements.  See
:doc:`performance` for the full comparison.)*

Features
--------

* **Blazing-fast parsing** — up to 15.9× faster than ElementTree
* **Full XPath 1.0** — complete query engine with all standard functions
* **Memory efficient** — zero-copy C++ memory management via pugixml
* **Pythonic API** — intuitive methods and properties, not a direct C++ mirror
* **Cross-platform** — Windows, Linux, macOS
* **Text extraction** — recursive text gathering with configurable joins
* **XML serialization** — output with custom indentation (spaces or integer)
* **Node iteration** — depth-first traversal of the entire document
* **Node identity** — memory-based ID for debugging and comparison

Quick Example
-------------

.. code-block:: python

   import pygixml

   doc = pygixml.parse_string("""
   <library>
       <book id="1">
           <title>The Great Gatsby</title>
           <author>F. Scott Fitzgerald</author>
       </book>
   </library>
   """)

   # Access elements and attributes
   root = doc.root
   book = root.child("book")
   print(book.name)                              # → book
   print(book.attribute("id").value)             # → 1
   print(book.child("title").text())             # → The Great Gatsby

   # XPath queries
   titles = root.select_nodes("book/title")
   for t in titles:
       print(t.node.text())                      # → The Great Gatsby

   # Create and save
   doc = pygixml.XMLDocument()
   root = doc.append_child("catalog")
   root.append_child("item").set_value("Hello")
   doc.save_file("output.xml")

Core Classes
------------

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Class
     - Description
   * - :py:class:`~pygixml.XMLDocument`
     - Document-level operations: load, save, append-child
   * - :py:class:`~pygixml.XMLNode`
     - Navigate, read, and modify individual nodes
   * - :py:class:`~pygixml.XMLAttribute`
     - Attribute name and value access
   * - :py:class:`~pygixml.XPathQuery`
     - Pre-compiled XPath queries for repeated evaluation
   * - :py:class:`~pygixml.XPathNode`
     - Single XPath result (wraps a node or attribute)
   * - :py:class:`~pygixml.XPathNodeSet`
     - Collection of XPath results

.. note::
   **Properties vs Methods** — pygixml uses properties for simple accessors
   and methods for operations that take arguments:

   *Properties (no parentheses):* ``node.name``, ``node.value``,
   ``node.type``, ``node.parent``, ``node.next_sibling``,
   ``node.previous_sibling``, ``node.xml``, ``node.xpath``,
   ``attr.name``, ``attr.value``, ``attr.next_attribute``, ``doc.root``

   *Methods (need parentheses):* ``node.child(name)``,
   ``node.first_child()``, ``node.append_child(name)``,
   ``node.child_value(name)``, ``node.set_value(v)``,
   ``node.first_attribute()``, ``node.attribute(name)``,
   ``node.select_nodes(query)``, ``node.select_node(query)``,
   ``node.text()``, ``node.to_string()``

XPath Support
-------------

pygixml exposes pugixml's full XPath 1.0 engine:

* **Axes:** ``child::``, ``attribute::``, ``descendant::``, ``ancestor::``
* **Predicates:** ``book[@id='1']``, ``book[year > 1950]``
* **Functions:** ``position()``, ``last()``, ``count()``, ``sum()``,
  ``string()``, ``number()``, ``concat()``, ``substring()``
* **Operators:** ``and``, ``or``, ``not()``, ``=``, ``!=``, ``<``, ``>``,
  ``+``, ``-``, ``*``, ``div``, ``mod``
* **Wildcards:** ``*``, ``@*``, ``node()``

See :doc:`xpath` for a detailed walkthrough.

Installation
------------

**From PyPI**

.. code-block:: bash

   pip install pygixml

**From source**

.. code-block:: bash

   pip install git+https://github.com/MohammadRaziei/pygixml.git


Documentation Contents
======================

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   installation
   xml_basics
   quickstart
   xpath
   advanced
   examples
   api
   performance


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
