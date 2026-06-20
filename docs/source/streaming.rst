.. _streaming:

Streaming — Constant-Memory Parsing for Big XML
================================================

Everything covered so far (:doc:`objectify`, :doc:`dictify`, XPath) is built
on pugixml's in-memory DOM — fast, but the whole document has to fit in
RAM. ``pygixml``'s streaming layer is a second, independent engine: a
self-contained, inlined `yxml <https://dev.yorhel.nl/yxml>`_ push parser
that reads an XML file (or string, or file-like object) one chunk at a
time and lets you process matching elements **without ever holding the
full document in memory**. This is the layer to reach for once a file is
too big — or you simply don't want — to load whole.

.. code-block:: python

   import pygixml

   for record in pygixml.iterfind("big.xml", "record"):
       print(record.tag, record.get("id"), record.find("name").text)
       record.clear()      # drop this element's memory before the next one

Three layers build on top of each other, from lowest- to highest-level:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Function
     - What it gives you
   * - :func:`pygixml.iterparse`
     - ``(event, elem)`` pairs, ``ElementTree``-style — full control
   * - :func:`pygixml.iterfind`
     - Just the matched :class:`~pygixml.StreamElement` objects
   * - :func:`pygixml.dictify.iterdict` / :func:`pygixml.jsonify.iterjsonl`
     - Each match already converted to a ``dict`` / JSON ``str``

And for the common "convert the whole file" case, :mod:`pygixml.jsonify`
adds two endpoints that skip Python objects entirely and write straight
to disk — see :doc:`jsonify`.


``iterparse`` / ``iterfind``
-----------------------------

.. function:: pygixml.iterparse(source, events=("end",), tag=None, stack_size=4096, chunk_size=65536)
   :no-index:

   An incremental, ``ElementTree``-style parser. Reads ``source`` in
   ``chunk_size``-byte chunks and yields ``(event, elem)`` tuples as
   elements start and/or end, without ever building a full document
   tree.

   :param source: A path, ``bytes``/``bytearray`` of XML content, or any
      file-like object with ``.read()``.
   :type source: str or os.PathLike or bytes or bytearray or file-like
   :param events: Which events to yield: ``"start"``, ``"end"``, or both.
      Only ``"end"`` events carry a fully-populated element (children,
      text, attributes); a ``"start"`` event's element has its tag and
      attributes but no children or text yet.
   :type events: tuple[str, ...]
   :param tag: If given, only elements with this tag name produce
      events — everything else is skipped without allocating a
      :class:`~pygixml.StreamElement` for it.
   :type tag: str or None
   :param stack_size: Size (bytes) of yxml's internal element/attribute
      name stack. Increase this only if you hit a "stack too small"
      parse error on documents with unusually deep nesting or very long
      tag/attribute names.
   :type stack_size: int
   :param chunk_size: Bytes read per I/O operation from ``source``.
   :type chunk_size: int
   :returns: A generator of ``(event, elem)`` tuples.
   :rtype: Iterator[tuple[str, pygixml.StreamElement]]
   :raises PygiXMLError: On malformed XML.

   .. code-block:: python

      import pygixml

      for event, elem in pygixml.iterparse("big.xml", events=("start", "end")):
          if event == "start" and elem.tag == "record":
              print("entering record", elem.get("id"))
          elif event == "end" and elem.tag == "record":
              handle(elem)
              elem.clear()

.. function:: pygixml.iterfind(source, tag, stack_size=4096, chunk_size=65536)
   :no-index:

   Shortcut for ``pygixml.iterparse(source, events=("end",), tag=tag)`` that
   yields :class:`~pygixml.StreamElement` objects directly — no
   ``(event, elem)`` tuple to unpack.

   :param source: Same as :func:`~pygixml.iterparse`.
   :param tag: Tag name of the elements to yield. Matches at any depth,
      including nested occurrences of the same tag.
   :type tag: str
   :returns: A generator of matched elements.
   :rtype: Iterator[pygixml.StreamElement]

   .. code-block:: python

      for record in pygixml.iterfind("big.xml", "record"):
          handle(record)
          record.clear()


``StreamElement``
------------------

.. class:: pygixml.StreamElement
   :no-index:

   A small, ``ElementTree``-like element produced while streaming. It is
   **not** connected to a pugixml document — it's a standalone tree of
   plain Python objects (built once, for this one match, then thrown
   away), with a ``tag``, an ``attrib`` dict, optional ``text``/``tail``
   strings, and child ``StreamElement`` nodes.

   .. attribute:: tag
      :type: str
      :no-index:

   .. attribute:: attrib
      :type: dict
      :no-index:

   .. attribute:: text
      :type: str or None
      :no-index:

   .. attribute:: tail
      :type: str or None
      :no-index:

   .. attribute:: children
      :type: list[pygixml.StreamElement]
      :no-index:

      Direct children. Also available via iteration (``for child in
      elem``), indexing (``elem[0]``), and ``len(elem)``.

   .. method:: get(key, default=None)
      :no-index:

      ``attrib.get(key, default)``.

   .. method:: find(path)
      :no-index:

      First descendant matching ``path``, or ``None``. ``path`` supports
      ``"tag"``, ``"a/b/c"`` (direct-child traversal), ``"*"`` (any
      child), and ``".//tag"`` (any descendant).

   .. method:: findall(path)
      :no-index:

      All descendants matching ``path`` (same syntax as :meth:`find`).
      Always returns a list, possibly empty.

   .. method:: findtext(path, default=None)
      :no-index:

      ``.text`` of the first match of ``path``, or *default*.

   .. method:: iter(tag=None)
      :no-index:

      Depth-first iterator over this element and all its descendants,
      optionally restricted to ``tag``.

   .. method:: clear()
      :no-index:

      Drop this element's attributes, text, tail, and children, freeing
      the memory they hold. **Call this after processing each element**
      yielded by :func:`~pygixml.iterfind` — it's what keeps peak memory
      flat across millions of elements.

   .. method:: to_dict(attr_prefix="@", cdata_key="#text", force_list=None)
      :no-index:

      Convert this element (and its subtree) to a plain ``dict``, using
      the exact same conventions as :func:`pygixml.dictify.parse`
      (``@``-prefixed attributes, ``#text`` for mixed content, repeated
      siblings collapsed into a list).

   .. method:: to_json(attr_prefix="@", cdata_key="#text", force_list=None)
      :no-index:

      Same conversion as :meth:`to_dict`, returned as a JSON ``str``
      instead of a ``dict``.

   .. code-block:: python

      for record in pygixml.iterfind("big.xml", "record"):
          d = record.to_dict()              # {'@id': '1', 'name': 'Ali', ...}
          line = record.to_json()           # '{"@id": "1", "name": "Ali", ...}'
          record.clear()


Streaming straight to ``dict`` or JSON
---------------------------------------

Wrapping every loop in ``elem.to_dict()`` / ``elem.to_json()`` /
``elem.clear()`` is common enough to have its own generators:

.. function:: pygixml.dictify.iterdict(source, tag, attr_prefix="@", cdata_key="#text", force_list=None, stack_size=4096, chunk_size=65536)
   :no-index:

   Generator yielding :meth:`~pygixml.StreamElement.to_dict` for every
   element matching ``tag``, clearing each one automatically once
   converted. Identical to looping over :func:`~pygixml.iterfind`
   yourself, just shorter.

   .. code-block:: python

      from pygixml import dictify

      for record in dictify.iterdict("big.xml", "record"):
          print(record["@id"], record["name"])     # plain dict, no XML API

.. function:: pygixml.jsonify.iterjsonl(source, tag, attr_prefix="@", cdata_key="#text", force_list=None, stack_size=4096, chunk_size=65536)
   :no-index:

   Generator yielding :meth:`~pygixml.StreamElement.to_json` (one JSON
   object string per match) for every element matching ``tag``. Each
   yielded line is independently parseable JSON — write them to a
   ``.jsonl`` file yourself, forward them over a socket, push them onto
   a queue, whatever fits:

   .. code-block:: python

      from pygixml import jsonify

      with open("big.jsonl", "w") as f:
          for line in jsonify.iterjsonl("big.xml", "record"):
              f.write(line + "\n")

   If the destination really is just a ``.jsonl`` file and you don't
   need the records in Python at all, :func:`pygixml.jsonify.stream_to_jsonl`
   does the same job without creating a single Python object per
   element — see :doc:`jsonify`.


Sources accepted everywhere
----------------------------

:func:`~pygixml.iterparse`, :func:`~pygixml.iterfind`,
:func:`~pygixml.dictify.iterdict`, and :func:`~pygixml.jsonify.iterjsonl`
all accept the same set of ``source`` types:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Type
     - Behavior
   * - ``str`` / ``os.PathLike``
     - Treated as a filesystem path and opened for reading.
   * - ``bytes`` / ``bytearray``
     - Treated as XML *content* (not a path) and read from memory.
   * - File-like object
     - Anything with a ``.read()`` method — sockets, ``io.BytesIO``,
       already-open file handles, decompression streams, etc.

.. note::
   A plain ``str`` is always treated as a **path**, never as XML content
   — pass ``bytes`` (e.g. ``xml.encode()``) if you have an XML string in
   memory and want to stream it without writing it to a file first.


Memory model
------------

Peak memory while streaming is bounded by the size of **one matched
element's own subtree**, not the document. A 10 GB XML file with
millions of small, flat ``<record>`` elements streams in roughly the
same peak memory as a 10 KB one — only the *time* scales with the file
size, not the memory.

.. code-block:: python

   import pygixml

   n, total_score = 0, 0
   for record in pygixml.iterfind("huge_export.xml", "record"):
       n += 1
       total_score += int(record.findtext("score", "0"))
       record.clear()

   print(f"{n} records, average score {total_score / n:.1f}")
   # peak memory: roughly constant, regardless of how big huge_export.xml is
