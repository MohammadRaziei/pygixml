XPath Support
=============

pygixml provides full XPath 1.0 support through pugixml's powerful XPath implementation.

Basic XPath Usage
-----------------

Selecting Nodes
~~~~~~~~~~~~~~~

.. code-block:: python

   import pygixml

   xml_string = '''
   <library>
       <book id="1" category="fiction">
           <title>The Great Gatsby</title>
           <author>F. Scott Fitzgerald</author>
           <year>1925</year>
           <price>12.99</price>
       </book>
       <book id="2" category="fiction">
           <title>1984</title>
           <author>George Orwell</author>
           <year>1949</year>
           <price>10.99</price>
       </book>
       <book id="3" category="non-fiction">
           <title>A Brief History of Time</title>
           <author>Stephen Hawking</author>
           <year>1988</year>
           <price>15.99</price>
       </book>
   </library>
   '''

   doc = pygixml.parse_string(xml_string)
   root = doc.first_child()

   # Select all books
   books = root.select_nodes("book")
   print(f"Found {len(books)} books")

   # Select single book
   book = root.select_node("book[@id='1']")
   if book:
       print(f"Book 1: {book.node().child('title').child_value()}")

   # Select by attribute
   fiction_books = root.select_nodes("book[@category='fiction']")
   print(f"Found {len(fiction_books)} fiction books")

XPath Query Object
------------------

For repeated queries, use ``XPathQuery`` for better performance:

.. code-block:: python

   # Create XPath query once, use multiple times
   fiction_query = pygixml.XPathQuery("book[@category='fiction']")
   expensive_query = pygixml.XPathQuery("book[price > 12]")

   fiction_books = fiction_query.evaluate_node_set(root)
   expensive_books = expensive_query.evaluate_node_set(root)

   print(f"Fiction books: {len(fiction_books)}")
   print(f"Expensive books: {len(expensive_books)}")

XPath Evaluation Types
----------------------

Boolean Evaluation
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Check if any books exist
   has_books = pygixml.XPathQuery("book").evaluate_boolean(root)
   print(f"Has books: {has_books}")  # Output: True

   # Check if there are expensive books
   has_expensive = pygixml.XPathQuery("book[price > 20]").evaluate_boolean(root)
   print(f"Has expensive books: {has_expensive}")  # Output: False

Number Evaluation
~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get average price
   avg_price = pygixml.XPathQuery("sum(book/price) div count(book)").evaluate_number(root)
   print(f"Average price: ${avg_price:.2f}")

   # Get total books
   total_books = pygixml.XPathQuery("count(book)").evaluate_number(root)
   print(f"Total books: {total_books}")

String Evaluation
~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get first book title
   first_title = pygixml.XPathQuery("book[1]/title").evaluate_string(root)
   print(f"First title: {first_title}")

   # Get all titles concatenated
   all_titles = pygixml.XPathQuery("string-join(book/title, ', ')").evaluate_string(root)
   print(f"All titles: {all_titles}")

Advanced XPath Features
-----------------------

Positional Functions
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # First book
   first_book = root.select_node("book[1]")

   # Last book
   last_book = root.select_node("book[last()]")

   # Books in specific positions
   second_book = root.select_node("book[2]")
   first_two_books = root.select_nodes("book[position() <= 2]")

Text and Value Selection
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Select by text content
   gatsby = root.select_node("book[title='The Great Gatsby']")

   # Select by partial text
   history_books = root.select_nodes("book[contains(title, 'History')]")

   # Select by numeric comparison
   old_books = root.select_nodes("book[year < 1950]")
   expensive_books = root.select_nodes("book[price > 12]")

Complex Expressions
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Multiple conditions
   old_fiction = root.select_nodes("book[@category='fiction' and year < 1950]")

   # Union of selections
   fiction_or_expensive = root.select_nodes("book[@category='fiction'] | book[price > 14]")

   # Nested selections
   authors = root.select_nodes("book/author")
   for author in authors:
       print(f"Author: {author.node().child_value()}")

XPath Axes
----------

Child Axis
~~~~~~~~~~

.. code-block:: python

   # All direct children named 'book'
   books = root.select_nodes("child::book")

   # All children (any name)
   all_children = root.select_nodes("child::*")

Attribute Axis
~~~~~~~~~~~~~~

.. code-block:: python

   # All attributes
   all_attributes = root.select_nodes("book/@*")

   # Specific attribute
   ids = root.select_nodes("book/@id")

Descendant Axis
~~~~~~~~~~~~~~~

.. code-block:: python

   # All descendant titles (at any level)
   all_titles = root.select_nodes("descendant::title")

   # Titles that are grandchildren
   grandchild_titles = root.select_nodes("book/*/title")

XPath Functions
---------------

String Functions
~~~~~~~~~~~~~~~~

.. code-block:: python

   # Contains
   contains_gatsby = root.select_nodes("book[contains(title, 'Gatsby')]")

   # Starts with
   starts_with_the = root.select_nodes("book[starts-with(title, 'The')]")

   # String length
   long_titles = root.select_nodes("book[string-length(title) > 15]")

   # Substring
   substring_books = root.select_nodes("book[substring(title, 1, 3) = 'The']")

Number Functions
~~~~~~~~~~~~~~~~

.. code-block:: python

   # Round
   rounded_price = pygixml.XPathQuery("round(book[1]/price)").evaluate_number(root)

   # Floor and ceiling
   floor_price = pygixml.XPathQuery("floor(book[1]/price)").evaluate_number(root)
   ceil_price = pygixml.XPathQuery("ceiling(book[1]/price)").evaluate_number(root)

Node Set Functions
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Count
   book_count = pygixml.XPathQuery("count(book)").evaluate_number(root)

   # Position
   first_book = root.select_node("book[position() = 1]")

   # Last position
   last_book = root.select_node("book[position() = last()]")

Performance Tips
----------------

1. **Use XPathQuery for repeated queries** - Compile once, use many times
2. **Be specific in your paths** - Avoid wildcards when possible
3. **Use attributes for filtering** - Attribute comparisons are faster than text comparisons
4. **Limit result sets** - Use positional predicates to limit results

Common XPath Patterns
---------------------

.. code-block:: python

   # Find elements with specific attribute
   elements_with_id = root.select_nodes("//*[@id]")

   # Find elements with specific text
   elements_with_text = root.select_nodes("//*[text()='specific text']")

   # Find parent of specific element
   parent_of_title = root.select_node("title/..")

   # Find siblings
   next_sibling = root.select_node("book[1]/following-sibling::book[1]")

   # Find ancestors
   ancestors = root.select_nodes("title/ancestor::*")

Supported XPath 1.0 Features
-----------------------------

- All core XPath 1.0 axes: ``child``, ``descendant``, ``parent``, ``ancestor``, ``following-sibling``, ``preceding-sibling``, ``following``, ``preceding``, ``attribute``, ``namespace``, ``self``, ``descendant-or-self``, ``ancestor-or-self``
- All XPath 1.0 functions: ``string``, ``number``, ``boolean``, ``concat``, ``contains``, ``starts-with``, ``substring``, ``substring-before``, ``substring-after``, ``string-length``, ``normalize-space``, ``translate``, ``not``, ``true``, ``false``, ``lang``, ``sum``, ``floor``, ``ceiling``, ``round``, ``position``, ``last``, ``count``, ``local-name``, ``namespace-uri``, ``name``
- Full boolean and comparison operators
- Complete numeric operations
- String operations and comparisons
