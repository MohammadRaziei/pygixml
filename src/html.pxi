# html.pxi
# --------
# HTML <-> XML. All logic is C++ (html.hpp); every function here crosses the
# Python/C++ boundary exactly once: the text goes in, the result comes out,
# nothing is walked or built node-by-node from Python.
#
#   html_to_xml(html)            messy HTML -> well-formed XML text
#   parse_html(html)             messy HTML -> XMLDocument (one call, no
#                                intermediate Python string)
#   xml_to_html(node_or_doc)     XML tree   -> HTML text

cdef extern from "html.hpp" namespace "pygixml_html":
    string html_to_xml_cpp "pygixml_html::to_xml"(const string& html, const string& root) except +
    string xml_to_html_cpp "pygixml_html::to_html"(
        const xml_node& first, bint siblings, bint pretty, const string& indent,
        bint doctype, const char* unwrap) except +


class PygiXMLHTMLError(PygiXMLError):
    """Raised by the HTML helpers: input that isn't a ``str``, an empty
    wrapper name, normalised XML the parser rejects, or a null /
    unsupported node passed to :func:`xml_to_html`.  Subclass of
    :class:`PygiXMLError`.
    """
    pass


cdef string _normalise_html(html, str root) except *:
    if not isinstance(html, str):
        raise PygiXMLHTMLError(
            f"html must be str, not {type(html).__name__} (decode bytes first)"
        )
    if not root:
        raise PygiXMLHTMLError("root must be a non-empty element name")
    # "replace": a lone surrogate must not abort the whole conversion.
    cdef bytes data = (<str>html).encode("utf-8", "replace")
    return html_to_xml_cpp(data, root.encode("utf-8"))


def html_to_xml(html, str root="root"):
    """Convert HTML (possibly malformed, possibly a fragment) to a
    well-formed XML string.

    Output has exactly one root element. If the input already has exactly
    one top-level element (typically ``<html>``) it is used as is;
    otherwise everything is wrapped in ``<root>`` (name configurable via
    *root*).

    Names XML rejects are encoded reversibly (``o:p`` -> ``o_colon_p``,
    ``@click`` -> ``_at_click``) so :func:`xml_to_html` can restore them.

    Raises:
        PygiXMLHTMLError: *html* isn't a ``str`` (decode bytes first), or
            *root* is empty.
    """
    cdef string xml = _normalise_html(html, root)
    return xml.decode("utf-8")


def parse_html(html, str root="root", options=None):
    """Parse HTML into an :class:`~pygixml.XMLDocument` (see
    :func:`html_to_xml` for what is normalised and what is not).

    The whole conversion runs in C++ in a single call.

    *options* are the usual :class:`~pygixml.ParseFlags`. The default keeps
    whitespace-only text and comments (``DEFAULT | WS_PCDATA | COMMENTS``):
    in HTML the space in ``<b>a</b> <i>b</i>`` is content, and dropping
    comments would make :func:`xml_to_html` lose them.

    Raises:
        PygiXMLHTMLError: see :func:`html_to_xml`; also if the normalised
            XML is rejected by the XML parser.
    """
    cdef string xml = _normalise_html(html, root)
    cdef unsigned int opts = (parse_default | parse_ws_pcdata | parse_comments
                              if options is None else <unsigned int>options)
    cdef XMLDocument doc = XMLDocument()
    cdef bint ok
    if opts == 0xFFFFFFFF:
        ok = <bint>doc._doc.load_string(xml.c_str())
    else:
        ok = <bint>doc._doc.load_string(xml.c_str(), opts)
    if not ok:
        raise PygiXMLHTMLError("normalised HTML was rejected by the XML parser")
    return doc


def xml_to_html(node, bint pretty=False, indent="  ", bint doctype=False, unwrap=None):
    """Serialize an XML node or document as HTML (the inverse of
    :func:`parse_html`).

    Unlike ``to_string()`` this follows HTML rules: void tags are written
    ``<br>``, empty elements ``<div></div>`` (never ``<div/>``, which a
    browser reads as an open tag), ``<script>``/``<style>`` contents are
    not escaped, and names encoded by :func:`html_to_xml` are restored
    (``o_colon_p`` -> ``o:p``). Runs in a single C++ call.

    Args:
        node: an :class:`XMLNode` or :class:`XMLDocument`.
        pretty: indent block-level structure. Inline elements, text and
            ``<pre>``/``<textarea>``/``<script>``/``<style>`` are never
            re-indented, so rendering doesn't change.
        indent (str | int): indentation unit when *pretty* (a string, or a
            number of spaces).
        doctype: prepend ``<!DOCTYPE html>``.
        unwrap (str | None): if the only top-level element has this name
            (typically the ``"root"`` that :func:`html_to_xml` adds around
            fragments), emit only its children.

    Raises:
        PygiXMLHTMLError: *node* isn't a node/document, or is null.
    """
    cdef XMLNode n
    cdef XMLDocument d
    cdef string out
    cdef bytes ind, unw
    cdef const char* unw_c = NULL
    cdef xml_node_type t
    if isinstance(indent, int):
        indent = " " * indent
    ind = (<str>indent).encode("utf-8")
    if unwrap is not None:
        unw = (<str>unwrap).encode("utf-8")
        unw_c = unw
    if isinstance(node, XMLDocument):
        d = <XMLDocument>node
        out = xml_to_html_cpp(d._doc.first_child(), True, pretty, ind, doctype, unw_c)
    elif isinstance(node, XMLNode):
        n = <XMLNode>node
        t = n._node.type()
        if t == node_null:
            raise PygiXMLHTMLError("can't serialize a null node")
        if t == node_document:
            out = xml_to_html_cpp(n._node.first_child(), True, pretty, ind, doctype, unw_c)
        else:
            out = xml_to_html_cpp(n._node, False, pretty, ind, doctype, unw_c)
    else:
        raise PygiXMLHTMLError(
            f"expected XMLNode or XMLDocument, not {type(node).__name__}"
        )
    return out.decode("utf-8", "replace")
