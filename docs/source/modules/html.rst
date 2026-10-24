.. _html:

HTML Support
============

pygixml reads real-world (messy) HTML by first normalising it to
well-formed XML, then handing that to the normal pugixml parser. Because
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

From the shell, HTML is an input format of ``pygixml convert``::

   pygixml convert page.html --to json

What gets fixed
---------------

* void tags (``<br>``, ``<img>``, ...) are self-closed
* implicitly closed ``<p>``, ``<li>``, ``<dt>``/``<dd>``, ``<tr>``,
  ``<td>``/``<th>``, ``<tbody>``, ``<option>``, ... (nested lists and
  tables are left alone)
* stray end tags are ignored, unclosed tags are closed at the end
* valueless attributes (``disabled`` becomes ``disabled=""``) and duplicate
  attributes (the first one wins, as in browsers)
* entities such as ``&nbsp;`` and ``&copy;`` become real characters
* ``<script>`` / ``<style>`` contents are kept as raw text
* names XML rejects are made safe: ``@click`` becomes ``_click`` and
  ``o:p`` becomes ``o_p``
* comments containing ``--``, control characters, doctype and
  ``<?...?>`` instructions
* fragments with several top-level nodes (or top-level text) are wrapped in
  a ``<root>`` element; a single top-level element (usually ``<html>``) is
  used as is

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
