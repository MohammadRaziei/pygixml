.. _dictify:

dictify — XML to Dict
=====================

``pygixml.dictify`` converts XML to a nested Python ``dict``, fully
compatible with the `xmltodict <https://github.com/martinblech/xmltodict>`_
library.  Drop ``import xmltodict`` and replace it with
``from pygixml import dictify`` — the API is identical.

.. code-block:: python

   from pygixml import dictify

   xml = """
   <database name="users_db" version="1.2">
       <user-profile id="101" verified="true">
           <first_name>Mohammad</first_name>
           <balance>450.75</balance>
       </user-profile>
       <entry>Value A</entry>
       <entry>Value B</entry>
   </database>
   """

   d = dictify.parse(xml)
   # {
   #   'database': {
   #     '@name': 'users_db',
   #     '@version': '1.2',
   #     'user-profile': {
   #       '@id': '101', '@verified': 'true',
   #       'first_name': 'Mohammad', 'balance': '450.75'
   #     },
   #     'entry': ['Value A', 'Value B']
   #   }
   # }

   # Repeated siblings are automatically collapsed into a list
   d['database']['entry']      # ['Value A', 'Value B']

   # Attributes are prefixed with '@'
   d['database']['@name']      # 'users_db'

   # Convert back to XML
   xml_out = dictify.unparse(d, pretty=True)


Entry Points
------------

.. function:: pygixml.dictify.parse(xml, attr_prefix='@', cdata_key='#text', force_list=None, encoding=None)

   Parse an XML string into a nested dict.

   :param xml: XML source text.
   :type xml: str
   :param attr_prefix: Prefix prepended to attribute keys. Default ``"@"``.
   :type attr_prefix: str
   :param cdata_key: Key used for text content in mixed nodes. Default
      ``"#text"``.
   :type cdata_key: str
   :param force_list: Tag names that should always be wrapped in a list even
      when only one element exists.  Pass ``True`` to force all tags.
   :type force_list: set or True or None
   :param encoding: Accepted for API compatibility; ignored (pygixml
      auto-detects encoding).
   :returns: Parsed document as a nested dict.
   :rtype: dict
   :raises PygiXMLError: If the XML is malformed.

   .. code-block:: python

      # Default — attributes prefixed with '@'
      d = dictify.parse('<root id="1"><item>x</item></root>')
      # {'root': {'@id': '1', 'item': 'x'}}

      # Custom prefix
      d = dictify.parse('<root id="1">text</root>',
                        attr_prefix='', cdata_key='text')
      # {'root': {'id': '1', 'text': 'text'}}

      # Force single element into a list
      d = dictify.parse('<root><x>only</x></root>', force_list={'x'})
      # {'root': {'x': ['only']}}

.. function:: pygixml.dictify.parse_file(path, attr_prefix='@', cdata_key='#text', force_list=None)

   Parse an XML file into a nested dict.  Accepts the same keyword arguments
   as :func:`~pygixml.dictify.parse`.

   :param path: Filesystem path to the XML file.
   :type path: str
   :raises PygiXMLError: If the file cannot be read or the XML is malformed.

.. function:: pygixml.dictify.unparse(input_dict, output=None, encoding='utf-8', full_document='true', indent='\\t', attr_prefix='@', cdata_key='#text', pretty=False)

   Emit an XML string from a dict produced by :func:`~pygixml.dictify.parse`.

   :param input_dict: A ``{root_tag: value}`` dict.
   :type input_dict: dict
   :param encoding: Encoding declared in the XML header. Default ``"utf-8"``.
   :type encoding: str
   :param full_document: ``"true"`` to include the XML declaration line.
   :type full_document: str
   :param indent: Indentation string when *pretty* is ``True``. Default tab.
   :type indent: str
   :param attr_prefix: Prefix that identifies attribute keys. Default ``"@"``.
   :type attr_prefix: str
   :param cdata_key: Key holding text content. Default ``"#text"``.
   :type cdata_key: str
   :param pretty: Whether to indent output. Default ``False``.
   :type pretty: bool
   :returns: XML string.
   :rtype: str
   :raises ValueError: If *input_dict* does not have exactly one root key.

   .. code-block:: python

      d = {'root': {'@id': '1', 'item': ['a', 'b']}}
      print(dictify.unparse(d, pretty=True))
      # <?xml version="1.0" encoding="utf-8"?>
      # <root id="1">
      #     <item>a</item>
      #     <item>b</item>
      # </root>


Conversion Rules
----------------

The conversion rules match the ``xmltodict`` library exactly:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - XML structure
     - Dict representation
   * - ``<root/>`` (empty element)
     - ``{'root': None}``
   * - ``<root>text</root>``
     - ``{'root': 'text'}``
   * - ``<root>  </root>`` (whitespace only)
     - ``{'root': None}``
   * - ``<root id="1"/>``
     - ``{'root': {'@id': '1'}}``
   * - ``<root id="1">text</root>``
     - ``{'root': {'@id': '1', '#text': 'text'}}``
   * - ``<r><x>a</x><x>b</x></r>`` (repeated)
     - ``{'r': {'x': ['a', 'b']}}``
   * - ``<![CDATA[hello]]>``
     - Text content ``'hello'``

.. note::

   Unlike :mod:`pygixml.objectify`, ``dictify`` does **not** perform type
   inference — all values remain as strings, exactly as ``xmltodict`` behaves.
   This preserves round-trip fidelity with :func:`~pygixml.dictify.unparse`.


force_list
----------

By default, a tag that appears only once is stored as a scalar value.  Use
``force_list`` to always produce a list — useful when your code always expects
a list regardless of how many elements are present:

.. code-block:: python

   xml = '<catalog><item>only one</item></catalog>'

   # Without force_list — scalar
   d = dictify.parse(xml)
   d['catalog']['item']              # 'only one'  (str)

   # With force_list — always a list
   d = dictify.parse(xml, force_list={'item'})
   d['catalog']['item']              # ['only one']  (list)

   # Force ALL tags into lists
   d = dictify.parse(xml, force_list=True)
   d['catalog']['item']              # ['only one']


Round-trip
----------

:func:`~pygixml.dictify.parse` and :func:`~pygixml.dictify.unparse` are
round-trip compatible — parsing the output of ``unparse`` produces the same
dict:

.. code-block:: python

   original_xml = '<root id="1"><items><item>a</item><item>b</item></items></root>'

   d      = dictify.parse(original_xml)
   xml2   = dictify.unparse(d)
   d2     = dictify.parse(xml2)

   assert d == d2   # ✓


Comparison with objectify
-------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Feature
     - ``objectify``
     - ``dictify``
   * - Access style
     - ``root.user_profile.id``
     - ``d['root']['user-profile']['@id']``
   * - Type inference
     - Yes — ``int``, ``float``, ``bool``
     - No — all values are ``str``
   * - Repeated siblings
     - :class:`~pygixml.NodeSequence`, indexable
     - Python ``list``
   * - Memory
     - Wraps the live DOM — no copy
     - Full copy into Python dicts
   * - Best for
     - Navigating and reading XML
     - Serialising XML to JSON / passing to APIs
