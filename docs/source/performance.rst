Performance
===========

pygixml is designed for high-performance XML processing, leveraging the power
of pugixml's C++ implementation (and a streaming yxml layer for oversized
documents) through Cython.

Benchmarks
----------

The numbers below come from the full benchmark suite in ``benchmarks/`` --
parsing, ``dictify``, ``objectify``, and ``jsonify`` measured against lxml,
ElementTree, xmltodict, and xmljson, plus memory-at-scale and install
footprint. It's embedded below as the real interactive report rather than
copied in as a static table, so nothing here was manually transcribed or
rounded off.

The report itself is refreshed on a schedule
(``.github/workflows/benchmark.yml``, weekly, plus on-demand), not on every
commit -- benchmark timing needs a stable, quiet machine to mean anything,
which a shared per-PR CI runner isn't. So this can lag the very latest commit
by up to a week; it won't ever be wildly out of date, but if you changed
something performance-sensitive today, don't expect to see it reflected here
yet.

.. raw:: html

   <div class="benchmark-embed-card">
     <div class="benchmark-embed-toolbar">
       <span>Live benchmark report</span>
       <a href="_static/benchmark-report.html" target="_blank" rel="noopener">Open full report &#8599;</a>
     </div>
     <iframe id="pygixml-benchmark-iframe" class="benchmark-embed-frame"
             src="_static/benchmark-report.html" title="pygixml benchmark report"
             loading="lazy"></iframe>
   </div>
   <script>
   (function () {
     var frame = document.getElementById('pygixml-benchmark-iframe');
     function fit() {
       try {
         var doc = frame.contentWindow.document;
         var h = Math.max(doc.documentElement.scrollHeight, doc.body.scrollHeight);
         if (h > 0) { frame.style.height = h + 'px'; }
       } catch (e) { /* cross-origin fallback: keep the CSS default height */ }
     }
     frame.addEventListener('load', function () {
       fit();
       setTimeout(fit, 300);   // charts finish laying out a beat after load
     });
     window.addEventListener('resize', fit);
   })();
   </script>

Reproducing or updating these numbers is one CMake build away -- see
`benchmarks/README.md <https://github.com/MohammadRaziei/pygixml/blob/master/benchmarks/README.md>`_
for the full methodology (corpus generation, why timing uses best-of-N, and a
real memory-measurement gotcha we hit building this exact report).

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
------------------

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
-----------------------

* Use ``XPathQuery`` for repeated queries
* Prefer attribute filtering over text filtering
* Be specific in XPath expressions (avoid ``//``)
* Limit result sets with positional predicates
* Reuse ``XMLDocument`` objects with ``reset()``
* Use XPath for bulk selection, iterate results in Python
* Avoid unnecessary string conversions
* For giant documents, prefer ``jsonify.stream_dump`` over building a full
  DOM -- see the memory panel above for what that trades away and gains
