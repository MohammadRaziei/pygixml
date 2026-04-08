Quick Start
===========

This guide walks you through the core features of pygixml: parsing, navigating,
querying, and creating XML documents.

Parsing XML
-----------

**From a string**

.. code-block:: python

   import pygixml

   xml = '''
   <library>
       <book id="1" category="fiction">
           <title>The Great Gatsby</title>
           <author>F. Scott Fitzgerald</author>
           <year>1925</year>
       </book>
       <book id="2" category="fiction">
           <title>1984</title>
           <author>George Orwell</author>
           <year>1949</year>
       </book>
   </library>
   '''

   doc = pygixml.parse_string(xml)

**From a file**

.. code-block:: python

   doc = pygixml.parse_file("data.xml")

Parse Flags
-----------

All parse functions accept a ``ParseFlags`` enum to control how pugixml
processes the input.  By default pygixml uses ``ParseFlags.DEFAULT`` which
gives full XML compliance.  Use ``ParseFlags.MINIMAL`` for maximum speed when
you only need the structure.

.. code-block:: python

   import pygixml

   # Fastest parse — skip escapes, EOL normalization, whitespace handling
   doc = pygixml.parse_string(xml, pygixml.ParseFlags.MINIMAL)

   # Combine specific flags with bitwise OR
   flags = pygixml.ParseFlags.COMMENTS | pygixml.ParseFlags.CDATA
   doc = pygixml.parse_string(xml, flags)

Available flags:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Flag
     - What it enables
   * - ``ParseFlags.MINIMAL``
     - No optional processing — fastest parse
   * - ``ParseFlags.COMMENTS``
     - Parse ``<!--comment-->`` nodes
   * - ``ParseFlags.CDATA``
     - Parse ``<![CDATA[...]]>`` sections
   * - ``ParseFlags.PI``
     - Parse processing instructions ``<?...?>``
   * - ``ParseFlags.ESCAPES``
     - Process ``&amp;``, ``&lt;``, ``&quot;``, etc.
   * - ``ParseFlags.EOL``
     - Normalize line endings to ``\n``
   * - ``ParseFlags.WS_PCDATA``
     - Convert whitespace in PCDATA to spaces
   * - ``ParseFlags.WS_PCDATA_SINGLE``
     - Collapse multiple whitespace to one space
   * - ``ParseFlags.WCONV_ATTRIBUTE``
     - Convert attribute whitespace
   * - ``ParseFlags.WNORM_ATTRIBUTE``
     - Normalize attribute whitespace
   * - ``ParseFlags.DECLARATION``
     - Parse ``<?xml ...?>`` declaration
   * - ``ParseFlags.DOCTYPE``
     - Parse ``<!DOCTYPE ...>`` node
   * - ``ParseFlags.TRIM_PCDATA``
     - Trim leading/trailing PCDATA whitespace
   * - ``ParseFlags.FRAGMENT``
     - Parse XML fragments (no root element required)
   * - ``ParseFlags.EMBED_PCDATA``
     - Parse embedded PCDATA as markup
   * - ``ParseFlags.MERGE_PCDATA``
     - Merge adjacent PCDATA nodes
   * - ``ParseFlags.DEFAULT``
     - Default — all standard processing enabled
   * - ``ParseFlags.FULL``
     - Everything — same as default

The same flags apply to :py:meth:`~pygixml.XMLDocument.load_string` and
:py:meth:`~pygixml.XMLDocument.load_file`.

Navigating the Tree
-------------------

Every parsed document starts at its root element. From there you walk the
tree with :py:meth:`~pygixml.XMLNode.first_child`,
:py:meth:`~pygixml.XMLNode.child`, and sibling properties.

.. code-block:: python

   # Access the root element directly
   root = doc.root
   print(root.name)               # → library

   # Get the first <book> child by name
   book = root.child("book")
   print(book.name)               # → book

   # Read an attribute
   book_id = book.attribute("id")
   print(book_id.value)           # → 1

   # Read text content
   title = book.child("title")
   print(title.text())            # → The Great Gatsby

Iterating
---------

**Depth-first traversal** — the document itself is iterable:

.. code-block:: python

   for node in doc:
       print(f"{node.type:12s} {node.name}")

**Walking children with siblings:**

.. code-block:: python

   child = root.first_child()
   while child:
       print(child.name)
       child = child.next_sibling

XPath Queries
-------------

Select multiple nodes or a single node with standard XPath 1.0 expressions:

.. code-block:: python

   # All <book> elements
   books = root.select_nodes("book")
   print(f"Found {len(books)} books")

   # Fiction books via attribute filter
   fiction = root.select_nodes("book[@category='fiction']")
   for b in fiction:
       print(b.node.child("title").text())

   # Single match
   match = root.select_node("book[@id='2']")
   if match:
       print(match.node.child("title").text())   # → 1984

**Pre-compiled queries** — reuse an :py:class:`~pygixml.XPathQuery` for
repeated evaluation:

.. code-block:: python

   query = pygixml.XPathQuery("book[year > 1950]")

   # Node set
   results = query.evaluate_node_set(root)

   # Scalar results
   avg_price = pygixml.XPathQuery(
       "sum(book/price) div count(book)"
   ).evaluate_number(root)

   first_title = pygixml.XPathQuery(
       "book[1]/title"
   ).evaluate_string(root)

Creating XML from Scratch
-------------------------

.. code-block:: python

   doc = pygixml.XMLDocument()
   root = doc.append_child("catalog")

   product = root.append_child("product")
   name = product.append_child("name")
   name.set_value("Laptop")

   price = product.append_child("price")
   price.set_value("999.99")

   doc.save_file("catalog.xml")

.. tip::
   Attribute *creation* is not yet exposed in the Python API.  When you need
   attributes, either parse a string or write the raw XML and load it:

   .. code-block:: python

      doc = pygixml.parse_string(
          '<catalog><product id="1" name="Laptop"/></catalog>'
      )

Modifying XML
-------------

.. code-block:: python

   doc = pygixml.parse_string('<item><name>Old</name></item>')
   root = doc.root

   # Change element text content
   root.child("name").set_value("New")

   # Rename an element
   root.child("name").name = "title"

   # Add a new child
   root.append_child("price").set_value("29.99")

Error Handling
--------------

All parsing errors raise :py:class:`~pygixml.PygiXMLError`:

.. code-block:: python

   try:
       doc = pygixml.parse_string("not xml")
   except pygixml.PygiXMLError as e:
       print(f"Parse failed: {e}")

Next Steps
----------

- Dive into :doc:`XPath capabilities <xpath>`
- Browse the full :doc:`API reference <api>`
- See :doc:`practical examples <examples>`
- Learn about :doc:`performance <performance>`
