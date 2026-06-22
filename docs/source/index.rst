.. pygixml documentation master file

Welcome to pygixml
==================

**pygixml** (*Python Giant XML*) is a high-performance Cython framework
bridging two specialized C++ engines: `pugixml <https://pugixml.org/>`_
for its in-memory DOM parser (full XPath 1.0, :doc:`objectify`,
:doc:`dictify`), and an inlined `yxml <https://dev.yorhel.nl/yxml>`_
push parser for true constant-memory :doc:`streaming <streaming>`. The
result is a faster, constant-memory alternative to
`lxml <https://lxml.de/>`_ and
`xmltodict <https://github.com/martinblech/xmltodict>`_ — everything
they do, plus a streaming layer neither of them has, which is what
makes pygixml the package to reach for once a dataset gets *massive*.

New to XML?  Start with :doc:`xml_basics` for a primer on the format, its
structure, and real-world applications.

.. note::
   Enjoy pygixml?  Star the project on GitHub to support the development:
   https://github.com/MohammadRaziei/pygixml

Why pygixml?
------------

**Speed** — pugixml is one of the fastest XML parsers available.  pygixml
brings that speed directly to Python:

+-------------------------+------------+------------------------+
| Library                 | Avg Time   | Speedup vs ElementTree |
+=========================+============+========================+
| **pygixml**             | 0.0009 s   | **9.2× faster**        |
+-------------------------+------------+------------------------+
| **lxml**                | 0.0041 s   | 2.0× faster            |
+-------------------------+------------+------------------------+
| **ElementTree**         | 0.0083 s   | 1.0× (baseline)        |
+-------------------------+------------+------------------------+

(Benchmark: parsing a document with 5 000 elements.  See
:doc:`performance` for the full comparison.)

Features
--------

* **Blazing-fast parsing** — up to 14× faster than ElementTree
* **Full XPath 1.0** — complete query engine with all standard functions
* **Memory efficient** — zero-copy C++ memory management via pugixml
* **Pythonic API** — intuitive methods and properties, not a direct C++ mirror
* **objectify** — lxml.objectify-style dotted navigation (``root.user.name``)
* **dictify** — xmltodict-compatible XML → dict conversion
* **jsonify** — direct XML → JSON, in memory or streamed straight to disk
  in constant memory (see :doc:`jsonify`)
* **Streaming** — constant-memory, ``ElementTree``-style incremental
  parsing for documents too big to load whole (see :doc:`streaming`)
* **Cross-platform** — Windows, Linux, macOS
* **Text extraction** — recursive text gathering with configurable joins
* **XML serialization** — output with custom indentation
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

   # Low-level API
   root = doc.root
   book = root.child("book")
   print(book.attribute("id").value)        # → 1
   print(book.child("title").text())        # → The Great Gatsby

   # XPath queries
   titles = root.select_nodes("book/title")
   for t in titles:
       print(t.node.text())                      # → The Great Gatsby

   # Create and save
   doc = pygixml.XMLDocument()
   root = doc.append_child("catalog")
   root.append_child("item").set_value("Hello")
   doc.save_file("output.xml")

   # objectify — dotted navigation
   from pygixml import objectify
   root = objectify.from_string(xml)
   print(root.book.title())                 # → 'The Great Gatsby'
   print(root.book.id)                      # → 1  (int)

   # dictify — XML to dict
   from pygixml import dictify
   d = dictify.parse(xml)
   print(d['library']['book']['@id']) 

   # jsonify — direct XML to JSON
   from pygixml import jsonify
   print(jsonify.dumps(xml))

   # streaming — constant memory, for files too big to load whole
   for book in pygixml.iterfind("library.xml", "book"):
       print(book.get("id"), book.findtext("title"))
       book.clear()

Core Classes
------------

See the :doc:`api` for the complete reference.

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Class / Module
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
   * - :doc:`objectify <objectify>`
     - lxml.objectify-style dotted navigation
   * - :doc:`dictify <dictify>`
     - xmltodict-compatible XML → dict conversion
   * - :doc:`jsonify <jsonify>`
     - Direct XML → JSON, in memory or streamed to disk in constant memory
   * - :doc:`streaming <streaming>`
     - ``iterparse``/``iterfind`` — constant-memory parsing for big XML

Pythonic Extensions
-------------------

pugixml gives pygixml its speed, but the **API you actually use** goes well
beyond what the C++ library provides:

* :attr:`~pygixml.XMLNode.text` — recursive text extraction with configurable
  joins. One call to gather all text content from an element
  and its descendants.
* :meth:`~pygixml.XMLNode.children` — iterate direct child elements only (or
  all descendants with ``recursive=True``), no manual sibling walking.
* :attr:`~pygixml.XMLNode.xpath` — generate an absolute XPath to any node
  using a custom O(depth) algorithm.  Not available in pugixml natively.
* :attr:`~pygixml.XMLNode.xml` — serialize a node to formatted XML in one
  property.
* :attr:`~pygixml.XMLNode.mem_id` — a unique numeric identifier for each
  node, ideal for caching and dictionary-based lookups.
* :meth:`~pygixml.XMLNode.to_string` — customizable XML serialization with
  string or integer indentation.
* :doc:`objectify <objectify>` — navigate XML like a Python object tree.
* :doc:`dictify <dictify>` — convert XML to dict / JSON with one call.
* :doc:`jsonify <jsonify>` — convert XML straight to JSON, in memory or
  streamed file-to-file in constant memory.
* :doc:`streaming <streaming>` — ``iterparse``/``iterfind`` for documents
  too large to ever load as a full DOM tree.

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
   objectify
   dictify
   jsonify
   streaming
   xpath
   advanced
   examples
   performance
   api


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
