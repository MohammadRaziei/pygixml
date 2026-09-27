What is XML?
============

**XML** (eXtensible Markup Language) is a flexible, text-based format for
storing and transporting structured data.  It was defined by the World Wide
Web Consortium (`W3C <https://www.w3.org/XML/>`_) and first published as a
`W3C Recommendation <https://www.w3.org/TR/xml/>`_ on February 10, 1998.

For a comprehensive overview, see the `Wikipedia article on XML
<https://en.wikipedia.org/wiki/XML>`_.


Anatomy of an XML Document
--------------------------

A complete XML document contains several types of nodes.  Here is an example
with every major component labeled:

.. code-block:: xml

   <?xml version="1.0" encoding="UTF-8"?>                             <!-- (1) -->
   <!DOCTYPE library SYSTEM "library.dtd">                            <!-- (2) -->
   <library name="Central">                                           <!-- (3) -->
       <!-- This is a comment -->                                     <!-- (4) -->
       <book id="1" category="fiction">                               <!-- (5) -->
           <title>The Great Gatsby</title>                            <!-- (6) -->
           <author>F. Scott Fitzgerald</author>                       <!-- (7) -->
           <notes><![CDATA[Said to be <inspired> by real events]]></notes>  <!-- (8) -->
           <?custom-processor run-at="save"?>                         <!-- (9) -->
       </book>
       <book id="2"/>                                                 <!-- (10) -->
   </library>

Let's go through each numbered component:

(1) **XML Declaration** — ``<?xml version="1.0" encoding="UTF-8"?>``

    The optional first line that identifies the document as XML and
    specifies the version and character encoding.  If present, it must be
    the very first thing in the document.

(2) **DOCTYPE Declaration** — ``<!DOCTYPE library SYSTEM "library.dtd">``

    References a `Document Type Definition (DTD)
    <https://en.wikipedia.org/wiki/Document_type_definition>`_ that defines
    the allowed structure and elements.  An XML document that conforms to its
    DTD is called **valid**.

(3) **Root Element** — ``<library name="Central">``

    Every XML document has exactly one root (top-level) element that
    contains all other elements.  Elements can have **attributes**
    (``name="Central"``) which are key-value pairs.

(4) **Comments** — ``<!-- This is a comment -->``

    Human-readable annotations that parsers can optionally preserve or skip.
    Comments are never part of the data model for applications.

(5) **Element with Attributes** — ``<book id="1" category="fiction">``

    Elements are the building blocks of XML.  Each element has a tag name
    (``book``) and zero or more attributes (``id``, ``category``).

(6) **Text Node (PCDATA)** — ``The Great Gatsby``

    Parsed Character Data — the actual text content inside an element.
    "PCDATA" means the text is parsed, so entity references like ``&amp;``
    are expanded.

(7) **Child Element** — ``<author>`` inside ``<book>``

    Elements nest inside parent elements, forming a tree structure.

(8) **CDATA Section** — ``<![CDATA[...]]>``

    Character Data sections allow you to include text that would otherwise
    be treated as markup.  Inside CDATA, characters like ``<``, ``>``, and
    ``&`` lose their special meaning and are treated literally.

(9) **Processing Instruction (PI)** — ``<?custom-processor run-at="save"?>``

    Directives for applications processing the document.  They provide
    application-specific information that is not part of the XML data model.

(10) **Empty (Self-Closing) Element** — ``<book id="2"/>``

    An element with no content can be written as a self-closing tag with
    a trailing ``/>`` instead of a separate closing tag.


Elements
--------

Elements are containers that hold data.  Every element consists of:

* A **start tag** — ``<tagname>``
* Zero or more **attributes**
* **Content** — child elements, text, comments, etc.
* An **end tag** — ``</tagname>``

.. code-block:: xml

   <book id="1">          <!-- start tag with attribute -->
       <title>Gatsby</title>  <!-- child element -->
   </book>                <!-- end tag -->

**Empty elements** can use the shorthand syntax:

.. code-block:: xml

   <br/>                  <!-- self-closing -->
   <img src="photo.jpg"/>


Attributes
----------

Attributes are name-value pairs attached to elements:

.. code-block:: xml

   <book id="1" category="fiction" lang="en">

* Attribute names must be unique within an element
* Attribute values must always be quoted (single or double quotes)
* Order of attributes does not matter

**Entities** — special character references that can appear in attribute
values and text:

.. list-table::
   :header-rows: 1

   * - Entity
     - Renders As
   * - ``&amp;``
     - ``&``
   * - ``&lt;``
     - ``<``
   * - ``&gt;``
     - ``>``
   * - ``&quot;``
     - ``"``
   * - ``&apos;``
     - ``'``

Example: ``<tag attr="x &amp; y"/>`` renders as ``x & y``.


Text Nodes: PCDATA vs CDATA
---------------------------

PCDATA (Parsed Character Data)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The default mode for text content.  The parser **interprets** special
characters:

.. code-block:: xml

   <message>5 &lt; 10 &amp; 10 &gt; 3</message>

The parser sees: ``5 < 10 & 10 > 3``

CDATA (Character Data)
~~~~~~~~~~~~~~~~~~~~~~

A section where the parser treats everything as **literal text**.  No
entity processing, no markup recognition:

.. code-block:: xml

   <code><![CDATA[
       if (x < 10 && y > 3) {
           return x & y;
       }
   ]]></code>

The parser sees the text exactly as written — no escaping needed.
CDATA sections begin with ``<![CDATA[`` and end with ``]]>``.

**When to use CDATA:**

* Embedding code snippets (HTML, JavaScript, SQL)
* Including text that contains many ``<`` or ``&`` characters
* Avoiding the tedious process of escaping special characters

**When NOT to use CDATA:**

* When you need entity references to be expanded
* Inside attribute values (CDATA sections are only valid in element content)


Comments
--------

Comments are annotations ignored by applications:

.. code-block:: xml

   <!-- This is a comment -->
   <!--
       Multi-line comments
       are also supported
   -->

* Comments cannot appear inside attribute values
* Comments cannot be nested (``<!-- <!-- nested --> -->`` is invalid)
* The string ``--`` cannot appear inside a comment


Processing Instructions (PIs)
------------------------------

Processing instructions provide application-specific data:

.. code-block:: xml

   <?xml-stylesheet type="text/xsl" href="style.xsl"?>
   <?custom-app mode="debug"?>

* The **target** (e.g. ``xml-stylesheet``) identifies the application
* The **data** is passed as-is to that application
* PIs starting with ``xml`` (case-insensitive) are reserved for W3C use

See the `W3C specification on PIs
<https://www.w3.org/TR/xml/#sec-pi>`_.


Namespaces
----------

XML namespaces prevent name collisions when combining documents from
different vocabularies:

.. code-block:: xml

   <root xmlns:book="http://example.com/books"
         xmlns:store="http://example.com/store">
       <book:title>XML Guide</book:title>
       <store:title>Store Name Here</store:title>
   </root>

* ``xmlns:prefix="URI"`` declares a namespace
* Elements and attributes can be qualified with a prefix
* The **default namespace** (no prefix) applies to unprefixed elements:
  ``xmlns="http://example.com/default"``

See `W3C Namespaces in XML
<https://www.w3.org/TR/xml-names/>`_.


The XML Tree Model
------------------

An XML document is represented as a **DOM tree** (Document Object Model):

.. code-block:: text

   Document
   └── Element: library
       ├── Comment: "This is a comment"
       ├── Element: book  (id="1")
       │   ├── Element: title
       │   │   └── Text: "The Great Gatsby"
       │   └── Element: author
       │       └── Text: "F. Scott Fitzgerald"
       └── Element: book  (id="2")

Every node in the tree has a **type**:

===========  ==========================================================
Node Type    Description
===========  ==========================================================
Document     The root of the tree (the entire document)
Element      A tag like ``<book>`` or ``<title>``
Text         Character data inside an element
Comment      ``<!-- ... -->`` content
CDATA        Content inside a ``<![CDATA[...]]>`` section
PI           Processing instruction data
Declaration  The ``<?xml ...?>`` declaration
DOCTYPE      The ``<!DOCTYPE ...>`` declaration
===========  ==========================================================

In pygixml, you access the type via the ``node.type`` property.


XPath — Querying XML
--------------------

`XPath <https://en.wikipedia.org/wiki/XPath>`_ (XML Path Language) is a
query language for selecting nodes from an XML document.  It was developed
by the W3C and reached version 1.0 in November 1999.

XPath lets you navigate the tree using path expressions:

.. list-table::
   :header-rows: 1

   * - Expression
     - Meaning
   * - ``/library``
     - Root element ``library``
   * - ``/library/book``
     - All ``book`` children of ``library``
   * - ``//book``
     - All ``book`` elements anywhere in the document
   * - ``book[@id='1']``
     - ``book`` elements with ``id="1"``
   * - ``book[year > 1950]/title``
     - Titles of books published after 1950
   * - ``book[1]/author``
     - Author of the first book
   * - ``count(//book)``
     - Total number of books
   * - ``sum(book/price) div count(book)``
     - Average book price

pygixml supports the full XPath 1.0 specification.  The concepts above are
generic to any XML tooling; what follows is pygixml's own XPath API.

XPath Support
~~~~~~~~~~~~~

pygixml exposes pugixml's full XPath 1.0 engine.  Queries execute in C++ —
only the results you access cross the Python boundary.

Selection Methods
^^^^^^^^^^^^^^^^^

Two methods on :py:class:`~pygixml.XMLNode`:

.. list-table::
   :header-rows: 1

   * - Method
     - Returns
     - Empty match
   * - ``select_nodes(expr)``
     - :py:class:`~pygixml.XPathNodeSet` (iterable, ``len()``)
     - empty set
   * - ``select_node(expr)``
     - :py:class:`~pygixml.XPathNode` or ``None``
     - ``None``

.. code-block:: python

   import pygixml

   doc = pygixml.parse_string("""
   <library>
       <book id="1" category="fiction">
           <title>The Great Gatsby</title>
           <author>F. Scott Fitzgerald</author>
           <year>1925</year>
           <price>12.99</price>
       </book>
       <book id="2" category="non-fiction">
           <title>A Brief History of Time</title>
           <author>Stephen Hawking</author>
           <year>1988</year>
           <price>15.99</price>
       </book>
   </library>
   """)
   root = doc.root

   # Multiple matches
   books = root.select_nodes("book")
   print(f"Found {len(books)} books")    # Found 2 books

   # Single match
   book = root.select_node("book[@id='1']")
   if book:
       print(book.node.child("title").text())   # The Great Gatsby

   # Attribute filter
   fiction = root.select_nodes("book[@category='fiction']")
   for b in fiction:
       print(b.node.child("author").text())     # F. Scott Fitzgerald

Working with Results
^^^^^^^^^^^^^^^^^^^^

``select_nodes`` and ``select_node`` return **XPathNodeSet** and
**XPathNode** respectively.  Each ``XPathNode`` wraps either an
``XMLNode`` (``.node``) or an ``XMLAttribute`` (``.attribute``):

.. code-block:: python

   # XPathNodeSet — iterable
   for match in root.select_nodes("book/author"):
       print(match.node.text())

   # XPathNode — check for None
   match = root.select_node("book[@id='99']")
   if match:
       print("found")
   else:
       print("no match")

   # Selecting attributes returns XPathNode with .attribute
   for m in root.select_nodes("book/@id"):
       print(m.attribute.value)     # 1, 2

XPathQuery — Compile Once
^^^^^^^^^^^^^^^^^^^^^^^^^

Each call to ``select_nodes()`` parses and compiles the XPath string.
Use :py:class:`~pygixml.XPathQuery` when running the same query multiple
times:

.. code-block:: python

   # Compile once
   fiction_q = pygixml.XPathQuery("book[@category='fiction']")
   price_q   = pygixml.XPathQuery("book[price > 12]")

   # Evaluate many times
   fiction = fiction_q.evaluate_node_set(root)
   expensive = price_q.evaluate_node_set(root)

Typed Evaluations
"""""""""""""""""

``XPathQuery`` can return more than node sets.  Three typed methods:

.. code-block:: python

   # Boolean — does at least one book exist?
   pygixml.XPathQuery("book").evaluate_boolean(root)        # True

   pygixml.XPathQuery("book[price > 100]").evaluate_boolean(root)  # False

   # Number — count, sum, average
   pygixml.XPathQuery("count(book)").evaluate_number(root)         # 2.0
   pygixml.XPathQuery("sum(book/price)").evaluate_number(root)     # 28.98
   pygixml.XPathQuery("sum(book/price) div count(book)").evaluate_number(root)  # 14.49

   # String — first match as text
   pygixml.XPathQuery("book[1]/title").evaluate_string(root)       # The Great Gatsby
   pygixml.XPathQuery("concat(book[1]/title, ' by ', book[1]/author)").evaluate_string(root)
   # The Great Gatsby by F. Scott Fitzgerald

Common Patterns
^^^^^^^^^^^^^^^

.. code-block:: python

   # First / last / position
   root.select_node("book[1]")                     # first
   root.select_node("book[last()]")                # last
   root.select_nodes("book[position() <= 2]")      # first two

   # Text matching
   root.select_node("book[title='1984']")          # exact text
   root.select_nodes("book[contains(title, 'History')]")  # partial
   root.select_nodes("book[year < 1950]")          # numeric comparison

   # Multiple conditions
   root.select_nodes("book[@category='fiction' and year < 1950]")

   # Union of two node-sets
   root.select_nodes("book[@category='fiction'] | book[price > 14]")

   # Navigation — parent, siblings, descendants
   root.select_node("book[1]/title/..").node.name   # "book" (parent)
   root.select_nodes("book[1]/following-sibling::book")  # after first
   root.select_nodes("descendant::title")           # all titles at any depth

Supported Axes
^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - Axis
     - Shorthand
     - Example
   * - ``child``
     - (default)
     - ``book``
   * - ``attribute``
     - ``@``
     - ``@id``
   * - ``descendant``
     - ``//``
     - ``//title``
   * - ``descendant-or-self``
     - ``//``
     - ``.//title``
   * - ``parent``
     - ``..``
     - ``title/..``
   * - ``ancestor``
     - —
     - ``title/ancestor::library``
   * - ``ancestor-or-self``
     - —
     - ``title/ancestor-or-self::*``
   * - ``following-sibling``
     - —
     - ``book[1]/following-sibling::book``
   * - ``preceding-sibling``
     - —
     - ``book[3]/preceding-sibling::book``
   * - ``following``
     - —
     - ``book[1]/following::*``
   * - ``preceding``
     - —
     - ``book[3]/preceding::*``
   * - ``self``
     - ``.``
     - ``.``
   * - ``namespace``
     - —
     - ``namespace::*``

Supported Functions
^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - Category
     - Functions
   * - **Node-set**
     - ``position()``, ``last()``, ``count()``
   * - **String**
     - ``string()``, ``concat()``, ``contains()``,
       ``starts-with()``, ``substring()``, ``substring-before()``,
       ``substring-after()``, ``string-length()``, ``normalize-space()``,
       ``translate()``
   * - **Boolean**
     - ``boolean()``, ``not()``, ``true()``, ``false()``, ``lang()``
   * - **Number**
     - ``number()``, ``sum()``, ``floor()``, ``ceiling()``, ``round()``
   * - **Name**
     - ``name()``, ``local-name()``, ``namespace-uri()``

.. note::
   ``string-join()``, ``matches()`` (regex), and all XPath 2.0+ features are
   **not** available — pugixml implements XPath 1.0 only.

Performance
^^^^^^^^^^^

* **Use ``XPathQuery``** for repeated queries — compile once, evaluate many
  times.
* **Be specific** — ``library/book`` is faster than ``//book``.
* **Filter on attributes** — ``@id`` is faster than text comparison.
* **Limit results** — ``book[position() <= 10]`` beats fetching all and
  slicing in Python.


Well-Formed vs Valid XML
------------------------

**Well-formed** XML satisfies the basic syntactic rules:

* Every start tag has a matching end tag (or is self-closing)
* Elements are properly nested (no overlapping)
* Attribute values are quoted
* Exactly one root element
* Entity references are properly formed

**Valid** XML is well-formed **and** conforms to a DTD or XML Schema that
defines its allowed structure:

.. code-block:: xml

   <?xml version="1.0"?>
   <!DOCTYPE note [
     <!ELEMENT note (to,from,heading,body)>
     <!ELEMENT to     (#PCDATA)>
     <!ELEMENT from   (#PCDATA)>
     <!ELEMENT heading (#PCDATA)>
     <!ELEMENT body    (#PCDATA)>
   ]>
   <note>
       <to>Tove</to>
       <from>Jani</from>
       <heading>Reminder</heading>
       <body>Don't forget me this weekend!</body>
   </note>

.. note::
   pygixml checks for **well-formedness** only.  It does not validate
   against DTDs or XML Schemas.


Real-World Applications
-----------------------

XML is used in virtually every industry.  Key examples:

* **Web services** — `SOAP <https://en.wikipedia.org/wiki/SOAP>`_,
  `RSS <https://en.wikipedia.org/wiki/RSS>`_,
  `Atom <https://en.wikipedia.org/wiki/Atom_(web_standard)>`_
* **Office files** — ``.docx``, ``.xlsx``
  (`Office Open XML <https://en.wikipedia.org/wiki/Office_Open_XML>`_)
* **Vector graphics** — `SVG <https://en.wikipedia.org/wiki/SVG>`_
* **Build systems** — Maven (``pom.xml``), MSBuild (``.csproj``)
* **Configuration** — Android (``AndroidManifest.xml``), Spring, Apache
* **Scientific** — `MathML <https://en.wikipedia.org/wiki/MathML>`_,
  `SBML <https://en.wikipedia.org/wiki/SBML>`_
* **Documentation** — `DocBook <https://en.wikipedia.org/wiki/DocBook>`_,
  `DITA <https://en.wikipedia.org/wiki/Darwin_Information_Typing_Architecture>`_


Alternatives to XML
-------------------

* **JSON** — lighter syntax, dominant in web APIs
  (`RFC 8259 <https://datatracker.ietf.org/doc/html/rfc8259>`_)
* **YAML** — human-readable, used for configuration
  (`yaml.org <https://yaml.org/>`_)
* **Protocol Buffers** — binary serialization by Google
  (`protobuf <https://protobuf.dev/>`_)

XML's strengths remain: schema validation, namespaces, XPath/XQuery, and
mature tooling across all platforms.


See Also
--------

* `XML 1.0 Specification — W3C <https://www.w3.org/TR/xml/>`_
* `Namespaces in XML — W3C <https://www.w3.org/TR/xml-names/>`_
* `XPath 1.0 Specification — W3C <https://www.w3.org/TR/xpath-10/>`_
* `Wikipedia: XML <https://en.wikipedia.org/wiki/XML>`_
* `Wikipedia: XPath <https://en.wikipedia.org/wiki/XPath>`_
* `Wikipedia: CDATA <https://en.wikipedia.org/wiki/CDATA>`_
* `pugixml — C++ XML parser <https://pugixml.org/>`_
