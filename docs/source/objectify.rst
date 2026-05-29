.. _objectify:

objectify — Dotted Navigation
==============================

``pygixml.objectify`` provides an `lxml.objectify
<https://lxml.de/objectify.html>`_-inspired interface that lets you navigate
XML with plain Python attribute access — no ``.child()`` or ``.attribute()``
calls needed.

.. code-block:: python

   from pygixml import objectify

   root = objectify.from_string("""
   <database name="users_db" version="1.2">
       <user-profile id="101" verified="true">
           <first_name>Mohammad</first_name>
           <balance>450.75</balance>
       </user-profile>
       <entry>Value A</entry>
       <entry>Value B</entry>
   </database>
   """)

   # Dotted navigation
   print(str(root.user_profile.first_name))   # 'Mohammad'
   print(root.version)                        # 1.2  (float)
   print(root.user_profile.id)               # 101  (int)
   print(root.user_profile.verified)         # True (bool)

   # Text content
   print(root.user_profile.balance())        # 450.75  (float)

   # Repeated siblings
   print([str(e) for e in root.entry])       # ['Value A', 'Value B']


Entry Points
------------

.. function:: pygixml.objectify.from_string(xml)

   Parse an XML string and return the root element as an
   :class:`~pygixml.ObjectifiedElement`.

   :param xml: XML source text.
   :type xml: str
   :returns: Document root element.
   :rtype: ObjectifiedElement
   :raises PygiXMLError: If the XML is malformed.

   .. code-block:: python

      root = objectify.from_string('<db ver="2"><item>x</item></db>')
      print(root.ver)        # 2  (int)
      print(str(root.item))  # 'x'

.. function:: pygixml.objectify.from_file(path)

   Parse an XML file and return the root element as an
   :class:`~pygixml.ObjectifiedElement`.

   :param path: Filesystem path to the XML file.
   :type path: str
   :returns: Document root element.
   :rtype: ObjectifiedElement
   :raises PygiXMLError: If the file cannot be read or the XML is malformed.

   .. code-block:: python

      root = objectify.from_file("config.xml")
      print(root.server.host)


ObjectifiedElement
------------------

.. class:: pygixml.ObjectifiedElement

   Wraps a single XML element node and provides attribute-style navigation.

   Stores the underlying pugixml ``xml_node`` struct directly as a C-level
   field — no Python wrapper is allocated per access.  A ``_doc_ref`` slot
   keeps the owning :class:`~pygixml.XMLDocument` alive for the lifetime of
   the wrapper.

   .. rubric:: Navigation

   .. describe:: elem.child_tag

      Returns the first child element named ``child_tag``.  If not found,
      automatically retries with hyphens replacing underscores
      (``elem.user_profile`` → ``<user-profile>``).

      When multiple direct siblings share the same tag, a
      :class:`~pygixml.NodeSequence` is returned instead of a single element.

      Child elements take priority over same-named attributes.

   .. describe:: elem.attr_name

      Returns the type-inferred value of attribute ``attr_name`` when no
      child element with that name exists.  Underscores are also mapped to
      hyphens (``elem.data_id`` → ``data-id``).

   .. method:: get(name, default=None)

      Return the value of attribute *name*, or *default* if absent.  Never
      raises — behaves like ``dict.get()``.  Only attributes are searched;
      child elements are not considered.

      :param name: Attribute name (underscores map to hyphens).
      :type name: str
      :param default: Returned when the attribute is absent.
      :returns: Type-inferred attribute value, or *default*.

      .. code-block:: python

         root = objectify.from_string('<user id="42" active="true"/>')
         root.get('id')           # 42
         root.get('missing')      # None
         root.get('missing', -1)  # -1

   .. method:: find(tag, recursive=True)

      Return the first descendant element whose tag matches *tag*, or
      ``None`` if not found.  Direct children are checked first; recursion
      follows when *recursive* is ``True``.

      :param tag: Tag name to search for (underscores map to hyphens).
      :type tag: str
      :param recursive: Search all descendants (default ``True``), or only
         direct children (``False``).
      :type recursive: bool
      :returns: First matching element, or ``None``.
      :rtype: ObjectifiedElement or None

      .. code-block:: python

         root = objectify.from_string(
             '<root><a><b><target>found</target></b></a></root>')

         root.find('target')                    # ObjectifiedElement
         root.find('target', recursive=False)   # None

   .. method:: findall(tag, recursive=True)

      Return all descendant elements whose tag matches *tag*, in document
      order.

      :param tag: Tag name to search for (underscores map to hyphens).
      :type tag: str
      :param recursive: Search all descendants (default ``True``), or only
         direct children (``False``).
      :type recursive: bool
      :returns: All matching elements (may be empty).
      :rtype: list[ObjectifiedElement]

      .. code-block:: python

         root = objectify.from_string("""
         <root>
           <item>a</item>
           <group><item>b</item></group>
           <item>c</item>
         </root>""")

         root.findall('item')                   # [a, b, c]
         root.findall('item', recursive=False)  # [a, c]

   .. rubric:: Text access

   .. method:: __call__()

      Return the type-inferred text content of this node (``int``,
      ``float``, ``bool``, or ``str``).  Returns ``None`` for empty or
      structural nodes.

      .. code-block:: python

         root.user_profile.balance()   # 450.75  (float)
         root.user_profile.first_name() # 'Mohammad'

   .. method:: __str__()

      Return the raw text content as a plain ``str``.  Always returns a
      string — never raises.

      .. code-block:: python

         str(root.user_profile.first_name)   # 'Mohammad'

   .. rubric:: Sequence protocol

   .. method:: __iter__()

      Iterate over direct child element nodes.

   .. method:: __len__()

      Number of direct child element nodes.

   .. method:: __bool__()

      ``False`` only for a null (empty) node.

   .. rubric:: Properties

   .. attribute:: tag

      The XML tag name of this element (``str``).

   .. attribute:: text_content

      Raw text content, always a ``str``.

   .. attribute:: attrib

      All attributes as a ``{name: typed_value}`` dict.  Values are
      type-inferred (``bool`` / ``int`` / ``float`` / ``str``).

      .. code-block:: python

         root.user_profile.attrib
         # {'id': 101, 'verified': True}

   .. attribute:: xml

      Serialised XML of this node and its subtree.


NodeSequence
------------

.. class:: pygixml.NodeSequence

   A sequence of :class:`~pygixml.ObjectifiedElement` siblings that share a
   tag name.  Returned by attribute access when multiple direct siblings with
   the same tag exist.

   Supports integer indexing (including negative), ``len()``, and iteration.
   When exactly one element is present, calling or ``str()``-ing the sequence
   delegates to that sole item for convenience.

   .. code-block:: python

      entries = root.entry           # NodeSequence  (3 items)
      entries[0]                     # ObjectifiedElement
      entries[-1]                    # last entry
      [str(e) for e in entries]      # ['Value A', 'Value B', 'Value C']
      len(entries)                   # 3


Type Inference
--------------

Attribute values and leaf-node text are automatically converted to the most
specific Python type:

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - XML value
     - Python type
     - Example
   * - ``"true"`` / ``"false"`` (any case)
     - ``bool``
     - ``verified="true"`` → ``True``
   * - Integer string
     - ``int``
     - ``id="101"`` → ``101``
   * - Decimal / scientific string
     - ``float``
     - ``version="1.2"`` → ``1.2``
   * - Everything else
     - ``str``
     - ``name="users_db"`` → ``"users_db"``

.. note::

   Type inference applies to **both** attribute values (via ``elem.attr``) and
   leaf-node text content (via ``elem()``).  ``str(elem)`` always returns a
   plain ``str`` without inference.


Identifier Mapping
------------------

XML tag names and attribute names often contain hyphens (``user-profile``,
``data-id``), which are illegal in Python identifiers.  pygixml automatically
maps underscores to hyphens as a fallback:

1. The exact Python name is tried first (``user_profile`` → looks for
   ``<user_profile>``).
2. If not found, the hyphenated form is tried (``user_profile`` →
   ``<user-profile>``).

This means a tag that *literally* contains an underscore wins over a
hyphenated equivalent:

.. code-block:: python

   xml = "<root><a_b>underscore</a_b><a-b>hyphen</a-b></root>"
   r = objectify.from_string(xml)
   str(r.a_b)   # 'underscore'  ← literal underscore tag wins


Priority Rules
--------------

When a name exists as **both** a child element tag and an attribute name, the
child element always wins:

.. code-block:: python

   xml = '<root name="attr"><name>child</name></root>'
   r = objectify.from_string(xml)
   r.name              # ObjectifiedElement(<name>)  ← child wins
   r.attrib['name']    # 'attr'  ← attribute via .attrib
   r.get('name')       # 'attr'  ← attribute via .get()


Performance Notes
-----------------

* :class:`~pygixml.ObjectifiedElement` and :class:`~pygixml.NodeSequence`
  are ``cdef class`` objects compiled into ``pygixml_cy.so`` — no pure-Python
  overhead.
* ``_node`` holds the ``xml_node`` C struct directly; no intermediate Python
  :class:`~pygixml.XMLNode` wrapper is allocated per access.
* Child lookup, attribute lookup, and sibling collection all operate at the
  C++ level via direct pugixml API calls.
* ``_doc_ref`` is the only Python-level field — it keeps the
  :class:`~pygixml.XMLDocument` alive and prevents premature GC of the
  underlying pugixml memory pool.
