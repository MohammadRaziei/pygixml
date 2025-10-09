API Reference
=============

This page provides detailed API documentation for all classes and functions in pygixml.

Convenience Functions
---------------------

.. py:function:: parse_string(xml_string)

   Parse XML from string and return XMLDocument.

   :param str xml_string: XML string to parse
   :return: XMLDocument object
   :rtype: XMLDocument
   :raises ValueError: If XML parsing fails

   **Example:**

   .. code-block:: python

      import pygixml
      doc = pygixml.parse_string('<root><item>test</item></root>')

.. py:function:: parse_file(file_path)

   Parse XML from file and return XMLDocument.

   :param str file_path: Path to XML file
   :return: XMLDocument object
   :rtype: XMLDocument
   :raises ValueError: If file cannot be read or XML parsing fails

   **Example:**

   .. code-block:: python

      import pygixml
      doc = pygixml.parse_file('data.xml')

XMLDocument Class
-----------------

.. py:class:: XMLDocument()

   Main XML document class representing the entire XML document.

   **Methods:**

   .. py:method:: load_string(content)

      Load XML from string.

      :param str content: XML string content
      :return: True if successful, False otherwise
      :rtype: bool

   .. py:method:: load_file(path)

      Load XML from file.

      :param str path: File path
      :return: True if successful, False otherwise
      :rtype: bool

   .. py:method:: save_file(path, indent="  ")

      Save XML to file.

      :param str path: File path
      :param str indent: Indentation string (default: two spaces)
      :raises Exception: If file cannot be written

   .. py:method:: reset()

      Reset the document (clear all content).

   .. py:method:: append_child(name)

      Append a child node to the document.

      :param str name: Node name
      :return: New XMLNode object
      :rtype: XMLNode

   .. py:method:: first_child()

      Get first child node.

      :return: First child XMLNode or None if no children
      :rtype: XMLNode or None

   .. py:method:: child(name)

      Get child node by name.

      :param str name: Child node name
      :return: Child XMLNode or None if not found
      :rtype: XMLNode or None

   **Example:**

   .. code-block:: python

      doc = pygixml.XMLDocument()
      root = doc.append_child("root")
      doc.save_file("output.xml")

XMLNode Class
-------------

.. py:class:: XMLNode()

   Represents an XML node in the document.

   **Methods:**

   .. py:method:: name()

      Get node name.

      :return: Node name or None if no name
      :rtype: str or None

   .. py:method:: value()

      Get node value.

      :return: Node value or None if no value
      :rtype: str or None

   .. py:method:: set_name(name)

      Set node name.

      :param str name: New node name
      :return: True if successful, False otherwise
      :rtype: bool

   .. py:method:: set_value(value)

      Set node value.

      :param str value: New node value
      :return: True if successful, False otherwise
      :rtype: bool

   .. py:method:: first_child()

      Get first child node.

      :return: First child XMLNode or None if no children
      :rtype: XMLNode or None

   .. py:method:: child(name)

      Get child node by name.

      :param str name: Child node name
      :return: Child XMLNode or None if not found
      :rtype: XMLNode or None

   .. py:method:: append_child(name)

      Append a child node.

      :param str name: Child node name
      :return: New XMLNode object
      :rtype: XMLNode

   .. py:method:: child_value(name=None)

      Get child value. If name is provided, get value of specific child. Otherwise get value of this node.

      :param str name: Optional child name
      :return: Child value or None if not found
      :rtype: str or None

   .. py:method:: next_sibling()

      Get next sibling node.

      :return: Next sibling XMLNode or None if no more siblings
      :rtype: XMLNode or None

   .. py:method:: previous_sibling()

      Get previous sibling node.

      :return: Previous sibling XMLNode or None if no previous sibling
      :rtype: XMLNode or None

   .. py:method:: parent()

      Get parent node.

      :return: Parent XMLNode or None if no parent
      :rtype: XMLNode or None

   .. py:method:: first_attribute()

      Get first attribute.

      :return: First XMLAttribute or None if no attributes
      :rtype: XMLAttribute or None

   .. py:method:: attribute(name)

      Get attribute by name.

      :param str name: Attribute name
      :return: XMLAttribute or None if not found
      :rtype: XMLAttribute or None

   .. py:method:: select_nodes(query)

      Select nodes using XPath query.

      :param str query: XPath query string
      :return: XPathNodeSet containing matching nodes
      :rtype: XPathNodeSet

   .. py:method:: select_node(query)

      Select single node using XPath query.

      :param str query: XPath query string
      :return: XPathNode or None if not found
      :rtype: XPathNode or None

   **Example:**

   .. code-block:: python

      node = root.first_child()
      print(f"Node name: {node.name()}")
      child = node.append_child("new_child")
      children = node.select_nodes("child")

XMLAttribute Class
------------------

.. py:class:: XMLAttribute()

   Represents an XML attribute.

   **Methods:**

   .. py:method:: name()

      Get attribute name.

      :return: Attribute name or None if no name
      :rtype: str or None

   .. py:method:: value()

      Get attribute value.

      :return: Attribute value or None if no value
      :rtype: str or None

   .. py:method:: set_name(name)

      Set attribute name.

      :param str name: New attribute name
      :return: True if successful, False otherwise
      :rtype: bool

   .. py:method:: set_value(value)

      Set attribute value.

      :param str value: New attribute value
      :return: True if successful, False otherwise
      :rtype: bool

   .. py:method:: next_attribute()

      Get next attribute.

      :return: Next XMLAttribute or None if no more attributes
      :rtype: XMLAttribute or None

   .. py:method:: previous_attribute()

      Get previous attribute.

      :return: Previous XMLAttribute or None if no previous attribute
      :rtype: XMLAttribute or None

   **Example:**

   .. code-block:: python

      attr = node.first_attribute()
      while attr:
          print(f"{attr.name()} = {attr.value()}")
          attr = attr.next_attribute()

XPath Classes
-------------

XPathQuery Class
~~~~~~~~~~~~~~~~

.. py:class:: XPathQuery(query)

   Compiled XPath query for efficient repeated execution.

   :param str query: XPath query string

   **Methods:**

   .. py:method:: evaluate_node_set(context_node)

      Evaluate query and return node set.

      :param XMLNode context_node: Context node for evaluation
      :return: XPathNodeSet containing matching nodes
      :rtype: XPathNodeSet

   .. py:method:: evaluate_node(context_node)

      Evaluate query and return first node.

      :param XMLNode context_node: Context node for evaluation
      :return: XPathNode or None if not found
      :rtype: XPathNode or None

   .. py:method:: evaluate_boolean(context_node)

      Evaluate query and return boolean result.

      :param XMLNode context_node: Context node for evaluation
      :return: Boolean result
      :rtype: bool

   .. py:method:: evaluate_number(context_node)

      Evaluate query and return numeric result.

      :param XMLNode context_node: Context node for evaluation
      :return: Numeric result
      :rtype: float

   .. py:method:: evaluate_string(context_node)

      Evaluate query and return string result.

      :param XMLNode context_node: Context node for evaluation
      :return: String result or None if empty
      :rtype: str or None

   **Example:**

   .. code-block:: python

      query = pygixml.XPathQuery("book[@category='fiction']")
      results = query.evaluate_node_set(root)

XPathNode Class
~~~~~~~~~~~~~~~

.. py:class:: XPathNode()

   Result of XPath query, representing a node or attribute.

   **Methods:**

   .. py:method:: node()

      Get XML node from XPath node.

      :return: XMLNode or None if no node
      :rtype: XMLNode or None

   .. py:method:: attribute()

      Get XML attribute from XPath node.

      :return: XMLAttribute or None if no attribute
      :rtype: XMLAttribute or None

   .. py:method:: parent()

      Get parent node.

      :return: Parent XMLNode or None if no parent
      :rtype: XMLNode or None

   **Example:**

   .. code-block:: python

      xpath_node = root.select_node("book[1]")
      if xpath_node:
          book_node = xpath_node.node()

XPathNodeSet Class
~~~~~~~~~~~~~~~~~~

.. py:class:: XPathNodeSet()

   Collection of XPath query results.

   **Methods and Properties:**

   .. py:method:: __len__()

      Get number of nodes in the set.

      :return: Number of nodes
      :rtype: int

   .. py:method:: __getitem__(index)

      Get node at specified index.

      :param int index: Index of node to retrieve
      :return: XPathNode at specified index
      :rtype: XPathNode
      :raises IndexError: If index out of range

   .. py:method:: __iter__()

      Iterate over nodes in the set.

      :return: Iterator of XPathNode objects
      :rtype: iterator

   **Example:**

   .. code-block:: python

      node_set = root.select_nodes("book")
      print(f"Found {len(node_set)} books")
      for node in node_set:
          book = node.node()
          print(book.child("title").child_value())

Node Types
----------

The following node types are available as constants:

.. py:data:: node_null
   :value: 0

   Null node

.. py:data:: node_document
   :value: 1

   Document node

.. py:data:: node_element
   :value: 2

   Element node

.. py:data:: node_pcdata
   :value: 3

   PCDATA node

.. py:data:: node_cdata
   :value: 4

   CDATA node

.. py:data:: node_comment
   :value: 5

   Comment node

.. py:data:: node_pi
   :value: 6

   Processing instruction node

.. py:data:: node_declaration
   :value: 7

   Declaration node

.. py:data:: node_doctype
   :value: 8

   DOCTYPE node

**Example:**

.. code-block:: python

   import pygixml
   node_type = node.node_type()
   if node_type == pygixml.node_element:
       print("This is an element node")

Error Handling
--------------

All methods that can fail will return appropriate values (like None or False) rather than throwing exceptions for expected error conditions. However, some operations may raise exceptions:

- ``parse_string()`` and ``parse_file()`` raise ``ValueError`` for invalid XML
- ``save_file()`` may raise exceptions for file system errors
- Indexing operations on ``XPathNodeSet`` raise ``IndexError`` for out-of-range access

Best Practices
--------------

1. **Check return values**: Always check if nodes/attributes exist before using them
2. **Use context managers**: For file operations, use try/except blocks
3. **Reuse XPathQuery**: For repeated queries, compile once and reuse
4. **Iterate efficiently**: Use the iterator pattern for large node sets

**Example of proper error handling:**

.. code-block:: python

   try:
       doc = pygixml.parse_string(xml_string)
   except ValueError as e:
       print(f"Failed to parse XML: {e}")
       return

   root = doc.first_child()
   if not root:
       print("Empty document")
       return

   book = root.child("book")
   if book:
       title = book.child("title")
       if title:
           print(f"Title: {title.child_value()}")

Complete Module Reference
-------------------------

For a complete list of all available classes and functions, see the :doc:`modules` page.
