DOM Parser
==========

pygixml's core is a thin Cython wrapper around `pugixml <https://pugixml.org/>`_'s
in-memory DOM tree: parse a document once, then navigate, query, and modify it
through :py:class:`~pygixml.XMLDocument`, :py:class:`~pygixml.XMLNode`, and
:py:class:`~pygixml.XMLAttribute`. Everything on this page assumes the whole
document fits in memory; for files too large to load at once, see
:doc:`/core/stream-parser` instead.

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

.. tip::
   Use :py:class:`~pygixml.ParseFlags` to control parsing speed vs strictness.
   ``ParseFlags.MINIMAL`` skips escape processing and whitespace handling for
   maximum throughput. See :ref:`Parse Flags <parse-flags>` for details.

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

**Depth-first traversal**: the document itself is iterable:

.. code-block:: python

   for node in doc:
       print(f"{node.type:12s} {node.name}")

**Walking children with siblings:**

.. code-block:: python

   child = root.first_child()
   while child:
       print(child.name)
       child = child.next_sibling

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

XPath Support
-------------

pygixml exposes pugixml's full XPath 1.0 engine.  Queries execute in C++: only the results you access cross the Python boundary.

Selection Methods
~~~~~~~~~~~~~~~~~

Two methods on :py:class:`~pygixml.XMLNode`:

.. list-table::
   :header-rows: 1

   * - Method
     - Returns
     - Empty match
   * - ``select_nodes(expr)``
     - :py:class:`~pygixml.XPathNodeSet` (iterable, ``len()``)
     - empty set
   * - ``select_node(expr)``
     - :py:class:`~pygixml.XPathNode` or ``None``
     - ``None``

.. code-block:: python

   import pygixml

   doc = pygixml.parse_string("""
   <library>
       <book id="1" category="fiction">
           <title>The Great Gatsby</title>
           <author>F. Scott Fitzgerald</author>
           <year>1925</year>
           <price>12.99</price>
       </book>
       <book id="2" category="non-fiction">
           <title>A Brief History of Time</title>
           <author>Stephen Hawking</author>
           <year>1988</year>
           <price>15.99</price>
       </book>
   </library>
   """)
   root = doc.root

   # Multiple matches
   books = root.select_nodes("book")
   print(f"Found {len(books)} books")    # Found 2 books

   # Single match
   book = root.select_node("book[@id='1']")
   if book:
       print(book.node.child("title").text())   # The Great Gatsby

   # Attribute filter
   fiction = root.select_nodes("book[@category='fiction']")
   for b in fiction:
       print(b.node.child("author").text())     # F. Scott Fitzgerald

Working with Results
~~~~~~~~~~~~~~~~~~~~

``select_nodes`` and ``select_node`` return **XPathNodeSet** and
**XPathNode** respectively.  Each ``XPathNode`` wraps either an
``XMLNode`` (``.node``) or an ``XMLAttribute`` (``.attribute``):

.. code-block:: python

   # XPathNodeSet: iterable
   for match in root.select_nodes("book/author"):
       print(match.node.text())

   # XPathNode: check for None
   match = root.select_node("book[@id='99']")
   if match:
       print("found")
   else:
       print("no match")

   # Selecting attributes returns XPathNode with .attribute
   for m in root.select_nodes("book/@id"):
       print(m.attribute.value)     # 1, 2

XPathQuery: Compile Once
~~~~~~~~~~~~~~~~~~~~~~~~~

Each call to ``select_nodes()`` parses and compiles the XPath string.
Use :py:class:`~pygixml.XPathQuery` when running the same query multiple
times:

.. code-block:: python

   # Compile once
   fiction_q = pygixml.XPathQuery("book[@category='fiction']")
   price_q   = pygixml.XPathQuery("book[price > 12]")

   # Evaluate many times
   fiction = fiction_q.evaluate_node_set(root)
   expensive = price_q.evaluate_node_set(root)

Typed Evaluations
^^^^^^^^^^^^^^^^^

``XPathQuery`` can return more than node sets.  Three typed methods:

.. code-block:: python

   # Boolean: does at least one book exist?
   pygixml.XPathQuery("book").evaluate_boolean(root)        # True

   pygixml.XPathQuery("book[price > 100]").evaluate_boolean(root)  # False

   # Number: count, sum, average
   pygixml.XPathQuery("count(book)").evaluate_number(root)         # 2.0
   pygixml.XPathQuery("sum(book/price)").evaluate_number(root)     # 28.98
   pygixml.XPathQuery("sum(book/price) div count(book)").evaluate_number(root)  # 14.49

   # String: first match as text
   pygixml.XPathQuery("book[1]/title").evaluate_string(root)       # The Great Gatsby
   pygixml.XPathQuery("concat(book[1]/title, ' by ', book[1]/author)").evaluate_string(root)
   # The Great Gatsby by F. Scott Fitzgerald

Common Patterns
~~~~~~~~~~~~~~~

.. code-block:: python

   # First / last / position
   root.select_node("book[1]")                     # first
   root.select_node("book[last()]")                # last
   root.select_nodes("book[position() <= 2]")      # first two

   # Text matching
   root.select_node("book[title='1984']")          # exact text
   root.select_nodes("book[contains(title, 'History')]")  # partial
   root.select_nodes("book[year < 1950]")          # numeric comparison

   # Multiple conditions
   root.select_nodes("book[@category='fiction' and year < 1950]")

   # Union of two node-sets
   root.select_nodes("book[@category='fiction'] | book[price > 14]")

   # Navigation: parent, siblings, descendants
   root.select_node("book[1]/title/..").node.name   # "book" (parent)
   root.select_nodes("book[1]/following-sibling::book")  # after first
   root.select_nodes("descendant::title")           # all titles at any depth

Supported Axes
~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - Axis
     - Shorthand
     - Example
   * - ``child``
     - (default)
     - ``book``
   * - ``attribute``
     - ``@``
     - ``@id``
   * - ``descendant``
     - ``//``
     - ``//title``
   * - ``descendant-or-self``
     - ``//``
     - ``.//title``
   * - ``parent``
     - ``..``
     - ``title/..``
   * - ``ancestor``
     - -
     - ``title/ancestor::library``
   * - ``ancestor-or-self``
     - -
     - ``title/ancestor-or-self::*``
   * - ``following-sibling``
     - -
     - ``book[1]/following-sibling::book``
   * - ``preceding-sibling``
     - -
     - ``book[3]/preceding-sibling::book``
   * - ``following``
     - -
     - ``book[1]/following::*``
   * - ``preceding``
     - -
     - ``book[3]/preceding::*``
   * - ``self``
     - ``.``
     - ``.``
   * - ``namespace``
     - -
     - ``namespace::*``

Supported Functions
~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - Category
     - Functions
   * - **Node-set**
     - ``position()``, ``last()``, ``count()``
   * - **String**
     - ``string()``, ``concat()``, ``contains()``,
       ``starts-with()``, ``substring()``, ``substring-before()``,
       ``substring-after()``, ``string-length()``, ``normalize-space()``,
       ``translate()``
   * - **Boolean**
     - ``boolean()``, ``not()``, ``true()``, ``false()``, ``lang()``
   * - **Number**
     - ``number()``, ``sum()``, ``floor()``, ``ceiling()``, ``round()``
   * - **Name**
     - ``name()``, ``local-name()``, ``namespace-uri()``

.. note::
   ``string-join()``, ``matches()`` (regex), and all XPath 2.0+ features are
   **not** available (pugixml implements XPath 1.0 only).

Performance
~~~~~~~~~~~

* **Use ``XPathQuery``** for repeated queries: compile once, evaluate many
  times.
* **Be specific**: ``library/book`` is faster than ``//book``.
* **Filter on attributes**: ``@id`` is faster than text comparison.
* **Limit results**: ``book[position() <= 10]`` beats fetching all and
  slicing in Python.


