.. _html:

HTML Support
============

pygixml reads real-world (messy) HTML by first normalising it to
well-formed XML, then handing that to the normal pugixml parser, and it can
write a tree back out as HTML. All of it runs in C++, and every call
crosses the Python/C++ boundary exactly once: the text goes in, the result
comes out, and nothing is walked or built node by node from Python. Because
the intermediate form is plain XML text, everything else in pygixml (XPath,
:doc:`objectify </modules/objectify>`, :doc:`dictify </modules/dictify>`,
:doc:`jsonify </modules/jsonify>`) works on HTML with no extra code.

.. code-block:: python

   import pygixml

   # 1. Parse straight to a DOM, then use XPath as usual
   doc = pygixml.parse_html("<ul><li>a<li>b<br></ul>")
   root = doc.first_child()
   print([n.node.child_value() for n in root.select_nodes("//li")])

   # 2. Or just get the XML text and feed it to anything
   pygixml.html_to_xml("<ul><li>a<li>b<br></ul>")
   # '<ul><li>a</li><li>b<br/></li></ul>'

   # 3. Combine with dictify / jsonify
   from pygixml import dictify
   dictify.parse(pygixml.html_to_xml(page))

   # 4. ...and back: edit the tree, write HTML
   for n in doc.root.select_nodes("//script"):
       n.node.parent.remove_child(n.node)
   print(doc.to_html(pretty=True, unwrap="root"))

From the shell, HTML is both an input and an output format of
``pygixml convert``::

   pygixml convert page.html --to json
   pygixml convert messy.html -o clean.html -p     # normalise + re-indent
   pygixml convert data.xml --to html

What gets fixed
---------------

* void tags (``<br>``, ``<img>``, ...) are self-closed
* implicitly closed ``<p>``, ``<li>``, ``<dt>``/``<dd>``, ``<tr>``,
  ``<td>``/``<th>``, ``<tbody>``, ``<option>``, ... (nested lists and
  tables are left alone)
* stray end tags are ignored, unclosed tags are closed at the end
* valueless attributes (``disabled`` becomes ``disabled=""``) and duplicate
  attributes (the first one wins, as in browsers)
* HTML5 character references (all 2231 named ones, legacy ones without a
  ``;``, numeric ones) become real characters. In attribute values a legacy
  reference followed by ``=`` or a letter is left alone, so ``?a=1&copy=2``
  stays a URL
* ``<script>`` / ``<style>`` contents are kept as raw text, and
  ``<title>`` / ``<textarea>`` contents are text (entities decoded, no tags
  inside), as in browsers
* ``\r\n`` and lone ``\r`` become ``\n``; the newline right after
  ``<pre>`` / ``<textarea>`` is dropped (and written back by
  ``xml_to_html``), exactly as the HTML spec says
* a tag cut off by the end of the input is dropped, as browsers do
* names XML rejects are mapped reversibly (see below)
* newlines and tabs inside attribute values are kept (XML parsers would
  otherwise turn them into spaces)
* comments containing ``--``, control characters, doctype and
  ``<?...?>`` instructions
* fragments with several top-level nodes (or top-level text) are wrapped in
  a ``<root>`` element; a single top-level element (usually ``<html>``) is
  used as is

Names XML can't hold
--------------------

Names such as ``o:p`` (a bare prefix breaks namespace-aware parsers) or
``@click`` are mapped, not dropped, and :func:`pygixml.xml_to_html` restores
them. The mapping is the SQL/XML one (ISO/IEC 9075-14, "Mapping SQL
identifiers to XML Names"; the same as PostgreSQL's and .NET's
``XmlConvert.EncodeName``), available on its own as
:func:`pygixml.encode_name` / :func:`pygixml.decode_name`. What counts as a
valid character follows the XML 1.0 name rules, so Unicode letters in names
are kept as they are:

.. list-table::
   :header-rows: 1

   * - HTML name
     - In the XML
   * - ``o:p``
     - ``o_x003A_p``
   * - ``@click``
     - ``_x0040_click``
   * - ``[prop]``
     - ``_x005B_prop_x005D_``
   * - ``1bad`` (attribute)
     - ``_x0031_bad``
   * - ``xml:lang``, ``xmlns``
     - ``_x0078_ml_x003A_lang``, ``_x0078_mlns``  (names starting with
       ``xml`` are reserved: the first letter is escaped)
   * - ``my_xvalue``
     - ``my_x005F_xvalue``  (``_`` before ``x`` is escaped, so a name can never
       be mistaken for an escape)

The mapping is one-to-one: ``xml_to_html`` always gets back what was there.
When an encoded name is hard to read, decode it::

    >>> doc = pygixml.parse_html("<o:p>t</o:p>")
    >>> doc.root.name
    'o_x003A_p'
    >>> pygixml.decode_name(doc.root.name)
    'o:p'

HTML names are case-insensitive, so the tokenizer lower-cases them first:
``@Click`` reaches the mapping as ``@click`` (and SVG's ``viewBox`` as
``viewbox``). ``encode_name`` itself keeps case.

Back to HTML
------------

:func:`pygixml.xml_to_html` (also ``node.to_html()`` and
``doc.to_html()``) follows HTML rules that ``to_string()`` does not:

* void tags are written ``<br>``, empty elements ``<div></div>`` (never
  ``<div/>``, which browsers treat as an *open* tag)
* ``<script>`` / ``<style>`` contents are not escaped (a literal ``</script``
  inside is written ``<\/script`` so it cannot close the element early)
* ``pretty=True`` only indents block-level structure. Inline elements, text
  and ``<pre>``/``<textarea>``/``<script>``/``<style>`` are never
  re-indented, so rendering does not change. Likewise no newline is added
  between top-level nodes if one of them is text or an inline element
* the walk is iterative, so a very deeply nested document cannot overflow
  the stack (20000 nested ``<div>`` is fine)
* ``unwrap="root"`` drops the wrapper that fragments get when parsed
* ``doctype=True`` prepends ``<!DOCTYPE html>``

``parse_html`` keeps whitespace-only text and comments by default (pass
``options=`` to change that), so a tree survives the trip:
``html_to_xml(xml_to_html(parse_html(x))) == html_to_xml(x)``. The output is
a normalised version of the input, not a byte-for-byte copy.

Errors
------

Everything raises :class:`pygixml.PygiXMLHTMLError`, a subclass of
:class:`pygixml.PygiXMLError`: input that is not ``str`` (decode bytes
first), an empty ``root`` name, normalised XML the parser rejects, or a null
or unsupported node given to ``xml_to_html``. HTML itself never fails to
tokenize: like a browser, the C++ tokenizer recovers from anything.

Limitations
-----------

This is **not** the HTML5 tree-building algorithm. There are no implied
``<html>``/``<head>``/``<body>`` elements, no browser-style table repair,
and tag and attribute names are lower-cased (SVG's ``viewBox`` arrives as
``viewbox``). That is fine for scraping and data extraction; if you need
browser-exact trees, use a spec-compliant HTML5 parser.

API
---

.. autofunction:: pygixml.html_to_xml

.. autofunction:: pygixml.parse_html

.. autofunction:: pygixml.xml_to_html

.. autofunction:: pygixml.encode_name

.. autofunction:: pygixml.decode_name

.. autoclass:: pygixml.XMLNameCodec
   :members:

.. autoexception:: pygixml.PygiXMLHTMLError
