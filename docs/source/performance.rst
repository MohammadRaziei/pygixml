Performance
===========

pygixml is designed for high-performance XML processing, leveraging the power of pugixml's C++ implementation through Cython.

Benchmarks
----------

Parsing Performance
~~~~~~~~~~~~~~~~~~~

pygixml is significantly faster than Python's built-in XML libraries:

.. list-table:: XML Parsing Performance (Lower is better)
   :header-rows: 1
   :widths: 40 30 30

   * - Library
     - Time (ms)
     - Relative Speed
   * - **pygixml**
     - **63 ms**
     - **1.0x**
   * - lxml
     - 125 ms
     - 2.0x slower
   * - ElementTree
     - 1,000 ms
     - 15.9x slower

Memory Usage
~~~~~~~~~~~~

.. list-table:: Memory Usage Comparison
   :header-rows: 1
   :widths: 40 30 30

   * - Library
     - Memory (MB)
     - Relative Usage
   * - **pygixml**
     - **45 MB**
     - **1.0x**
   * - lxml
     - 78 MB
     - 1.7x more
   * - ElementTree
     - 120 MB
     - 2.7x more

XPath Performance
~~~~~~~~~~~~~~~~~

.. list-table:: XPath Query Performance (Queries/second)
   :header-rows: 1
   :widths: 40 30 30

   * - Library
     - QPS
     - Relative Speed
   * - **pygixml**
     - **15,200**
     - **1.0x**
   * - lxml
     - 8,500
     - 1.8x slower
   * - ElementTree
     - 950
     - 16x slower

Performance Tips
----------------

Use XPathQuery for Repeated Queries
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # ✅ Good: Compile once, use many times
   query = pygixml.XPathQuery("book[@category='fiction']")
   for i in range(1000):
       results = query.evaluate_node_set(root)

   # ❌ Bad: Compile every time
   for i in range(1000):
       results = root.select_nodes("book[@category='fiction']")

Be Specific in XPath Expressions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # ✅ Good: Specific path
   books = root.select_nodes("library/book")

   # ❌ Bad: Wildcard search
   books = root.select_nodes("//book")

   # ✅ Good: Attribute filtering
   fiction_books = root.select_nodes("book[@category='fiction']")

   # ❌ Bad: Text filtering
   fiction_books = root.select_nodes("book[category='fiction']")

Use Attributes for Filtering
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # ✅ Good: Fast attribute comparison
   books = root.select_nodes("book[@id='123']")

   # ❌ Bad: Slower text comparison
   books = root.select_nodes("book[id='123']")

Limit Result Sets
~~~~~~~~~~~~~~~~~

.. code-block:: python

   # ✅ Good: Limit results
   first_10_books = root.select_nodes("book[position() <= 10]")

   # ❌ Bad: Get all then slice
   all_books = root.select_nodes("book")
   first_10_books = all_books[:10]

Avoid Unnecessary String Conversions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # ✅ Good: Work with nodes directly
   book = root.select_node("book[1]")
   title = book.node().child("title").child_value()

   # ❌ Bad: Convert to string and parse
   xml_string = doc.to_string()
   # ... string processing ...

Memory Management
-----------------

Automatic Cleanup
~~~~~~~~~~~~~~~~~

pygixml automatically manages memory through C++ destructors:

.. code-block:: python

   # Memory is automatically freed when objects go out of scope
   def process_large_xml():
       doc = pygixml.parse_file("large_file.xml")  # Memory allocated
       # ... process XML ...
       # Memory automatically freed when function returns

Document Reset
~~~~~~~~~~~~~~

.. code-block:: python

   # Reuse document to avoid reallocation
   doc = pygixml.XMLDocument()

   for filename in large_file_list:
       doc.reset()  # Clear existing content
       doc.load_file(filename)
       # ... process ...

Large File Handling
-------------------

Streaming Processing
~~~~~~~~~~~~~~~~~~~~

For very large files, process in chunks:

.. code-block:: python

   def process_large_xml_in_chunks(filename, chunk_size=1000):
       doc = pygixml.parse_file(filename)
       root = doc.first_child()
       
       # Process books in chunks
       books = root.select_nodes("book")
       for i in range(0, len(books), chunk_size):
           chunk = books[i:i + chunk_size]
           process_chunk(chunk)
           
           # Free memory for processed chunk
           del chunk

Memory-Efficient Iteration
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Use iterators instead of loading all nodes
   def iterate_books_efficiently(root):
       book = root.first_child()
       while book:
           process_book(book)
           book = book.next_sibling()

Real-World Performance Examples
-------------------------------

High-Volume Data Processing
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pygixml
   import time

   def benchmark_processing():
       # Large dataset (10,000 books)
       large_xml = generate_large_xml(10000)
       
       start_time = time.time()
       
       doc = pygixml.parse_string(large_xml)
       root = doc.first_child()
       
       # Process all books with XPath
       fiction_books = root.select_nodes("book[@category='fiction']")
       expensive_books = root.select_nodes("book[price > 20]")
       recent_books = root.select_nodes("book[year >= 2020]")
       
       # Complex filtering
       target_books = root.select_nodes(
           "book[@category='fiction' and price < 15 and year >= 2010]"
       )
       
       end_time = time.time()
       
       print(f"Processed {len(fiction_books)} fiction books")
       print(f"Processed {len(expensive_books)} expensive books") 
       print(f"Processed {len(recent_books)} recent books")
       print(f"Found {len(target_books)} target books")
       print(f"Total time: {end_time - start_time:.3f} seconds")

Web Application Scenario
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from flask import Flask, request
   import pygixml

   app = Flask(__name__)

   @app.route('/api/books/filter', methods=['POST'])
   def filter_books():
       xml_data = request.data.decode('utf-8')
       
       # Parse XML (fast)
       doc = pygixml.parse_string(xml_data)
       root = doc.first_child()
       
       # Extract filter parameters
       category = request.args.get('category')
       max_price = float(request.args.get('max_price', 1000))
       min_year = int(request.args.get('min_year', 0))
       
       # Build dynamic XPath query
       conditions = []
       if category:
           conditions.append(f"@category='{category}'")
       if max_price < 1000:
           conditions.append(f"price <= {max_price}")
       if min_year > 0:
           conditions.append(f"year >= {min_year}")
           
       xpath_query = "book"
       if conditions:
           xpath_query += f"[{' and '.join(conditions)}]"
       
       # Execute query (very fast)
       results = root.select_nodes(xpath_query)
       
       # Format response
       books = []
       for result in results:
           book_node = result.node()
           books.append({
               'title': book_node.child('title').child_value(),
               'author': book_node.child('author').child_value(),
               'price': float(book_node.child('price').child_value()),
               'year': int(book_node.child('year').child_value())
           })
       
       return {'books': books, 'count': len(books)}

Comparison with Other Libraries
-------------------------------

vs. lxml
~~~~~~~~

**Advantages of pygixml:**
- 2x faster parsing
- Lower memory usage
- Simpler API
- No external dependencies

**When to use lxml:**
- Need XPath 2.0/3.0 features
- Require XML Schema validation
- Need XSLT transformation

vs. ElementTree
~~~~~~~~~~~~~~~

**Advantages of pygixml:**
- 16x faster parsing
- 2.7x less memory
- Full XPath 1.0 support
- Better performance with large files

**When to use ElementTree:**
- Standard library requirement
- Simple XML tasks only
- No performance requirements

Performance Testing
-------------------

You can run the included benchmarks:

.. code-block:: bash

   # Run performance tests
   python benchmarks/benchmark_parsing.py

   # Generate performance report
   python benchmarks/clean_visualization.py

The benchmarks compare pygixml against lxml and ElementTree across various metrics including parsing speed, memory usage, and XPath performance.

Optimization Checklist
----------------------

- [ ] Use ``XPathQuery`` for repeated queries
- [ ] Prefer attribute filtering over text filtering
- [ ] Be specific in XPath expressions (avoid ``//``)
- [ ] Limit result sets with positional predicates
- [ ] Reuse ``XMLDocument`` objects with ``reset()``
- [ ] Process large files in chunks
- [ ] Use iterators for large node sets
- [ ] Avoid unnecessary string conversions

By following these guidelines, you can achieve optimal performance with pygixml in your applications.
