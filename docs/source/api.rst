API Reference
=============

This page provides detailed API documentation for all classes and functions in pygixml.

Convenience Functions
---------------------

.. py:function:: parse_string(xml_string)

   Parse XML from string and return XMLDocument.

   :param str xml_string: XML content as string
   :return: Parsed XML document
   :rtype: XMLDocument
   :raises PygiXMLError: If parsing fails

   **Example:**

   .. code-block:: python

      import pygixml
      doc = pygixml.parse_string('<root>content</root>')
      print(doc.first_child().name)  # 'root'

.. py:function:: parse_file(file_path)

   Parse XML from file and return XMLDocument.

   :param str file_path: Path to XML file
   :return: Parsed XML document
   :rtype: XMLDocument
   :raises PygiXMLError: If parsing fails

   **Example:**

   .. code-block:: python

      import pygixml
      doc = pygixml.parse_file('data.xml')
      print(doc.first_child().name)  # 'root'

XMLDocument Class
-----------------

.. py:class:: XMLDocument()

   XML document wrapper providing document-level operations.

   This class represents an XML document and provides methods for loading,
   saving, and manipulating the document structure.

   **Methods:**

   .. py:method:: load_string(content)

      Load XML from string.

      :param str content: XML content as string
      :return: True if parsing succeeded, False otherwise
      :rtype: bool

      **Example:**

      .. code-block:: python

         doc = pygixml.XMLDocument()
         success = doc.load_string('<root>content</root>')
         print(success)  # True

   .. py:method:: load_file(path)

      Load XML from file.

      :param str path: Path to XML file
      :return: True if loading succeeded, False otherwise
      :rtype: bool

      **Example:**

      .. code-block:: python

         doc = pygixml.XMLDocument()
         success = doc.load_file('data.xml')
         print(success)  # True

   .. py:method:: save_file(path, indent="  ")

      Save XML to file.

      :param str path: Path where to save the file
      :param str indent: Indentation string (default: two spaces)

      **Example:**

      .. code-block:: python

         doc = pygixml.parse_string('<root>content</root>')
         doc.save_file('output.xml', indent='    ')

   .. py:method:: reset()

      Reset the document to empty state.

      Clears all content and resets the document to its initial state.

      **Example:**

      .. code-block:: python

         doc = pygixml.parse_string('<root>content</root>')
         doc.reset()  # Document is now empty

   .. py:method:: append_child(name)

      Append a child node to the document.

      :param str name: Name of the new element
      :return: The newly created node
      :rtype: XMLNode

      **Example:**

      .. code-block:: python

         doc = pygixml.XMLDocument()
         root = doc.append_child('root')
         item = root.append_child('item')

   .. py:method:: first_child()

      Get first child node of the document.

      :return: First child node or None if no children
      :rtype: XMLNode or None

      **Example:**

      .. code-block:: python

         doc = pygixml.parse_string('<root><child/></root>')
         first = doc.first_child()
         print(first.name)  # 'root'

   .. py:method:: child(name)

      Get child node by name.

      :param str name: Name of the child element to find
      :return: Child node with specified name or None if not found
      :rtype: XMLNode or None

      **Example:**

      .. code-block:: python

         doc = pygixml.parse_string('<root><item>value</item></root>')
         item = doc.child('item')
         print(item.text())  # 'value'

   .. py:method:: to_string(indent="  ")

      Serialize the document to XML string with custom indentation.

      :param str|int indent: Indentation string or number of spaces (default: two spaces)
      :return: XML content as string
      :rtype: str

      **Example:**

      .. code-block:: python

         doc = pygixml.parse_string('<root><item>value</item></root>')
         # Default indentation (2 spaces)
         xml_string = doc.to_string()
         # Custom string indentation
         xml_string = doc.to_string('    ')
         # Number of spaces
         xml_string = doc.to_string(4)

   .. py:method:: __iter__()

      Iterate over all nodes in the document.

      :return: Iterator of XMLNode objects in depth-first order
      :rtype: iterator

      **Example:**

      .. code-block:: python

         doc = pygixml.parse_string('<root><a><b/></a></root>')
         for node in doc:
             print(node.name)
         # Output: root, a, b

   **Example:**

   .. code-block:: python

      doc = pygixml.XMLDocument()
      root = doc.append_child("root")
      doc.save_file("output.xml")

XMLNode Class
-------------

.. py:class:: XMLNode()

   XML node wrapper providing node-level operations.

   This class represents an XML node and provides methods for accessing
   and manipulating node properties, children, attributes, and text content.

   **Properties:**

   .. py:attribute:: name

      Get node name.

      :return: Node name or None if no name
      :rtype: str or None

      **Example:**

      .. code-block:: python

         node = doc.first_child()
         print(node.name)  # 'root'

   .. py:attribute:: value

      Get node value.

      :return: Node value or None if no value
      :rtype: str or None

      **Example:**

      .. code-block:: python

         text_node = node.first_child()
         print(text_node.value)  # 'text content'

   .. py:attribute:: next_sibling

      Get next sibling node.

      :return: Next sibling XMLNode or None if no more siblings
      :rtype: XMLNode or None

   .. py:attribute:: previous_sibling

      Get previous sibling node.

      :return: Previous sibling XMLNode or None if no previous sibling
      :rtype: XMLNode or None

   .. py:attribute:: next_element_sibling

      Get next sibling that is an element node.

      :return: Next element sibling or None if no more element siblings
      :rtype: XMLNode or None

   .. py:attribute:: previous_element_sibling

      Get previous sibling that is an element node.

      :return: Previous element sibling or None if no previous element sibling
      :rtype: XMLNode or None

   .. py:attribute:: parent

      Get parent node.

      :return: Parent XMLNode or None if no parent
      :rtype: XMLNode or None

   .. py:attribute:: xpath

      Get the absolute XPath of this node.

      :return: XPath string (e.g., '/root/item[1]/name[1]')
      :rtype: str

      **Example:**

      .. code-block:: python

         node = doc.select_node('//item')
         print(node.xpath)  # '/root/item[1]'

   .. py:attribute:: xml

      Get XML representation with default indent (two spaces).

      :return: XML content as string
      :rtype: str

   .. py:attribute:: mem_id

      Get memory identifier for this node.

      :return: Memory address as integer
      :rtype: int

   **Methods:**

   .. py:method:: set_name(name)

      Set node name.

      :param str name: New name for the node
      :return: True if successful, False if node is null or invalid
      :rtype: bool

      **Example:**

      .. code-block:: python

         success = node.set_name('new_name')
         print(success)  # True

   .. py:method:: set_value(value)

      Set node value.

      :param str value: New value for the node
      :return: True if successful, False if node is null or invalid
      :rtype: bool

      **Example:**

      .. code-block:: python

         success = node.set_value('new value')
         print(success)  # True

   .. py:method:: first_child()

      Get first child node.

      :return: First child node or None if no children
      :rtype: XMLNode or None

      **Example:**

      .. code-block:: python

         root = doc.first_child()
         first_child = root.first_child()
         print(first_child.name)  # 'child'

   .. py:method:: child(name)

      Get child node by name.

      :param str name: Name of the child element to find
      :return: Child node with specified name or None if not found
      :rtype: XMLNode or None

      **Example:**

      .. code-block:: python

         root = doc.first_child()
         item = root.child('item')
         print(item.text())  # 'value'

   .. py:method:: append_child(name)

      Append a child node.

      :param str name: Name of the new child element
      :return: The newly created child node
      :rtype: XMLNode

      **Example:**

      .. code-block:: python

         root = doc.first_child()
         new_child = root.append_child('new_element')

   .. py:method:: child_value(name=None)

      Get child value.

      :param str name: Optional name of specific child element. 
                       If None, returns direct text content.
      :return: Text content or None if no content
      :rtype: str or None

      **Example:**

      .. code-block:: python

         # Get direct text content
         text = node.child_value()
         # Get text from specific child
         title = node.child_value('title')

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

   .. py:method:: is_null()

      Check if this node is null.

      :return: True if node is null
      :rtype: bool

   .. py:method:: to_string(indent="  ")

      Serialize this node to XML string with custom indentation.

      :param str|int indent: Indentation string or number of spaces (default: two spaces)
      :return: XML content as string
      :rtype: str

      **Example:**

      .. code-block:: python

         node = doc.first_child()
         # Default indentation (2 spaces)
         xml_string = node.to_string()
         # Custom string indentation
         xml_string = node.to_string('    ')
         # Number of spaces
         xml_string = node.to_string(4)

   .. py:method:: text(recursive=True, join="\n")

      Get the text content of this node.

      :param bool recursive: If True, get text from all descendants (default: True)
      :param str join: String to join multiple text nodes (default: newline)
      :return: Text content as string
      :rtype: str

      **Example:**

      .. code-block:: python

         # Get direct text content only
         text = node.text(recursive=False)
         # Get all text content with custom separator
         text = node.text(join=' ')

   .. py:method:: find_mem_id(mem_id)

      Find node by memory identifier.

      :param int mem_id: Memory identifier
      :return: XMLNode with matching memory identifier or None if not found
      :rtype: XMLNode or None

   .. py:method:: __iter__()

      Iterate over all descendant nodes in DFS preorder.

      :return: Iterator of XMLNode objects
      :rtype: iterator

      **Example:**

      .. code-block:: python

         for descendant in node:
             print(descendant.name)

   .. py:method:: __bool__()

      Check if node is not null.

      :return: True if node is not null
      :rtype: bool

   .. py:method:: __eq__(other)

      Compare two nodes for equality.

      :param XMLNode other: Other node to compare
      :return: True if nodes are equal
      :rtype: bool

   **Example:**

   .. code-block:: python

      import pygixml
      doc = pygixml.parse_string('<root><item>value</item></root>')
      root = doc.first_child()
      item = root.child('item')
      print(item.text())  # 'value'

XMLAttribute Class
------------------

.. py:class:: XMLAttribute()

   XML attribute wrapper providing attribute operations.

   This class represents an XML attribute and provides methods for accessing
   and manipulating attribute properties.

   **Properties:**

   .. py:attribute:: name

      Get attribute name.

      :return: Attribute name or None if no name
      :rtype: str or None

      **Example:**

      .. code-block:: python

         attr = node.attribute('id')
         print(attr.name)  # 'id'

   .. py:attribute:: value

      Get attribute value.

      :return: Attribute value or None if no value
      :rtype: str or None

      **Example:**

      .. code-block:: python

         attr = node.attribute('id')
         print(attr.value)  # '123'

   **Methods:**

   .. py:method:: set_name(name)

      Set attribute name.

      :param str name: New name for the attribute
      :return: True if successful, False if attribute is null or invalid
      :rtype: bool

      **Example:**

      .. code-block:: python

         success = attr.set_name('new_name')
         print(success)  # True

   .. py:method:: set_value(value)

      Set attribute value.

      :param str value: New value for the attribute
      :return: True if successful, False if attribute is null or invalid
      :rtype: bool

      **Example:**

      .. code-block:: python

         success = attr.set_value('new_value')
         print(success)  # True

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

      import pygixml
      doc = pygixml.parse_string('<root id="123" name="test"/>')
      root = doc.first_child()
      attr = root.attribute('id')
      print(attr.value)  # '123'

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

- ``parse_string()`` and ``parse_file()`` raise ``PygiXMLError`` for invalid XML
- ``save_file()`` may raise exceptions for file system errors
- Indexing operations on ``XPathNodeSet`` raise ``IndexError`` for out-of-range access
- Property setters (``name`` and ``value``) raise ``PygiXMLError`` for null or invalid nodes/attributes

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
