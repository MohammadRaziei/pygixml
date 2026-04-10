Advanced Tips
=============

Performance tuning, parse flags, and advanced usage patterns for pygixml.

.. _parse-flags:

Parse Flags
-----------

All parse functions accept a :py:class:`~pygixml.ParseFlags` enum to control
exactly how pugixml processes the input.  By default pygixml uses
``ParseFlags.DEFAULT`` which enables all standard XML processing.  You can
trade strictness for speed when you know your input is clean.

Quick Example
~~~~~~~~~~~~~

.. code-block:: python

   import pygixml

   # Fastest possible parse — skip everything optional
   doc = pygixml.parse_string(xml, pygixml.ParseFlags.MINIMAL)

   # Combine specific flags with bitwise OR
   flags = pygixml.ParseFlags.COMMENTS | pygixml.ParseFlags.CDATA
   doc = pygixml.parse_string(xml, flags)

The same flags apply to :py:func:`~pygixml.parse_string`,
:py:func:`~pygixml.parse_file`, :py:meth:`~pygixml.XMLDocument.load_string`,
and :py:meth:`~pygixml.XMLDocument.load_file`.

Available Flags
~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Flag
     - What it enables
   * - ``ParseFlags.MINIMAL``
     - No optional processing — fastest parse.  Skips escapes, EOL
       normalization, and all whitespace handling.
   * - ``ParseFlags.COMMENTS``
     - Parse ``<!--comment-->`` nodes.  Without this flag, comments are
       silently skipped.
   * - ``ParseFlags.CDATA``
     - Parse ``<![CDATA[...]]>`` sections.  Without this flag, CDATA content
       is treated as regular PCDATA.
   * - ``ParseFlags.PI``
     - Parse processing instructions (``<?target data?>``).
   * - ``ParseFlags.ESCAPES``
     - Process entity references (``&amp;``, ``&lt;``, ``&quot;``, etc.).
       Disabling this leaves ``&amp;`` as literal text.
   * - ``ParseFlags.EOL``
     - Normalize line endings (``\r\n``, ``\r``) to ``\n``.
   * - ``ParseFlags.WS_PCDATA``
     - Convert whitespace characters in PCDATA to spaces.
   * - ``ParseFlags.WS_PCDATA_SINGLE``
     - Collapse consecutive whitespace in PCDATA to a single space.
   * - ``ParseFlags.WCONV_ATTRIBUTE``
     - Convert attribute whitespace (tabs, newlines) to spaces.
   * - ``ParseFlags.WNORM_ATTRIBUTE``
     - Normalize attribute whitespace (trim leading/trailing, collapse
       consecutive).
   * - ``ParseFlags.DECLARATION``
     - Parse the ``<?xml version="1.0" ...?>`` declaration node.
   * - ``ParseFlags.DOCTYPE``
     - Parse the ``<!DOCTYPE ...>`` node.
   * - ``ParseFlags.TRIM_PCDATA``
     - Trim leading and trailing PCDATA whitespace.
   * - ``ParseFlags.FRAGMENT``
     - Parse XML fragments that lack a root element.  Useful for processing
       partial documents.
   * - ``ParseFlags.EMBED_PCDATA``
     - Parse embedded PCDATA as markup.  Handles cases where escaped XML
       appears inside text content.
   * - ``ParseFlags.MERGE_PCDATA``
     - Merge adjacent PCDATA nodes into a single node.
   * - ``ParseFlags.DEFAULT``
     - All standard processing enabled.  This is the default when no flag
       is specified.
   * - ``ParseFlags.FULL``
     - Same as ``DEFAULT`` — full XML compliance.

When to Use MINIMAL
~~~~~~~~~~~~~~~~~~~

``ParseFlags.MINIMAL`` is the fastest parse mode.  It skips:

* Escape processing (``&amp;`` stays as ``&amp;``)
* EOL normalization
* Attribute whitespace conversion/normalization
* PCDATA whitespace handling

Use it when:

* You control the XML source and know it has no escapes
* You only need element structure, not text formatting
* You're processing large documents in a hot path

On real-world XML with lots of escaped content, MINIMAL can be up to **~16%
faster** than DEFAULT.

XPathQuery for Repeated Queries
-------------------------------

When running the same XPath query multiple times, use
:py:class:`~pygixml.XPathQuery` to compile once and evaluate many times:

.. code-block:: python

   # ✅ Good: compile once, evaluate many times
   query = pygixml.XPathQuery("book[@category='fiction']")
   for i in range(1000):
       results = query.evaluate_node_set(root)

   # ❌ Bad: re-compile every iteration
   for i in range(1000):
       results = root.select_nodes("book[@category='fiction']")

Be Specific in XPath Expressions
--------------------------------

Avoid the descendant-axis search (``//``) when you know the structure:

.. code-block:: python

   # ✅ Good: specific path
   books = root.select_nodes("library/book")

   # ❌ Bad: scans entire document
   books = root.select_nodes("//book")

Use Attributes for Filtering
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Attribute comparisons are faster than text-node comparisons:

.. code-block:: python

   # ✅ Good: fast attribute comparison
   books = root.select_nodes("book[@id='123']")

   # ❌ Bad: slower text comparison
   books = root.select_nodes("book[id='123']")

Limit Result Sets
~~~~~~~~~~~~~~~~~

Limit results in the query rather than slicing in Python:

.. code-block:: python

   # ✅ Good: limit in the query
   first_10 = root.select_nodes("book[position() <= 10]")

   # ❌ Bad: fetch all then slice
   all_books = root.select_nodes("book")
   first_10 = all_books[:10]

Document Reuse
--------------

Reuse an :py:class:`~pygixml.XMLDocument` with ``reset()`` to avoid
repeated allocations when processing many files:

.. code-block:: python

   doc = pygixml.XMLDocument()

   for filename in file_list:
       doc.reset()              # Clear existing content
       doc.load_file(filename)
       # ... process ...

Processing Large Files
----------------------

For documents with thousands of elements, use XPath to select only what you
need rather than walking the entire tree in Python:

.. code-block:: python

   # ✅ Fast: let XPath filter in C++
   fiction = root.select_nodes("book[@category='fiction']")

   # ❌ Slower: filter in Python with per-node calls
   book = root.first_child()
   while book:
       cat = book.attribute("category")
       if cat and cat.value == "fiction":
           fiction.append(book)
       book = book.next_sibling

Every ``.child()``, ``.attribute()``, and ``.text()`` call crosses the
Python↔Cython boundary.  Minimizing these calls in tight loops has the
biggest impact on traversal speed.

Node Identity and Fast Lookup
-----------------------------

Unlike pugixml, which works exclusively with C++ object references,
pygixml introduces ``mem_id`` — a **pygixml-specific** numeric
identifier that uniquely tracks each node.  Each :class:`~pygixml.XMLNode`
exposes a :attr:`~pygixml.XMLNode.mem_id`, making node identity checks,
caching, and fast lookups possible directly from Python.

Because ``mem_id`` is a plain integer, it is **hashable and ideal for use
as a dictionary key** — a common pattern when building indexes, caches, or
associating extra data with specific nodes:

.. code-block:: python

   # Cache node metadata by mem_id
   cache = {}
   for node in doc:
       cache[node.mem_id] = {
           "xpath": node.xpath,
           "depth": node.xpath.count("/"),
       }

There are two ways to look up a node by its identifier:

:meth:`~pygixml.XMLNode.find_mem_id` — safe, **O(n)**
   Walks the tree from the current node, comparing identifiers.  Returns
   ``None`` if the node is not found.

   .. code-block:: python

      node_id = item.mem_id
      found = root.find_mem_id(node_id)   # safe, but O(n)

:meth:`~pygixml.XMLNode.from_mem_id_unsafe` — instant, **O(1)**
   Reconstructs an ``XMLNode`` directly from the identifier.  No tree
   traversal — the lookup is instantaneous.

   .. code-block:: python

      node_id = item.mem_id
      node = pygixml.XMLNode.from_mem_id_unsafe(node_id)  # O(1)

   ⚠️ **Warning**: If the identifier is stale (the document was freed or the
   node was deleted), calling methods on the returned object **may cause a
   segmentation fault**.  Use this only when you are certain the identifier
   still belongs to a live node.

**Which to choose?**  For most code, ``find_mem_id`` is the right choice —
it's safe and fast enough for typical use.  ``from_mem_id_unsafe`` is
reserved for performance-critical hot paths where you've profiled and
confirmed that the **O(n)** tree walk is a bottleneck.
