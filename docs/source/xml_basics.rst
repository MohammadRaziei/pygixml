What is XML?
============

**XML** (eXtensible Markup Language) is a flexible, text-based format for
storing and transporting structured data.  It was defined by the World Wide
Web Consortium (`W3C <https://www.w3.org/XML/>`_) and first published as a
`W3C Recommendation <https://www.w3.org/TR/xml/>`_ on February 10, 1998.
The design goals of XML emphasize simplicity, generality, and usability
over the Internet.

For a comprehensive overview, see the `Wikipedia article on XML
<https://en.wikipedia.org/wiki/XML>`_.

XML is a simplified subset of `Standard Generalized Markup Language (SGML)
<https://en.wikipedia.org/wiki/SGML>`_ and was specifically designed to be
easy to implement while providing the full expressive power of SGML.


Document Structure
------------------

An XML document is a hierarchical tree of **elements**, **attributes**, and
**text nodes**:

.. code-block:: xml

   <?xml version="1.0" encoding="UTF-8"?>
   <library>
       <book id="1" category="fiction">
           <title>The Great Gatsby</title>
           <author>F. Scott Fitzgerald</author>
           <year>1925</year>
       </book>
   </library>

Each **element** (e.g. ``<book>``) may contain:

* **Attributes** — name-value pairs on the element itself (e.g. ``id="1"``)
* **Child elements** — nested elements (e.g. ``<title>``, ``<author>``)
* **Text nodes** — the actual content inside elements
* **Comments** — ``<!-- like this -->``
* **Processing Instructions** — ``<?target data?>``

Every XML document has exactly one **root element** (``<library>`` above)
that contains all other elements.

For the formal specification, see `XML 1.0 (Fifth Edition) — W3C
<https://www.w3.org/TR/xml/>`_.


Well-Formedness
---------------

An XML document is **well-formed** if it satisfies the syntactic rules of the
XML specification:

* Every start tag has a matching end tag (or is self-closing: ``<br/>``)
* Elements are properly nested (no overlapping tags)
* Attribute values are quoted
* There is exactly one root element

A document is **valid** if it is well-formed **and** conforms to a
`Document Type Definition (DTD) <https://en.wikipedia.org/wiki/Document_type_definition>`_
or `XML Schema <https://en.wikipedia.org/wiki/XML_schema_(W3C)>`_ that defines
its allowed structure.

.. note::
   pygixml checks for **well-formedness** only.  It does not validate
   against DTDs or XML Schemas.


XPath Query Language
--------------------

`XPath <https://en.wikipedia.org/wiki/XPath>`_ (XML Path Language) is a query
language for selecting nodes from an XML document.  It was developed by the
W3C and reached version 1.0 in 1999.  pygixml supports the full XPath 1.0
specification via pugixml's engine.

Example queries:

.. list-table::
   :header-rows: 1

   * - Expression
     - Meaning
   * - ``//book``
     - All ``<book>`` elements anywhere in the document
   * - ``/library/book``
     - All ``<book>`` elements that are direct children of ``<library>``
   * - ``book[@category='fiction']``
     - ``<book>`` elements with ``category="fiction"``
   * - ``book[year > 1950]/title``
     - Titles of books published after 1950
   * - ``sum(book/price) div count(book)``
     - Average book price
   * - ``book[1]/author``
     - Author of the first book

See :doc:`xpath` for a detailed guide.


Real-World Applications
-----------------------

XML is used in virtually every industry and domain.  Below are the most
common use cases.

Web Services & APIs
~~~~~~~~~~~~~~~~~~~

* **SOAP** — `Simple Object Access Protocol <https://en.wikipedia.org/wiki/SOAP>`_
  uses XML for message encoding
* **XML-RPC** — Remote procedure calls encoded in XML
* **RSS / Atom feeds** — `RSS <https://en.wikipedia.org/wiki/RSS>`_ and
  `Atom <https://en.wikipedia.org/wiki/Atom_(web_standard)>`_ syndication
  formats are XML-based
* **SVG** — `Scalable Vector Graphics <https://en.wikipedia.org/wiki/SVG>`_
  is an XML-based vector image format

Configuration Files
~~~~~~~~~~~~~~~~~~~

* **Maven** — ``pom.xml`` project configuration
* **Android** — ``AndroidManifest.xml``, layout resources
* **Spring Framework** — bean definitions and application context
* **.NET** — ``web.config``, ``app.config``
* **Apache** — ``server.xml``, ``web.xml`` deployment descriptors

Office Documents
~~~~~~~~~~~~~~~~

Modern office file formats are XML-based (zipped XML packages):

* **Microsoft Office** — ``.docx``, ``.xlsx``, ``.pptx``
  (`Office Open XML <https://en.wikipedia.org/wiki/Office_Open_XML>`_)
* **OpenDocument** — ``.odt``, ``.ods``, ``.odp``
  (`ODF <https://en.wikipedia.org/wiki/OpenDocument>`_)
* **EPUB** — e-book format built on XHTML/XML
  (`EPUB <https://en.wikipedia.org/wiki/EPUB>`_)

Scientific & Technical Data
~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **MathML** — `Mathematical Markup Language <https://en.wikipedia.org/wiki/MathML>`_
* **CML** — `Chemical Markup Language <https://en.wikipedia.org/wiki/Chemical_Markup_Language>`_
* **SBML** — `Systems Biology Markup Language <https://en.wikipedia.org/wiki/SBML>`_
* **KML** — `Keyhole Markup Language <https://en.wikipedia.org/wiki/Keyhole_Markup_Language>`_
  (used by Google Earth)

Documentation
~~~~~~~~~~~~~

* **DocBook** — `technical writing standard <https://en.wikipedia.org/wiki/DocBook>`_
* **DITA** — `Darwin Information Typing Architecture
  <https://en.wikipedia.org/wiki/Darwin_Information_Typing_Architecture>`_
* **XHTML** — HTML reformulated as XML
* **Sphinx / reStructuredText** — pygixml's own documentation is built with
  `Sphinx <https://www.sphinx-doc.org/>`_, which processes XML internally

Build Systems
~~~~~~~~~~~~~

* **Apache Ant** — XML-based build tool for Java
* **MSBuild** — ``.csproj`` / ``.vbproj`` project files
* **Maven** — dependency management and build lifecycle


Alternatives to XML
-------------------

While XML remains widely used, other data formats have gained popularity:

* **JSON** — lighter syntax, dominant in web APIs
  (`RFC 8259 <https://datatracker.ietf.org/doc/html/rfc8259>`_)
* **YAML** — human-readable, used for configuration
  (`yaml.org <https://yaml.org/>`_)
* **Protocol Buffers** — binary serialization by Google
  (`protobuf <https://protobuf.dev/>`_)

Each format has trade-offs in readability, tooling, and ecosystem support.
XML's strengths include schema validation, namespace support, and mature
querying (XPath/XQuery).


See Also
--------

* `XML Specification — W3C <https://www.w3.org/TR/xml/>`_
* `XPath Specification — W3C <https://www.w3.org/TR/xpath-10/>`_
* `Wikipedia: XML <https://en.wikipedia.org/wiki/XML>`_
* `Wikipedia: XPath <https://en.wikipedia.org/wiki/XPath>`_
* `pugixml — C++ XML parser <https://pugixml.org/>`_
* `Comparison of XML parsers <https://en.wikipedia.org/wiki/Comparison_of_XML_parsers>`_
