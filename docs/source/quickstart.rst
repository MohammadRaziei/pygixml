Quick Start
===========

This guide will help you get started with pygixml quickly.

Basic Usage
-----------

Parsing XML
~~~~~~~~~~~

.. code-block:: python

   import pygixml

   # Parse from string
   xml_string = '''
   <library>
       <book id="1">
           <title>The Great Gatsby</title>
           <author>F. Scott Fitzgerald</author>
           <year>1925</year>
       </book>
   </library>
   '''
   doc = pygixml.parse_string(xml_string)

   # Parse from file
   doc = pygixml.parse_file("data.xml")

Navigating XML
~~~~~~~~~~~~~~

.. code-block:: python

   # Get root element
   root = doc.first_child()
   print(f"Root name: {root.name()}")  # Output: library

   # Access children
   book = root.first_child()
   print(f"Book name: {book.name()}")  # Output: book

   # Get specific child by name
   title = book.child("title")
   print(f"Title: {title.child_value()}")  # Output: The Great Gatsby

   # Iterate through children
   current = root.first_child()
   while current:
       print(f"Node: {current.name()}")
       current = current.next_sibling()

Working with Attributes
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get attribute
   book_id = book.attribute("id")
   print(f"Book ID: {book_id.value()}")  # Output: 1

   # Iterate through attributes
   attr = book.first_attribute()
   while attr:
       print(f"Attribute: {attr.name()} = {attr.value()}")
       attr = attr.next_attribute()

Creating and Modifying XML
--------------------------

Creating New Documents
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pygixml

   # Create new document
   doc = pygixml.XMLDocument()

   # Add root element
   root = doc.append_child("library")

   # Add child elements
   book = root.append_child("book")
   book.set_attribute("id", "1")

   title = book.append_child("title")
   title.set_value("The Great Gatsby")

   author = book.append_child("author")
   author.set_value("F. Scott Fitzgerald")

   # Save to file
   doc.save_file("output.xml")

Modifying Existing XML
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Load existing XML
   doc = pygixml.parse_string(xml_string)
   root = doc.first_child()

   # Modify values
   book = root.first_child()
   book.child("title").set_value("New Title")

   # Add new elements
   price = book.append_child("price")
   price.set_value("12.99")

   # Remove elements
   year = book.child("year")
   book.remove_child(year)

XPath Queries
-------------

Basic XPath Usage
~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Select all books
   books = root.select_nodes("book")
   print(f"Found {len(books)} books")

   # Select specific book by ID
   book1 = root.select_node("book[@id='1']")
   if book1:
       print(f"Book 1 title: {book1.node().child('title').child_value()}")

   # Select books by year
   old_books = root.select_nodes("book[year < 1950]")
   print(f"Found {len(old_books)} old books")

Advanced XPath
~~~~~~~~~~~~~~

.. code-block:: python

   # Using XPathQuery for repeated queries
   query = pygixml.XPathQuery("book[price > 10]")
   expensive_books = query.evaluate_node_set(root)

   # XPath evaluations
   has_books = pygixml.XPathQuery("book").evaluate_boolean(root)
   avg_price = pygixml.XPathQuery("sum(book/price) div count(book)").evaluate_number(root)
   first_title = pygixml.XPathQuery("book[1]/title").evaluate_string(root)

Error Handling
--------------

.. code-block:: python

   try:
       doc = pygixml.parse_string(invalid_xml)
   except ValueError as e:
       print(f"Failed to parse XML: {e}")

   try:
       doc.save_file("/invalid/path/file.xml")
   except Exception as e:
       print(f"Failed to save file: {e}")

Next Steps
----------

- Learn about :doc:`XPath capabilities <xpath>`
- Explore :doc:`API reference <api>`
- Check out :doc:`examples <examples>`
- Read about :doc:`performance <performance>`
