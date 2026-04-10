Performance
===========

pygixml is designed for high-performance XML processing, leveraging the power
of pugixml's C++ implementation through Cython.

Benchmarks
----------

All numbers below come from the included benchmark suite
(``benchmarks/full_benchmark.py``) comparing **pygixml**, **lxml**, and
**xml.etree.ElementTree** on the same machine.

Parsing Performance
~~~~~~~~~~~~~~~~~~~

.. list-table:: XML Parsing Performance (warmed-up, 50 iterations)
   :header-rows: 1
   :widths: 20 25 20 20

   * - Size
     - pygixml
     - lxml
     - ElementTree
   * - 100
     - 0.000020 s
     - 0.000217 s
     - 0.000209 s
   * - 500
     - 0.000098 s
     - 0.000371 s
     - 0.000657 s
   * - 1 000
     - 0.000171 s
     - 0.001099 s
     - 0.001327 s
   * - 2 500
     - 0.000459 s
     - 0.002058 s
     - 0.003478 s
   * - 5 000
     - 0.000954 s
     - 0.004368 s
     - 0.007967 s
   * - 10 000
     - 0.002488 s
     - 0.011066 s
     - 0.018558 s

Measured with ``ParseFlags.MINIMAL`` (``pygixml.parse_string(xml, pygixml.ParseFlags.MINIMAL)``).
Skips escape processing, EOL normalization, and attribute whitespace conversion
for maximum throughput.  Use the default (``ParseFlags.DEFAULT``) when you need
full XML compliance.

Speedup vs ElementTree
~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: Parsing Speedup (how many times faster than ElementTree)
   :header-rows: 1
   :widths: 20 20

   * - Size
     - pygixml
   * - 100
     - **10.5×**
   * - 500
     - **6.7×**
   * - 1 000
     - **7.8×**
   * - 2 500
     - **7.6×**
   * - 5 000
     - **8.4×**
   * - 10 000
     - **7.5×**

pygixml consistently outperforms lxml by ~2× and ElementTree by **7–10×**
depending on document size.  Each row shows the faster of
``ParseFlags.DEFAULT`` and ``ParseFlags.MINIMAL``.

Traversal Performance
~~~~~~~~~~~~~~~~~~~~~

Traversal is measured as walking each top-level child, reading two sub-elements
and extracting their text content.

.. list-table:: Traversal (seconds)
   :header-rows: 1
   :widths: 20 20 20 20

   * - Size
     - pygixml
     - lxml
     - ElementTree
   * - 100
     - 0.000026 s
     - 0.000207 s
     - 0.000009 s
   * - 500
     - 0.000108 s
     - 0.001002 s
     - 0.000042 s
   * - 1 000
     - 0.000213 s
     - 0.002014 s
     - 0.000085 s
   * - 5 000
     - 0.001063 s
     - 0.010307 s
     - 0.000421 s
   * - 10 000
     - 0.002168 s
     - 0.020971 s
     - 0.000859 s

pygixml traversal is ~10× faster than lxml but slower than ElementTree in
absolute terms.  This is because every ``.child()`` and ``.child_value()``
call crosses the Python↔Cython boundary.  **Best practice:** use XPath for
bulk selection (which stays in C++) rather than walking nodes manually.

Memory Usage
------------

Peak memory during parsing, measured via ``tracemalloc``:

.. list-table:: Peak Memory (MB)
   :header-rows: 1
   :widths: 25 25 25 25

   * - Size
     - pygixml
     - lxml
     - ElementTree
   * - 1 000
     - **0.13 MB**
     - 0.13 MB
     - 1.01 MB
   * - 5 000
     - **0.67 MB**
     - 0.67 MB
     - 4.84 MB
   * - 10 000
     - **1.34 MB**
     - 1.34 MB
     - 9.68 MB

pygixml and lxml have nearly identical memory footprints (both backed by
C/C++ parsers), while ElementTree uses **~7× more memory** due to creating
full Python objects for every node and attribute.

Package Size
------------

.. list-table:: Installed Package Size
   :header-rows: 1
   :widths: 25 25

   * - Package
     - Size
   * - **pygixml**
     - **0.43 MB**
   * - lxml
     - 5.48 MB

pygixml is **12.7× smaller** than lxml in installed size according to
`pip-size <https://github.com/MohammadRaziei/pip-size>`_ package.

Performance Tips
----------------

Use XPathQuery for Repeated Queries
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # ✅ Good: compile once, evaluate many times
   query = pygixml.XPathQuery("book[@category='fiction']")
   for _ in range(1000):
       results = query.evaluate_node_set(root)

   # ❌ Bad: re-compile every iteration
   for _ in range(1000):
       results = root.select_nodes("book[@category='fiction']")

Be Specific in XPath Expressions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # ✅ Good: specific path
   books = root.select_nodes("library/book")

   # ❌ Bad: descendant-axis search
   books = root.select_nodes("//book")

Use Attributes for Filtering
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # ✅ Good: fast attribute comparison
   books = root.select_nodes("book[@id='123']")

   # ❌ Bad: slower text-node comparison
   books = root.select_nodes("book[id='123']")

Limit Result Sets
~~~~~~~~~~~~~~~~~

.. code-block:: python

   # ✅ Good: limit in the query
   first_10 = root.select_nodes("book[position() <= 10]")

   # ❌ Bad: fetch all then slice
   all_books = root.select_nodes("book")
   first_10 = all_books[:10]

Memory Management
-----------------

Automatic Cleanup
~~~~~~~~~~~~~~~~~

pygixml automatically manages memory through C++ destructors:

.. code-block:: python

   # Memory is automatically freed when objects go out of scope
   def process_large_xml():
       doc = pygixml.parse_file("large_file.xml")
       # ... process XML ...
       # Memory automatically freed when function returns

Document Reset
~~~~~~~~~~~~~~

.. code-block:: python

   # Reuse document to avoid reallocation
   doc = pygixml.XMLDocument()

   for filename in large_file_list:
       doc.reset()          # Clear existing content
       doc.load_file(filename)
       # ... process ...

Optimization Checklist
----------------------

* [ ] Use ``XPathQuery`` for repeated queries
* [ ] Prefer attribute filtering over text filtering
* [ ] Be specific in XPath expressions (avoid ``//``)
* [ ] Limit result sets with positional predicates
* [ ] Reuse ``XMLDocument`` objects with ``reset()``
* [ ] Use XPath for bulk selection, iterate results in Python
* [ ] Avoid unnecessary string conversions

Running Benchmarks
------------------

Reproduce the numbers on your own machine:

.. code-block:: bash

   # Full suite: parsing, memory, package size across 6 XML sizes
   python benchmarks/full_benchmark.py

   # Legacy parsing-only benchmark
   python benchmarks/benchmark_parsing.py

The full suite tests 100 – 10 000 element documents over 5 iterations,
measures peak memory at 1 000 / 5 000 / 10 000 elements, and reports
installed package sizes.
