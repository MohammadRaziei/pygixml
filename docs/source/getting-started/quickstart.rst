Quick Start
===========

A five-minute tour of pygixml: parse a string, read a value, and save it back
out. For the full picture (navigating, XPath, streaming, the higher-level
modules), see the pages linked in Next Steps below.

.. code-block:: python

   import pygixml

   xml = '''
   <library>
       <book id="1" category="fiction">
           <title>The Great Gatsby</title>
           <author>F. Scott Fitzgerald</author>
           <year>1925</year>
       </book>
   </library>
   '''

   doc = pygixml.parse_string(xml)
   root = doc.root

   book = root.child("book")
   print(book.attribute("id").value)        # 1
   print(book.child("title").text())        # The Great Gatsby

   # Create and save
   doc = pygixml.XMLDocument()
   root = doc.append_child("catalog")
   root.append_child("item").set_value("Hello")
   doc.save_file("output.xml")

.. tip::
   Use :py:class:`~pygixml.ParseFlags` to control parsing speed vs strictness.
   ``ParseFlags.MINIMAL`` skips escape processing and whitespace handling for
   maximum throughput. See :ref:`Parse Flags <parse-flags>` for details.

Next Steps
----------

- Learn the full DOM API: navigating, iterating, creating, modifying, and
  XPath, in :doc:`/core/dom-parser`
- Reading huge files without loading them whole: :doc:`/core/stream-parser`
- Dotted-navigation, dict, and JSON views of the same tree, in
  :doc:`/modules/objectify`, :doc:`/modules/dictify`, and
  :doc:`/modules/jsonify`
- The command-line tools, in :doc:`/cli`
- Practical, runnable examples, in :doc:`/examples`
- The full :doc:`API reference </reference/api>`
- How fast this all actually is: :doc:`/performance`
