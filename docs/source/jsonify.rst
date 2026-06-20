.. _jsonify:

Jsonify — XML to JSON
======================

``pygixml.jsonify`` serializes XML directly to JSON. "Directly" is the
operative word: the in-memory entry points (:func:`~pygixml.jsonify.dumps`
and friends) traverse the pugixml DOM in C++ and write straight into a
JSON string buffer — no intermediate Python ``dict``/``list`` is ever
built, unlike going through :func:`pygixml.dictify.parse` followed by
:func:`json.dumps`. The streaming entry points
(:func:`~pygixml.jsonify.stream_dump`,
:func:`~pygixml.jsonify.stream_to_jsonl`) go a step further and skip
even the DOM, converting a giant XML *file* to a giant JSON *file* in
roughly constant memory.

The output shape matches :func:`pygixml.dictify.parse` exactly (same
``@``-prefixed attributes, ``#text`` for mixed content, repeated
siblings collapsed into arrays) — ``jsonify.dumps(xml)`` is equivalent
to, but faster than, ``json.dumps(dictify.parse(xml))``.

.. code-block:: python

   from pygixml import jsonify

   xml = """
   <database name="users_db">
       <user id="101">
           <name>Mohammad</name>
           <balance>450.75</balance>
       </user>
       <tag>active</tag>
       <tag>verified</tag>
   </database>
   """

   jsonify.dumps(xml)
   # '{"database": {"@name": "users_db", "user": {"@id": "101", ...}, "tag": ["active", "verified"]}}'

   jsonify.dumps(xml, pretty=True, indent="  ")   # multi-line, 2-space indent


In-memory entry points
------------------------

.. function:: pygixml.jsonify.dumps(source, attr_prefix="@", cdata_key="#text", force_list=None, pretty=False, indent="\\t", encoding="utf-8")
   :no-index:

   Smart dispatcher — serializes XML to JSON regardless of what form the
   XML is already in:

   * ``str`` starting with ``<``  →  parsed and serialized (same as
     :func:`~pygixml.jsonify.dumps_str`)
   * :class:`~pygixml.ObjectifiedElement`  →  serialized directly from
     the live DOM subtree (same as :func:`~pygixml.jsonify.dumps_obj`)
   * :class:`~pygixml.XMLNode`  →  serialized directly (same as
     :func:`~pygixml.jsonify.dumps_node`)

   :param source: XML string, an already-parsed
      :class:`~pygixml.ObjectifiedElement`, or an :class:`~pygixml.XMLNode`.
   :param attr_prefix: Prefix prepended to attribute keys. Default ``"@"``.
   :type attr_prefix: str
   :param cdata_key: Key used for text content in mixed nodes. Default
      ``"#text"``.
   :type cdata_key: str
   :param force_list: Tag names that should always be wrapped in a JSON
      array, even when only one sibling exists. Pass ``True`` to force
      every tag.
   :type force_list: set or True or None
   :param pretty: Indent the output. Default ``False`` (compact).
   :type pretty: bool
   :param indent: Indentation string used when ``pretty=True``. Default
      a tab.
   :type indent: str
   :returns: JSON string.
   :rtype: str
   :raises PygiXMLError: If the XML is malformed.
   :raises TypeError: If ``source``'s type isn't recognized.
   :raises ValueError: If ``source`` is a ``str`` that doesn't look like
      XML (file paths are rejected here on purpose — use
      :func:`~pygixml.jsonify.dumps_file` explicitly for files).

   .. note::
      File input is intentionally excluded from the dispatcher — call
      :func:`~pygixml.jsonify.dumps_file` directly for a path, so it's
      always unambiguous whether a ``str`` argument is XML content or a
      file path.

.. function:: pygixml.jsonify.dumps_str(xml, attr_prefix="@", cdata_key="#text", force_list=None, pretty=False, indent="\\t", encoding="utf-8")
   :no-index:

   Parse an XML *string* and serialize it directly to JSON.

   :param xml: XML source text.
   :type xml: str
   :returns: JSON string.
   :rtype: str
   :raises PygiXMLError: If the XML is malformed.

.. function:: pygixml.jsonify.dumps_file(path, attr_prefix="@", cdata_key="#text", force_list=None, pretty=False, indent="\\t", encoding="utf-8")
   :no-index:

   Parse an XML *file* and serialize it directly to JSON, returning the
   result as a ``str``. For files too big to hold as a JSON string in
   memory, see :func:`~pygixml.jsonify.stream_dump` instead.

   :param path: Filesystem path to the XML file.
   :type path: str
   :returns: JSON string.
   :rtype: str
   :raises PygiXMLError: If the file cannot be read or the XML is malformed.

.. function:: pygixml.jsonify.dumps_obj(elem, attr_prefix="@", cdata_key="#text", force_list=None, pretty=False, indent="\\t", encoding="utf-8")
   :no-index:

   Serialize an already-parsed :class:`~pygixml.ObjectifiedElement`
   subtree directly to JSON, without re-parsing or re-traversing as a
   dict first.

   :param elem: Element to serialize.
   :type elem: pygixml.ObjectifiedElement
   :returns: JSON string.
   :rtype: str
   :raises TypeError: If ``elem`` is not an ``ObjectifiedElement``.

   .. code-block:: python

      from pygixml import objectify, jsonify

      root = objectify.from_string(xml)
      jsonify.dumps_obj(root.user)            # just the <user> subtree

.. function:: pygixml.jsonify.dumps_node(node, attr_prefix="@", cdata_key="#text", force_list=None, pretty=False, indent="\\t", encoding="utf-8")
   :no-index:

   Serialize a low-level :class:`~pygixml.XMLNode` directly to JSON.

   :param node: Node to serialize.
   :type node: pygixml.XMLNode
   :returns: JSON string.
   :rtype: str
   :raises TypeError: If ``node`` is not an ``XMLNode``.


Streaming entry points: constant memory, files in and out
-------------------------------------------------------------

The functions above all hold the *result* (and, except for
``dumps_obj``/``dumps_node``, the parsed DOM too) in memory — fine for
documents that fit comfortably in RAM. For documents that don't,
``jsonify`` has two streaming converters that go file-to-file, entirely
in C++, with no pugixml DOM, no Python ``dict``/``list``/``str`` for
individual elements, and no ``json`` module anywhere in the call chain.

.. function:: pygixml.jsonify.stream_dump(xml_path, json_path, attr_prefix="@", cdata_key="#text", force_list=None, indent=0, stack_size=4096, io_buf_size=65536)
   :no-index:

   Convert a (potentially gigantic) XML **file** into a single,
   standard, valid JSON **file** — in roughly constant memory. Produces
   exactly what :func:`~pygixml.jsonify.dumps_file` would produce (one
   JSON value mirroring the whole document, loadable with a plain
   ``json.load``), just without ever holding the document, or the
   output, fully in memory.

   :param xml_path: Path to the input XML file.
   :type xml_path: str
   :param json_path: Path to the output JSON file. **Overwritten if it
      exists.**
   :type json_path: str
   :param attr_prefix: Prefix for XML attribute names in JSON keys.
      Default ``"@"``.
   :type attr_prefix: str
   :param cdata_key: JSON key used for text content mixed with
      attributes or child elements. Default ``"#text"``.
   :type cdata_key: str
   :param force_list: Tag names always serialized as a JSON array.
      ``True`` forces every tag. Default ``None`` (a tag becomes an
      array only once a second sibling with that name actually
      appears).
   :type force_list: set or True or None
   :param indent: Spaces per nesting level, same convention as
      ``json.dump(..., indent=N)``. ``0`` (default) is compact;
      any positive value pretty-prints.
   :type indent: int
   :param stack_size: Size in bytes of yxml's internal name stack.
   :type stack_size: int
   :param io_buf_size: Bytes read per XML I/O operation. Default 64 KB.
   :type io_buf_size: int
   :returns: Number of XML elements processed (informational).
   :rtype: int
   :raises PygiXMLError: On malformed XML, or if the input/output file
      cannot be opened.

   **How it stays constant-memory while still producing valid JSON
   syntax.** A JSON array needs to know, before its closing ``]``,
   whether more items follow — but the parser only finds that out when
   (and if) a second same-tag sibling actually shows up. Rather than
   buffer whole subtrees to be safe, the engine writes optimistically
   and *patches the output file in place* once it learns more:

   * The first time a child tag is seen under some parent, one
     placeholder byte is reserved right before its value, and the tag
     is written as a plain (non-array) value.
   * A second sibling with the same tag arrives → that placeholder byte
     is overwritten with ``[`` (an O(1) patch), and the new value is
     appended right after the first. This is the common case for
     record-oriented XML (same-tag siblings adjacent in the source) and
     never moves a single byte.
   * A *different* child tag is interleaved between two same-tag
     siblings → the engine splices: it shifts just the interleaved
     bytes forward (in small fixed-size chunks) to open a gap for the
     new sibling. Cost is proportional to how much was interleaved, not
     to the file size — and it's the only case where any data movement
     happens at all.

   .. code-block:: python

      from pygixml import jsonify
      import json

      jsonify.stream_dump("huge.xml", "huge.json")            # compact
      jsonify.stream_dump("huge.xml", "huge.json", indent=2)  # pretty

      with open("huge.json") as f:
          data = json.load(f)   # a single, ordinary, valid JSON document

.. function:: pygixml.jsonify.stream_to_jsonl(xml_path, jsonl_path, tag, attr_prefix="@", cdata_key="#text", force_list=None, stack_size=4096, io_buf_size=65536)
   :no-index:

   The per-record sibling of :func:`~pygixml.jsonify.stream_dump`:
   streams an XML **file** straight to a ``.jsonl`` **file**, one
   matched element per line, entirely in C++. Unlike
   :func:`~pygixml.jsonify.iterjsonl`, no
   :class:`~pygixml.StreamElement` and no Python
   ``str``/``dict``/``list`` is ever created for the matched elements
   themselves — each element's JSON object is assembled in a small
   in-memory buffer (bounded by that one element's own subtree, the
   same constant-memory model as :func:`~pygixml.iterfind`) and written
   straight to the file.

   :param xml_path: Path to the source XML file.
   :type xml_path: str
   :param jsonl_path: Path to the ``.jsonl`` file to write.
      **Overwritten if it exists.**
   :type jsonl_path: str
   :param tag: Tag name of the elements to convert and write, one per
      line.
   :type tag: str
   :param attr_prefix: Same meaning as :func:`~pygixml.jsonify.stream_dump`.
   :param cdata_key: Same meaning as :func:`~pygixml.jsonify.stream_dump`.
   :param force_list: Same meaning as :func:`~pygixml.jsonify.stream_dump`.
   :param stack_size: Size in bytes of yxml's internal name stack.
   :type stack_size: int
   :param io_buf_size: Bytes read per XML I/O operation. Default 64 KB.
   :type io_buf_size: int
   :returns: Number of matched elements written.
   :rtype: int
   :raises PygiXMLError: On malformed XML, or if the input/output file
      cannot be opened.

   .. note::
      If ``tag`` appears *nested inside* an already-matched element,
      that inner occurrence is folded into the outer match as an
      ordinary nested field (under its own tag-name key) rather than
      written as a second, separate line — only the outermost
      occurrence of a match starts a new JSONL record. This only
      matters for genuinely self-nested tags; a flat list of repeated
      sibling records (the common case) is unaffected.

   .. code-block:: python

      from pygixml import jsonify

      n = jsonify.stream_to_jsonl("huge.xml", "huge.jsonl", "record")
      print(f"wrote {n} records")

      import json
      with open("huge.jsonl") as f:
          for line in f:
              record = json.loads(line)   # each line is independent, valid JSON


Choosing the right entry point
---------------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - You have / want
     - In memory
     - Streamed (constant memory)
   * - Whole document → one JSON value
     - :func:`~pygixml.jsonify.dumps` /
       :func:`~pygixml.jsonify.dumps_file`
     - :func:`~pygixml.jsonify.stream_dump`
   * - One record per line, output as a ``.jsonl`` file
     - Loop + write yourself (see
       :func:`~pygixml.jsonify.iterjsonl`)
     - :func:`~pygixml.jsonify.stream_to_jsonl`
   * - One record per line, kept as Python ``str`` objects
     - :func:`~pygixml.jsonify.iterjsonl`
     - *(inherently produces a Python object per line — see*
       :doc:`streaming` *for the all-C++ alternative when that's not
       needed)*
   * - Already-parsed ``ObjectifiedElement`` / ``XMLNode``
     - :func:`~pygixml.jsonify.dumps_obj` /
       :func:`~pygixml.jsonify.dumps_node`
     - *(n/a — already in memory)*

See :doc:`streaming` for ``iterjsonl`` and the rest of the underlying
constant-memory parsing layer that ``stream_dump`` and
``stream_to_jsonl`` are built on top of.
