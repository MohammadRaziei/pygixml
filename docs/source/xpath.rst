XPath Support
=============

pygixml exposes pugixml's full XPath 1.0 engine.  Queries execute in C++ —
only the results you access cross the Python boundary.

Selection Methods
-----------------

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
--------------------

``select_nodes`` and ``select_node`` return **XPathNodeSet** and
**XPathNode** respectively.  Each ``XPathNode`` wraps either an
``XMLNode`` (``.node``) or an ``XMLAttribute`` (``.attribute``):

.. code-block:: python

   # XPathNodeSet — iterable
   for match in root.select_nodes("book/author"):
       print(match.node.text())

   # XPathNode — check for None
   match = root.select_node("book[@id='99']")
   if match:
       print("found")
   else:
       print("no match")

   # Selecting attributes returns XPathNode with .attribute
   for m in root.select_nodes("book/@id"):
       print(m.attribute.value)     # 1, 2

XPathQuery — Compile Once
-------------------------

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
~~~~~~~~~~~~~~~~~

``XPathQuery`` can return more than node sets.  Three typed methods:

.. code-block:: python

   # Boolean — does at least one book exist?
   pygixml.XPathQuery("book").evaluate_boolean(root)        # True

   pygixml.XPathQuery("book[price > 100]").evaluate_boolean(root)  # False

   # Number — count, sum, average
   pygixml.XPathQuery("count(book)").evaluate_number(root)         # 2.0
   pygixml.XPathQuery("sum(book/price)").evaluate_number(root)     # 28.98
   pygixml.XPathQuery("sum(book/price) div count(book)").evaluate_number(root)  # 14.49

   # String — first match as text
   pygixml.XPathQuery("book[1]/title").evaluate_string(root)       # The Great Gatsby
   pygixml.XPathQuery("concat(book[1]/title, ' by ', book[1]/author)").evaluate_string(root)
   # The Great Gatsby by F. Scott Fitzgerald

Common Patterns
---------------

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

   # Navigation — parent, siblings, descendants
   root.select_node("book[1]/title/..").node.name   # "book" (parent)
   root.select_nodes("book[1]/following-sibling::book")  # after first
   root.select_nodes("descendant::title")           # all titles at any depth

Supported Axes
--------------

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
     - —
     - ``title/ancestor::library``
   * - ``ancestor-or-self``
     - —
     - ``title/ancestor-or-self::*``
   * - ``following-sibling``
     - —
     - ``book[1]/following-sibling::book``
   * - ``preceding-sibling``
     - —
     - ``book[3]/preceding-sibling::book``
   * - ``following``
     - —
     - ``book[1]/following::*``
   * - ``preceding``
     - —
     - ``book[3]/preceding::*``
   * - ``self``
     - ``.``
     - ``.``
   * - ``namespace``
     - —
     - ``namespace::*``

Supported Functions
-------------------

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
   **not** available — pugixml implements XPath 1.0 only.

Performance
-----------

* **Use ``XPathQuery``** for repeated queries — compile once, evaluate many
  times.
* **Be specific** — ``library/book`` is faster than ``//book``.
* **Filter on attributes** — ``@id`` is faster than text comparison.
* **Limit results** — ``book[position() <= 10]`` beats fetching all and
  slicing in Python.
