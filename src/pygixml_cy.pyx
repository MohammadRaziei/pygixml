# distutils: language = c++
# cython: language_level=3

"""
Python wrapper for pugixml using Cython
"""

from libcpp.string cimport string
from libcpp.vector cimport vector
from libcpp cimport bool

# Import pugixml headers
cdef extern from "pugixml.hpp" namespace "pugi":
    # Parse flags
    const unsigned int parse_minimal
    const unsigned int parse_pi
    const unsigned int parse_comments
    const unsigned int parse_cdata
    const unsigned int parse_ws_pcdata
    const unsigned int parse_escapes
    const unsigned int parse_eol
    const unsigned int parse_wconv_attribute
    const unsigned int parse_wnorm_attribute
    const unsigned int parse_declaration
    const unsigned int parse_doctype
    const unsigned int parse_ws_pcdata_single
    const unsigned int parse_trim_pcdata
    const unsigned int parse_fragment
    const unsigned int parse_embed_pcdata
    const unsigned int parse_merge_pcdata
    const unsigned int parse_default
    const unsigned int parse_full

    cdef cppclass xml_parse_result:
        bool operator bool() const
        const char* description() const

    cdef cppclass xml_document:
        xml_document() except +
        xml_node append_child(const char* name)
        xml_node prepend_child(const char* name)
        xml_node first_child()
        xml_node last_child()
        xml_node child(const char* name)
        xml_parse_result load_string(const char* contents, unsigned int options)
        xml_parse_result load_file(const char* path, unsigned int options)
        # Keep the original default-arg overloads
        xml_parse_result load_string(const char* contents)
        xml_parse_result load_file(const char* path)
        void save_file(const char* path, const char* indent) except +
        void reset()
        
    cdef cppclass xml_node:
        xml_node() except +
        xml_node_type type() const
        string name() const
        string value() const
        xml_node first_child()
        xml_node last_child()
        xml_node child(const char* name)
        xml_node next_sibling()
        xml_node previous_sibling()
        xml_node parent()
        xml_attribute first_attribute()
        xml_attribute last_attribute()
        xml_attribute attribute(const char* name)
        xml_node append_child(const char* name)
        xml_node prepend_child(const char* name)
        xml_node append_child(xml_node_type type)
        xml_node prepend_child(xml_node_type type)
        xml_node insert_child_before(const char* name, const xml_node& node)
        xml_node insert_child_after(const char* name, const xml_node& node)
        xml_attribute append_attribute(const char* name)
        xml_attribute prepend_attribute(const char* name)
        bool remove_child(const xml_node& node)
        bool remove_attribute(const xml_attribute& attr)
        string child_value() const
        string child_value(const char* name) const
        bool set_name(const char* name)
        bool set_value(const char* value)
        xpath_node select_node(const char* query, xpath_variable_set* variables = NULL) const
        xpath_node_set select_nodes(const char* query, xpath_variable_set* variables = NULL) const
        
    cdef cppclass xml_attribute:
        xml_attribute() except +
        string name() const
        string value() const
        bool set_name(const char* name)
        bool set_value(const char* value)
        xml_attribute next_attribute()
        xml_attribute previous_attribute()
        
    cdef enum xml_node_type:
        node_null
        node_document
        node_element
        node_pcdata
        node_cdata
        node_comment
        node_pi
        node_declaration
        node_doctype

    # XPath classes
    cdef cppclass xpath_node:
        xpath_node() except +
        xpath_node(const xml_node& node)
        xml_node node() const
        xml_attribute attribute() const
        xml_node parent() const
        
    cdef cppclass xpath_node_set:
        xpath_node_set() except +
        size_t size() const
        xpath_node operator[](size_t index) const
        
    cdef cppclass xpath_query:
        xpath_query() except +
        xpath_query(const char* query) except +
        xpath_node_set evaluate_node_set(const xml_node& n) const
        xpath_node evaluate_node(const xml_node& n) const
        bool evaluate_boolean(const xml_node& n) const
        double evaluate_number(const xml_node& n) const
        string evaluate_string(const xml_node& n) const
        
    cdef cppclass xpath_variable_set:
        xpath_variable_set() except +
    

    bool operator==(const xml_node&, const xml_node&)

cdef extern from *:
    """
    #include <sstream>
    #include <vector>
    #include "pugixml.hpp"

    // Reconstruct xml_node from raw internal pointer
    static inline pugi::xml_node node_from_raw_ptr(size_t addr) {
        return pugi::xml_node(reinterpret_cast<pugi::xml_node_struct*>(addr));
    }

    std::string pugi_serialize_node(
        const pugi::xml_node& node,
        const char* indent
    ) {
        if (node.type() == pugi::node_null) {
            return std::string();
        }
        std::ostringstream oss;
        node.print(oss, indent);
        std::string xml { oss.str() };
        if (!xml.empty() && *xml.rbegin() == '\\n') {
            xml.pop_back(); // Removes the last character
        }
        return xml;
    }

    static inline size_t get_pugi_node_address(const pugi::xml_node& node) {
        return reinterpret_cast<size_t>(node.internal_object());
    }

    static pugi::xml_node find_node_by_address(
        pugi::xml_node& root,
        size_t target_addr
    ) {
        if (root.type() == pugi::node_null) {
            return pugi::xml_node();
        }        
        std::vector<pugi::xml_node> stack;
        stack.push_back(root);
        
        while (!stack.empty()) {
            pugi::xml_node current = stack.back();
            stack.pop_back();
            
            size_t current_addr = get_pugi_node_address(current);
            
            if (current_addr == target_addr) {
                return current;
            }
            
            // Add children in reverse order
            pugi::xml_node child = current.last_child();
            while (child) {
                stack.push_back(child);
                child = child.previous_sibling();
            }
        }
        return pugi::xml_node();
    }

    static std::string get_xpath_for_node(const pugi::xml_node& node) {
        if (!node || node.type() != pugi::node_element) return "";

        // Collect path from node to root (then reverse)
        std::vector<pugi::xml_node> path;
        pugi::xml_node current = node;
        while (current && current.type() == pugi::node_element) {
            path.push_back(current);
            current = current.parent();
        }

        if (path.empty()) return "";

        std::ostringstream xpath;

        // Build from root to node
        for (auto it = path.rbegin(); it != path.rend(); ++it) {
            const pugi::xml_node& n = *it;
            const char* name = n.name();
            if (!name || !*name) continue;

            xpath << "/" << name;  
            // Count total same-name siblings under parent
            int total_same = 0;
            pugi::xml_node parent = n.parent();
            if (parent) {
                pugi::xml_node child = parent.first_child();
                while (child) {
                    if (child.type() == pugi::node_element && 
                        std::string(child.name()) == std::string(name)) {
                        ++total_same;
                    }
                    child = child.next_sibling();
                }
            } else {
                total_same = 1; // root element
            }

            // Only add index if needed
            if (total_same > 1) {
                int index = 1;
                pugi::xml_node sibling = n.previous_sibling();
                while (sibling) {
                    if (sibling.type() == pugi::node_element && 
                        std::string(sibling.name()) == std::string(name)) {
                        ++index;
                    }
                    sibling = sibling.previous_sibling();
                }
                xpath << "[" << index << "]";
            }
        }

        return xpath.str();
    }
    """
    string pugi_serialize_node(const xml_node& node, const char* indent)
    size_t get_pugi_node_address(xml_node& node)
    xml_node find_node_by_address(xml_node& root, size_t target_addr)
    string get_xpath_for_node(const xml_node& node)
    xml_node node_from_raw_ptr(size_t addr)


# Parse flags as an IntFlag enum (supports bitwise OR)
from enum import IntFlag as _IntFlag

class ParseFlags(_IntFlag):
    """Bitmask of parse options for :func:`parse_string` and :func:`parse_file`.

    Members are combined with the bitwise OR operator (``|``).  When no
    flags are supplied the parser uses ``ParseFlags.DEFAULT`` (all standard
    processing enabled).

    Use ``ParseFlags.MINIMAL`` when you only care about element structure
    and want the fastest possible parse — it skips escape processing,
    EOL normalization, and all whitespace handling.

    Example::

        >>> doc = pygixml.parse_string(xml, pygixml.ParseFlags.MINIMAL)
        >>> # Combine specific flags:
        >>> flags = pygixml.ParseFlags.COMMENTS | pygixml.ParseFlags.CDATA
        >>> doc = pygixml.parse_string(xml, flags)

    See the :ref:`parse-flags` section in the documentation for a complete
    description of each flag.
    """
    MINIMAL             = parse_minimal
    PI                  = parse_pi
    COMMENTS            = parse_comments
    CDATA               = parse_cdata
    WS_PCDATA           = parse_ws_pcdata
    ESCAPES             = parse_escapes
    EOL                 = parse_eol
    WCONV_ATTRIBUTE     = parse_wconv_attribute
    WNORM_ATTRIBUTE     = parse_wnorm_attribute
    DECLARATION         = parse_declaration
    DOCTYPE             = parse_doctype
    WS_PCDATA_SINGLE    = parse_ws_pcdata_single
    TRIM_PCDATA         = parse_trim_pcdata
    FRAGMENT            = parse_fragment
    EMBED_PCDATA        = parse_embed_pcdata
    MERGE_PCDATA        = parse_merge_pcdata
    DEFAULT             = parse_default
    FULL                = parse_full


# Version injected by CMake at compile time
cdef extern from *:
    """
    #define STRINGIFY(x) #x
    #define MACRO_STRINGIFY(x) STRINGIFY(x)
    #ifdef VERSION_INFO
        const char* PYGIXML_VERSION = MACRO_STRINGIFY(VERSION_INFO);
    #else
        const char* PYGIXML_VERSION = "dev";
    #endif
    """
    const char* PYGIXML_VERSION
__version__ = PYGIXML_VERSION.decode("utf-8")


class PygiXMLError(ValueError):
    """Raised when a pygixml operation fails.

    Typical causes include malformed XML passed to :func:`parse_string` or
    :func:`parse_file`, or an attempt to set a name/value on a null or
    otherwise invalid node.
    """
    pass


class PygiXMLNullNodeError(PygiXMLError):
    """Raised when an operation that requires a valid node is called on a
    null node (e.g. setting attributes on an element that was never found).
    """
    pass

cdef inline XMLNode _node_from_raw_ptr(size_t addr):
    cdef XMLNode wrapper = XMLNode()
    wrapper._node = node_from_raw_ptr(addr)
    return wrapper


cdef class XMLDocument:
    """An XML document, providing document-level operations.

    Use this class to load, create, save, and manipulate XML documents,
    or to access the root element and top-level children.

    The most common entry point is :func:`parse_string` or
    :func:`parse_file`, which return an ``XMLDocument``::

        >>> doc = pygixml.parse_string('<root><item>value</item></root>')
        >>> doc.root.child('item').text()
        'value'

    You can also build a document from scratch::

        >>> doc = pygixml.XMLDocument()
        >>> root = doc.append_child('catalog')
        >>> item = root.append_child('item')
        >>> item.set_value('content')

    When processing many files in a loop, reuse a single document with
    :meth:`reset` to avoid repeated allocations.
    """
    cdef xml_document* _doc

    def __cinit__(self):
        """Create an empty ``XMLDocument``.

        The document starts with no content.  Use :meth:`load_string`,
        :meth:`load_file`, or :meth:`append_child` to populate it.
        """
        self._doc = new xml_document()

    def __dealloc__(self):
        if self._doc != NULL:
            del self._doc
    
    def load_string(self, str content, options=0xFFFFFFFF):
        """Parse XML from a string and replace the current document content.

        Parses *content* and replaces whatever the document previously held.
        Returns ``True`` on success, ``False`` if the string is not
        well-formed.

        Args:
            content (str): The XML source text.
            options (ParseFlags): Which parse flags to use.  Defaults to
                ``ParseFlags.DEFAULT`` (full compliance).  Use
                ``ParseFlags.MINIMAL`` for faster parsing when you don't
                need escape processing, EOL normalization, or whitespace
                handling.

        Returns:
            bool: ``True`` if parsing succeeded, ``False`` otherwise.

        Example::

            >>> doc = pygixml.XMLDocument()
            >>> doc.load_string('<root><item>value</item></root>')
            True
            >>> doc.root.child('item').text()
            'value'

        Raises:
            PygiXMLError: When the input is not well-formed XML (raised
                by :func:`parse_string`; this method returns ``False``
                instead).
        """
        cdef unsigned int opts = options if options != 0xFFFFFFFF else 0xFFFFFFFF
        cdef bytes content_bytes = content.encode('utf-8')
        if opts == 0xFFFFFFFF:
            return <bool>self._doc.load_string(content_bytes)
        return <bool>self._doc.load_string(content_bytes, opts)

    def load_file(self, str path, options=0xFFFFFFFF):
        """Parse XML from a file and replace the current document content.

        Reads and parses the file at *path*.  Returns ``True`` on success,
        ``False`` if the file cannot be opened or does not contain
        well-formed XML.

        Args:
            path (str): Path to the XML file.
            options (ParseFlags): Which parse flags to use.  Defaults to
                ``ParseFlags.DEFAULT``.

        Returns:
            bool: ``True`` if loading succeeded, ``False`` otherwise.

        Example::

            >>> doc = pygixml.XMLDocument()
            >>> doc.load_file('data.xml')
            True
            >>> doc.root.name
            'root'
        """
        cdef unsigned int opts = options if options != 0xFFFFFFFF else 0xFFFFFFFF
        cdef bytes path_bytes = path.encode('utf-8')
        if opts == 0xFFFFFFFF:
            return <bool>self._doc.load_file(path_bytes)
        return <bool>self._doc.load_file(path_bytes, opts)
    
    def save_file(self, str path, str indent="  "):
        """Serialize the document and write it to a file.

        Args:
            path (str): Output file path.  Existing files will be
                overwritten.
            indent (str): Indentation string used for pretty-printing.
                Defaults to two spaces.  Pass an empty string for compact
                output with no indentation.

        Example::

            >>> doc = pygixml.parse_string('<root><item>value</item></root>')
            >>> doc.save_file('output.xml')              # 2-space indent
            >>> doc.save_file('compact.xml', indent='')  # no indent
        """
        cdef bytes path_bytes = path.encode('utf-8')
        cdef bytes indent_bytes = indent.encode('utf-8')
        self._doc.save_file(path_bytes, indent_bytes)

    def reset(self):
        """Clear all content, returning the document to its initial empty state.

        Reuses the same underlying C++ document object, avoiding
        reallocation overhead when processing many files in a loop.

        Example::

            >>> doc = pygixml.parse_string('<root>content</root>')
            >>> doc.reset()
            >>> doc.root  # None — document is empty
        """
        self._doc.reset()
    
    def append_child(self, str name):
        """Append a new child element and return it.

        Args:
            name (str): Tag name for the new element.  Pass an empty
                string to create a text node instead.

        Returns:
            XMLNode: The newly created element (or text node).

        Example::

            >>> doc = pygixml.XMLDocument()
            >>> root = doc.append_child('catalog')
            >>> item = root.append_child('item')
            >>> item.set_value('content')
        """
        cdef bytes name_bytes = name.encode('utf-8')
        cdef xml_node node = self._doc.append_child(name_bytes)
        return XMLNode.create_from_cpp(node)
    
    def first_child(self):
        """Return the first child element, or ``None`` if the document is
        empty.

        Returns:
            XMLNode | None

        Example::

            >>> doc = pygixml.parse_string('<root><child/></root>')
            >>> doc.first_child().name
            'root'
        """
        cdef xml_node node = self._doc.first_child()
        return XMLNode.create_from_cpp(node)
    
    def child(self, str name):
        """Return the first child element whose tag matches *name*, or
        ``None`` if no match is found.

        Args:
            name (str): Element tag to look for.

        Returns:
            XMLNode | None

        Example::

            >>> doc = pygixml.parse_string('<root><item>value</item></root>')
            >>> doc.child('item').text()
            'value'
        """
        cdef bytes name_bytes = name.encode('utf-8')
        cdef xml_node node = self._doc.child(name_bytes)
        return XMLNode.create_from_cpp(node)

    def to_string(self, indent="  "):
        """Serialize the document to an XML string.

        Args:
            indent (str | int): Indentation — either a string
                (e.g. ``'    '``) or a number of spaces (e.g. ``4``).
                Defaults to two spaces.

        Returns:
            str: The serialized XML.

        Example::

            >>> doc = pygixml.parse_string('<root><item>value</item></root>')
            >>> doc.to_string()
            '<root>\\n  <item>value</item>\\n</root>'
            >>> doc.to_string(4)
            '<root>\\n    <item>value</item>\\n</root>'
        """
        cdef str indent_str
        if isinstance(indent, int):
            indent_str = " " * indent
        else:
            indent_str = indent
            
        cdef bytes indent_bytes = indent_str.encode('utf-8')
        cdef string s = pugi_serialize_node(self._doc.first_child(), indent_bytes)
        return s.decode('utf-8')

    def __iter__(self):
        """Iterate over every element node in the document in depth-first
        order, starting from the root element.

        Yields:
            XMLNode: Each element node encountered.

        Example::

            >>> doc = pygixml.parse_string('<root><a><b/></a></root>')
            >>> [n.name for n in doc]
            ['root', 'a', 'b']
        """
        root = self.root
        return iter(root) if root else iter(())

    @property
    def root(self):
        """Return the root element of the document.

        Equivalent to calling :meth:`first_child`.  Returns ``None`` if
        the document is empty.

        Returns:
            XMLNode | None: The root element, or ``None``.

        Example::

            >>> doc = pygixml.parse_string('<root><item>value</item></root>')
            >>> doc.root.name
            'root'
        """
        return self.first_child()


cdef class XMLNode:
    """A single node in the XML tree.

    Represents an element, text, comment, processing instruction, or other
    node type.  Provides methods for navigating to related nodes
    (parent, children, siblings), reading and modifying content, and
    executing XPath queries scoped to this node.

    The most commonly used members are:

    - :attr:`name` / :attr:`value` — tag name and text value
    - :meth:`child` — first child with a given tag
    - :meth:`children` — iterate direct child elements
    - :meth:`text` — combined text content
    - :meth:`select_nodes` / :meth:`select_node` — XPath selection
    - :attr:`xml` — serialized XML of this node and its subtree

    Example::

        >>> doc = pygixml.parse_string('<root><item>value</item></root>')
        >>> root = doc.root
        >>> root.child('item').text()
        'value'
    """
    cdef xml_node _node

    def __init__(self):
        pass

    @staticmethod
    cdef XMLNode create_from_cpp(xml_node node):
        cdef XMLNode wrapper = XMLNode()
        wrapper._node = node
        return wrapper

    @property
    def type(self):
        """Return the node type as a human-readable string.

        Possible values: ``'element'``, ``'pcdata'``, ``'cdata'``,
        ``'comment'``, ``'pi'``, ``'declaration'``, ``'doctype'``,
        ``'document'``, ``'null'``.

        Returns:
            str

        Example::

            >>> doc = pygixml.parse_string('<root>text</root>')
            >>> doc.root.type
            'element'
            >>> doc.root.first_child().type
            'pcdata'
        """
        cdef xml_node_type node_type = self._node.type()
        
        if node_type == node_document:
            return "document"
        elif node_type == node_element:
            return "element"
        elif node_type == node_pcdata:
            return "pcdata"
        elif node_type == node_cdata:
            return "cdata"
        elif node_type == node_comment:
            return "comment"
        elif node_type == node_pi:
            return "pi"
        elif node_type == node_declaration:
            return "declaration"
        elif node_type == node_doctype:
            return "doctype"
        else:  # node_null
            return "null"
    
    @property
    def name(self):
        """Return the tag name of this node.

        For element nodes this is the element's tag name.  For text,
        comment, and other non-element nodes this is ``None``.

        Returns:
            str | None

        Example::

            >>> doc = pygixml.parse_string('<root/>')
            >>> doc.root.name
            'root'
        """
        cdef string name = self._node.name()
        return name.decode('utf-8') if not name.empty() else None
    
    
    @property
    def value(self):
        """Return the text content of this node.

        For text, CDATA, comment, and processing-instruction nodes, returns
        the raw value directly.

        For **element** nodes, this is a convenience shortcut that returns
        the value of the first text/CDATA child (or ``None`` if no text
        child exists).

        Returns:
            str | None

        Example::

            # Text node — returns raw value
            >>> doc = pygixml.parse_string('<root><item>hello</item></root>')
            >>> doc.root.child('item').first_child().value
            'hello'

            # Element node — returns first text child's value
            >>> doc.root.child('item').value
            'hello'
        """
        cdef string val
        cdef xml_node child
        if self._node.type() == node_element:
            child = self._node.first_child()
            if child.type() == node_pcdata or child.type() == node_cdata:
                val = child.value()
                return val.decode('utf-8') if not val.empty() else None
            return None
        val = self._node.value()
        return val.decode('utf-8') if not val.empty() else None
    
    def set_name(self, str name):
        """Change the tag name of this element.

        Returns ``False`` if the node is null.

        Args:
            name (str): New tag name.

        Returns:
            bool

        Example::

            >>> doc = pygixml.parse_string('<old/>')
            >>> doc.root.set_name('new')
            True
            >>> doc.root.name
            'new'
        """
        cdef bytes name_bytes = name.encode('utf-8')
        return self._node.set_name(name_bytes)

    def set_value(self, str value):
        """Replace the text content of this node.

        Returns ``False`` if the node is null.

        Args:
            value (str): New text content.

        Returns:
            bool

        Example::

            >>> doc = pygixml.parse_string('<root><item>old</item></root>')
            >>> doc.root.child('item').first_child().set_value('new')
            True
        """
        cdef bytes value_bytes = value.encode('utf-8')
        return self._node.set_value(value_bytes)

    @name.setter
    def name(self, str name):
        """Set the tag name, raising :class:`PygiXMLError` on failure.

        Example::

            >>> node.name = 'renamed'
        """
        if not self.set_name(name):
            raise PygiXMLError("Cannot set name: node is null or invalid")

    @value.setter
    def value(self, str value):
        """Set the text value of this node.

        For text, CDATA, and comment nodes, sets the raw value directly.

        For **element** nodes, this is a convenience shortcut that creates
        or replaces the first text-node child — equivalent to::

            text_node = node.first_child()
            if text_node and text_node.type in ('pcdata', 'cdata'):
                text_node.set_value(value)
            else:
                node.prepend_child('').set_value(value)

        Example::

            # Text node — sets raw value
            text_node.value = 'hello'

            # Element node — creates/replaces text child
            element.value = 'hello'   # <element>hello</element>
        """
        cdef bytes value_bytes = value.encode('utf-8')
        cdef xml_node child
        if self._node.type() == node_element:
            child = self._node.first_child()
            if child.type() == node_pcdata or child.type() == node_cdata:
                child.set_value(value_bytes)
            else:
                # Create a new text (pcdata) node and prepend it
                child = self._node.prepend_child(node_pcdata)
                child.set_value(value_bytes)
        else:
            if not self._node.set_value(value_bytes):
                raise PygiXMLError("Cannot set value: node is null or invalid")

    def first_child(self):
        """Return the first child element, or ``None``.

        Returns:
            XMLNode | None

        Example::

            >>> doc = pygixml.parse_string('<root><a/><b/></root>')
            >>> doc.root.first_child().name
            'a'
        """
        cdef xml_node node = self._node.first_child()
        return XMLNode.create_from_cpp(node)

    def child(self, str name):
        """Return the first child element whose tag matches *name*, or
        ``None``.

        Args:
            name (str): Element tag to look for.

        Returns:
            XMLNode | None

        Example::

            >>> doc = pygixml.parse_string('<root><item>value</item></root>')
            >>> doc.root.child('item').text()
            'value'
        """
        cdef bytes name_bytes = name.encode('utf-8')
        cdef xml_node node = self._node.child(name_bytes)
        return XMLNode.create_from_cpp(node)

    def append_child(self, str name):
        """Append a new child element and return it.

        Args:
            name (str): Tag name.  Use an empty string to create a text
                node instead.

        Returns:
            XMLNode: The newly created child.

        Example::

            >>> root = doc.root
            >>> root.append_child('title').set_value('My Title')
        """
        cdef bytes name_bytes = name.encode('utf-8')
        cdef xml_node node = self._node.append_child(name_bytes)
        return XMLNode.create_from_cpp(node)
    
    def child_value(self, str name=None):
        """Return the text content of a child element.

        If *name* is given, finds the first child with that tag and
        returns its text.  Without *name*, returns the direct text
        content of this node (i.e. text immediately inside this element,
        not inside a child).

        Args:
            name (str | None): Child tag to look up, or ``None`` for
                direct text.

        Returns:
            str | None

        Example::

            >>> doc = pygixml.parse_string('<root><title>Book</title></root>')
            >>> doc.root.child_value('title')
            'Book'
        """
        cdef string value
        cdef bytes name_bytes
        
        if name is None:
            value = self._node.child_value()
            return value.decode('utf-8') if not value.empty() else None
        else:
            name_bytes = name.encode('utf-8')
            value = self._node.child_value(name_bytes)
            return value.decode('utf-8') if not value.empty() else None
    
    @property
    def next_sibling(self):
        """The next sibling node, or ``None`` if this is the last child."""
        cdef xml_node node = self._node.next_sibling()
        if node.type() == node_null:
            return None
        return XMLNode.create_from_cpp(node)

    @property
    def previous_sibling(self):
        """The previous sibling node, or ``None`` if this is the first
        child."""
        cdef xml_node node = self._node.previous_sibling()
        if node.type() == node_null:
            return None
        return XMLNode.create_from_cpp(node)

    @property
    def next_element_sibling(self):
        """The next sibling that is an element node, skipping text,
        comment, and other non-element nodes.  ``None`` if none."""
        sibling = self.next_sibling
        while sibling and sibling.type != "element":
            sibling = sibling.next_sibling
        return sibling

    @property
    def previous_element_sibling(self):
        """The previous sibling that is an element node.  ``None`` if
        none."""
        sibling = self.previous_sibling
        while sibling and sibling.type != "element":
            sibling = sibling.previous_sibling
        return sibling

    @property
    def parent(self):
        """The parent element node.  Returns ``None`` for the document
        root."""
        cdef xml_node node = self._node.parent()
        return XMLNode.create_from_cpp(node)
    
    def first_attribute(self):
        """Return the first attribute on this element, or ``None`` if it
        has none.

        Returns:
            XMLAttribute | None

        Example::

            >>> doc = pygixml.parse_string('<root id="1" class="main"/>')
            >>> doc.root.first_attribute().name
            'id'
        """
        cdef xml_attribute attr = self._node.first_attribute()
        return XMLAttribute.create_from_cpp(attr)

    def attribute(self, str name):
        """Return the attribute with the given *name*, or ``None``.

        Args:
            name (str): Attribute name.

        Returns:
            XMLAttribute | None

        Example::

            >>> doc = pygixml.parse_string('<root id="1"/>')
            >>> doc.root.attribute('id').value
            '1'
        """
        cdef bytes name_bytes = name.encode('utf-8')
        cdef xml_attribute attr = self._node.attribute(name_bytes)
        return XMLAttribute.create_from_cpp(attr)
    
    # XPath methods using XPathQuery internally
    def select_nodes(self, str query):
        """Run an XPath expression and return all matching nodes.

        Args:
            query (str): XPath 1.0 expression.

        Returns:
            XPathNodeSet

        Example::

            >>> doc = pygixml.parse_string('<root><a/><b/><a/></root>')
            >>> len(doc.root.select_nodes('a'))
            2
        """
        cdef XPathQuery xpath_query = XPathQuery(query)
        return xpath_query.evaluate_node_set(self)

    def select_node(self, str query):
        """Run an XPath expression and return the first match, or
        ``None``.

        Args:
            query (str): XPath 1.0 expression.

        Returns:
            XPathNode | None

        Example::

            >>> doc = pygixml.parse_string('<root><a/><b/></root>')
            >>> doc.root.select_node('b').node.name
            'b'
        """
        cdef XPathQuery xpath_query = XPathQuery(query)
        return xpath_query.evaluate_node(self)

    def is_null(self):
        """Return ``True`` if this node is null (i.e. was not found or is
        invalid)."""
        return self._node.type() == node_null
    
    @property
    def xpath(self):
        """The absolute XPath to this node (e.g. ``/root/item[1]/name[1]``).

        .. note::
           This is a **pygixml-specific feature**.  pugixml does not
           provide XPath generation natively — pygixml implements a custom
           O(depth) algorithm that walks from the node up to the root,
           counting same-name siblings to produce accurate positional
           predicates.

        Returns an empty string if the node is not an element.

        Returns:
            str
        """
        if self._node.type() != node_element:
            return ""
        cdef string xpath_str = get_xpath_for_node(self._node)
        return xpath_str.decode('utf-8')

    def to_string(self, indent="  "):
        """Serialize this element (and its subtree) to an XML string.

        .. note::
           This is a **pygixml-specific feature**.  pugixml can serialize
           to a file via ``save_file()``, but it does not provide a
           method that returns the serialized XML as a Python string.
           pygixml implements this using an internal ``std::ostringstream``
           buffer.

        Args:
            indent (str | int): Indentation string or number of spaces.
                Defaults to two spaces.

        Returns:
            str

        Example::

            >>> doc = pygixml.parse_string('<root><item>val</item></root>')
            >>> doc.root.child('item').to_string()
            '<item>val</item>'
        """
        if self._node.type() == node_null:
            return ""
            
        cdef str indent_str
        if isinstance(indent, int):
            indent_str = " " * indent
        else:
            indent_str = indent
            
        cdef bytes indent_bytes = indent_str.encode('utf-8')
        cdef string s = pugi_serialize_node(self._node, indent_bytes)
        return s.decode('utf-8')

    @property
    def xml(self):
        """Shorthand for ``self.to_string()`` — serialized XML with
        default two-space indentation.

        .. note::
           This is a **pygixml-specific convenience property**.
           pugixml has no equivalent.
        """
        return self.to_string()

    def find_mem_id(self, size_t mem_id):
        """Look up a descendant node by its memory identifier
        (see :attr:`mem_id`).

        .. note::
           This is a **pygixml-specific feature**.  pugixml has no
           equivalent — pygixml walks the descendant tree in DFS order
           comparing node addresses until a match is found.

        Returns:
            XMLNode | None
        """
        cdef xml_node node = find_node_by_address(self._node, mem_id)
        return XMLNode.create_from_cpp(node)

    @staticmethod
    def from_mem_id_unsafe(size_t mem_id):
        """Reconstruct an ``XMLNode`` from its memory identifier in **O(1)** time.

        Unlike :meth:`find_mem_id`, which walks the entire tree in **O(n)**
        time to locate a node, this method performs an instant lookup.

        ⚠️ **Warning**: If the *mem_id* is stale (the node was deleted or
        the document has been freed), calling methods on the returned
        object **may cause a segmentation fault**.

        Only use this when you are certain the identifier still belongs
        to a live node within a valid ``XMLDocument``.

        Args:
            mem_id (int): An identifier previously obtained from
                ``node.mem_id``.

        Returns:
            XMLNode: A wrapper for the node at the given identifier.

        Complexity:
            **O(1)** — direct lookup, no tree traversal.
            Compare with :meth:`find_mem_id` which is **O(n)**.

        Example::

            >>> mid = root.child('item').mem_id
            >>> node = XMLNode.from_mem_id_unsafe(mid)
            >>> node.name
            'item'
        """
        return _node_from_raw_ptr(mem_id)


    @property
    def mem_id(self):
        """A unique numeric identifier derived from the node's internal address.

        .. note::
           This is a **pygixml-specific feature**.  The underlying pugixml
           library does not expose integer node identifiers natively.
           pygixml provides ``mem_id`` as a safe, hashable handle for
           debugging, caching, and fast node reconstruction.

        Returns ``0`` for null nodes.

        Returns:
            int
        """
        if self._node.type() == node_null:
            return 0
        return get_pugi_node_address(self._node)

    def __eq__(self, other: XMLNode) -> bool:
        """Return ``True`` if both objects wrap the same underlying
        pugixml node.

        This is an identity check, not a structural comparison.
        """
        if not isinstance(other, XMLNode):
            return False
        return self._node == other._node

    def __bool__(self):
        """Return ``True`` if this node is not null."""
        return self._node.type() != node_null

    def children(self, bint recursive=False):
        """Iterate over child **element** nodes.

        .. note::
           This is a **pygixml-specific feature**.  pugixml provides
           ``first_child()`` and ``next_sibling()`` for manual traversal,
           but ``children()`` offers a Pythonic one-liner for iterating
           direct child elements — or all descendants with
           ``recursive=True``.

        Text, comment, and processing-instruction nodes are skipped.

        Args:
            recursive (bool): Yield only direct children (``False``, the
                default) or all descendants in depth-first order
                (``True``).

        Yields:
            XMLNode

        Example::

            >>> doc = pygixml.parse_string('<root><a><a1/></a><b/></root>')
            >>> [c.name for c in doc.root.children()]
            ['a', 'b']
            >>> [c.name for c in doc.root.children(True)]
            ['a', 'a1', 'b']
        """
        cdef xml_node current = self._node.first_child()
        cdef xml_node child
        cdef vector[xml_node] stack

        if not recursive:
            while current.type() != node_null:
                if current.type() == node_element:
                    yield XMLNode.create_from_cpp(current)
                current = current.next_sibling()
            return

        # Recursive DFS
        current = self._node.last_child()
        while current.type() != node_null:
            stack.push_back(current)
            current = current.previous_sibling()

        while stack.size() > 0:
            current = stack.back()
            stack.pop_back()
            if current.type() == node_element:
                yield XMLNode.create_from_cpp(current)
            child = current.last_child()
            while child.type() != node_null:
                stack.push_back(child)
                child = child.previous_sibling()

    def __iter__(self):
        """Iterate over all descendant **element** nodes in depth-first
        order.

        Equivalent to ``self.children(recursive=True)``.

        Yields:
            XMLNode
        """
        yield from self.children(True)

    def text(self, bint recursive=True, str join="\n"):
        """Return the combined text content of this node.

        .. note::
           This is a **pygixml-specific feature**.  pugixml provides
           ``child_value()`` for a single child's text, but ``text()``
           recursively collects text from all descendants (optionally
           non-recursive) and joins the fragments with a configurable
           separator.

        Args:
            recursive (bool): When ``True`` (default), gathers text from
                all descendant text and CDATA nodes.  When ``False``,
                returns only text that is a *direct* child of this
                element.
            join (str): String used to join multiple text fragments.
                Defaults to ``\\n``.

        Returns:
            str

        Example::

            >>> doc = pygixml.parse_string(
            ...     '<root><a>hello</a><b>world</b></root>')
            >>> doc.root.text()
            'hello\\nworld'
            >>> doc.root.text(join=', ')
            'hello, world'
        """
        if self._node.type() == node_null:
            return ""

        cdef list out = []
        cdef xml_node current
        cdef string val
        cdef vector[xml_node] stack

        # Initialize stack with direct children (reverse order for left-to-right)
        current = self._node.last_child()
        while current.type() != node_null:
            stack.push_back(current)
            current = current.previous_sibling()

        while stack.size() > 0:
            current = stack.back()
            stack.pop_back()
            if current.type() == node_pcdata or current.type() == node_cdata:
                val = current.value()
                if not val.empty():
                    out.append(val.decode('utf-8'))
            # Expand children only in recursive mode
            if recursive:
                current = current.last_child()
                while current.type() != node_null:
                    stack.push_back(current)
                    current = current.previous_sibling()

        return join.join(out)
    

cdef class XMLAttribute:
    """An XML attribute on an element (e.g. ``id="123"``).

    Use :meth:`XMLNode.attribute` or :meth:`XMLNode.first_attribute` to
    obtain attributes.

    Example::

        >>> doc = pygixml.parse_string('<root id="42" class="main"/>')
        >>> root = doc.root
        >>> root.attribute('id').value
        '42'
    """
    cdef xml_attribute _attr
    
    @staticmethod
    cdef XMLAttribute create_from_cpp(xml_attribute attr):
        cdef XMLAttribute wrapper = XMLAttribute()
        wrapper._attr = attr
        return wrapper
    
    @property
    def name(self):
        """Return the attribute name.

        Returns:
            str | None
        """
        cdef string name = self._attr.name()
        return name.decode('utf-8') if not name.empty() else None

    @property
    def value(self):
        """Return the attribute value.

        Returns:
            str | None
        """
        cdef string value = self._attr.value()
        return value.decode('utf-8') if not value.empty() else None

    def set_name(self, str name):
        """Change the attribute name.  Returns ``False`` if null."""
        cdef bytes name_bytes = name.encode('utf-8')
        return self._attr.set_name(name_bytes)

    def set_value(self, str value):
        """Change the attribute value.  Returns ``False`` if null."""
        cdef bytes value_bytes = value.encode('utf-8')
        return self._attr.set_value(value_bytes)

    @name.setter
    def name(self, str name):
        """Set the attribute name, raising :class:`PygiXMLError` on
        failure."""
        if not self.set_name(name):
            raise PygiXMLError("Cannot set attribute name")

    @value.setter
    def value(self, str value):
        """Set the attribute value, raising :class:`PygiXMLError` on
        failure."""
        if not self.set_value(value):
            raise PygiXMLError("Cannot set attribute value")

    @property
    def next_attribute(self):
        """Get next attribute.
        
        Returns:
            XMLAttribute: Next attribute or None if no next attribute
            
        Example:
            >>> attr = node.first_attribute()
            >>> next_attr = attr.next_attribute
        """
        cdef xml_attribute attr = self._attr.next_attribute()
        return XMLAttribute.create_from_cpp(attr)

    def __iter__(self):
        """Iterate over all attributes starting from this one.
        
        Yields:
            XMLAttribute: Each attribute in the chain
            
        Example:
            >>> for attr in node.first_attribute():
            ...     print(f"{attr.name} = {attr.value}")
        """
        current = self
        while current:
            yield current
            current = current.next_attribute

    def __bool__(self):
        """Return True if this attribute is not null.
        
        Returns:
            bool: True if attribute has name or value, False otherwise
            
        Example:
            >>> attr = node.attribute('id')
            >>> if attr:
            ...     print(f"ID: {attr.value}")
        """
        cdef string name = self._attr.name()
        return not name.empty()

# XPath wrapper classes
cdef class XPathNode:
    """A single result from an XPath query.

    Wraps either an :class:`XMLNode` (``.node``) or an
    :class:`XMLAttribute` (``.attribute``).  One of these properties will
    be ``None`` depending on what the query matched.

    Example::

        >>> doc = pygixml.parse_string('<root><item id="1">value</item></root>')
        >>> result = doc.select_node('//item')
        >>> result.node.name
        'item'
    """
    cdef xpath_node _xpath_node

    @staticmethod
    cdef XPathNode create_from_cpp(xpath_node xpath_node):
        cdef XPathNode wrapper = XPathNode()
        wrapper._xpath_node = xpath_node
        return wrapper

    @property
    def node(self):
        """The matched element, or ``None`` if the query matched an
        attribute instead."""
        cdef xml_node n = self._xpath_node.node()
        return XMLNode.create_from_cpp(n)

    @property
    def attribute(self):
        """The matched attribute, or ``None`` if the query matched an
        element instead."""
        cdef xml_attribute attr = self._xpath_node.attribute()
        return XMLAttribute.create_from_cpp(attr)

    @property
    def parent(self):
        """The parent of the matched node (``None`` for attributes or the
        document root)."""
        cdef xml_node n = self._xpath_node.parent()
        return XMLNode.create_from_cpp(n)


cdef class XPathNodeSet:
    """A collection of :class:`XPathNode` results from an XPath query.

    Supports ``len()``, indexing (``node_set[0]``), and iteration.

    Example::

        >>> doc = pygixml.parse_string('<root><item>1</item><item>2</item></root>')
        >>> nodes = doc.select_nodes('//item')
        >>> len(nodes)
        2
        >>> nodes[0].node.text()
        '1'
    """
    cdef xpath_node_set _xpath_node_set

    def __cinit__(self):
        self._xpath_node_set = xpath_node_set()

    @staticmethod
    cdef XPathNodeSet create_from_cpp(xpath_node_set xpath_node_set):
        cdef XPathNodeSet wrapper = XPathNodeSet()
        wrapper._xpath_node_set = xpath_node_set
        return wrapper

    def __len__(self):
        """Number of matched nodes."""
        return self._xpath_node_set.size()

    def __getitem__(self, size_t index):
        """Return the :class:`XPathNode` at *index*.

        Raises:
            IndexError: If *index* is out of range.
        """
        if index >= self._xpath_node_set.size():
            raise IndexError("XPath node set index out of range")
        cdef xpath_node node = self._xpath_node_set[index]
        return XPathNode.create_from_cpp(node)

    def __iter__(self):
        """Iterate over matched :class:`XPathNode` objects."""
        cdef size_t i
        for i in range(self._xpath_node_set.size()):
            yield self[i]


cdef class XPathQuery:
    """A compiled XPath 1.0 query.

    Compiling a query once and re-using it is faster than calling
    ``select_nodes()`` repeatedly, because the expression is parsed only
    once.

    Example::

        >>> doc = pygixml.parse_string('<root><item>value</item></root>')
        >>> query = pygixml.XPathQuery('//item')
        >>> query.evaluate_node(doc.root).node.text()
        'value'
    """
    cdef xpath_query* _query

    def __cinit__(self, str query):
        """Compile an XPath expression.

        Args:
            query (str): XPath 1.0 expression.
        """
        cdef bytes query_bytes = query.encode('utf-8')
        self._query = new xpath_query(query_bytes)
    
    def __dealloc__(self):
        if self._query != NULL:
            del self._query
    
    def evaluate_node_set(self, XMLNode context_node):
        """Evaluate query and return node set.
        
        Args:
            context_node (XMLNode): Node to evaluate the query against
            
        Returns:
            XPathNodeSet: Set of matching XPath nodes
            
        Example:
            >>> query = pygixml.XPathQuery('//item')
            >>> nodes = query.evaluate_node_set(doc.first_child())
            >>> for node in nodes:
            ...     print(node.node.text())
        """
        cdef xpath_node_set result = self._query.evaluate_node_set(context_node._node)
        return XPathNodeSet.create_from_cpp(result)
    
    def evaluate_node(self, XMLNode context_node):
        """Evaluate query and return first node.
        
        Args:
            context_node (XMLNode): Node to evaluate the query against
            
        Returns:
            XPathNode: First matching XPath node or None if no matches
            
        Example:
            >>> query = pygixml.XPathQuery('//item')
            >>> node = query.evaluate_node(doc.first_child())
            >>> print(node.node.text())
        """
        cdef xpath_node result = self._query.evaluate_node(context_node._node)
        return XPathNode.create_from_cpp(result)
    
    def evaluate_boolean(self, XMLNode context_node):
        """Evaluate query and return boolean result.
        
        Args:
            context_node (XMLNode): Node to evaluate the query against
            
        Returns:
            bool: Boolean result of the XPath query
            
        Example:
            >>> query = pygixml.XPathQuery('count(//item) > 0')
            >>> has_items = query.evaluate_boolean(doc.first_child())
            >>> print(has_items)
            True
        """
        return self._query.evaluate_boolean(context_node._node)
    
    def evaluate_number(self, XMLNode context_node):
        """Evaluate query and return numeric result.
        
        Args:
            context_node (XMLNode): Node to evaluate the query against
            
        Returns:
            float: Numeric result of the XPath query
            
        Example:
            >>> query = pygixml.XPathQuery('count(//item)')
            >>> count = query.evaluate_number(doc.first_child())
            >>> print(count)
            2.0
        """
        return self._query.evaluate_number(context_node._node)
    
    def evaluate_string(self, XMLNode context_node):
        """Evaluate query and return string result.
        
        Args:
            context_node (XMLNode): Node to evaluate the query against
            
        Returns:
            str: String result of the XPath query or None if empty
            
        Example:
            >>> query = pygixml.XPathQuery('//item[1]/text()')
            >>> text = query.evaluate_string(doc.first_child())
            >>> print(text)
            'value'
        """
        cdef string result = self._query.evaluate_string(context_node._node)
        return result.decode('utf-8') if not result.empty() else None

# Convenience functions
def parse_string(str xml_string, options=0xFFFFFFFF):
    """Parse XML from string and return XMLDocument.

    Args:
        xml_string (str): XML content as string
        options (ParseFlags, optional): Parse flags
            (default: ``ParseFlags.DEFAULT``).
            Combine flags with bitwise OR.  Use ``ParseFlags.MINIMAL``
            for fastest parsing when you don't need comments, CDATA,
            or escape processing.

    Returns:
        XMLDocument: Parsed XML document

    Raises:
        PygiXMLError: If parsing fails

    Example:
        >>> import pygixml
        >>> doc = pygixml.parse_string('<root>content</root>')
        >>> doc = pygixml.parse_string(xml, pygixml.ParseFlags.MINIMAL)
    """
    doc = XMLDocument()
    if doc.load_string(xml_string, options):
        return doc
    else:
        raise PygiXMLError("Failed to parse XML string")

def parse_file(str file_path, options=0xFFFFFFFF):
    """Parse XML from file and return XMLDocument.

    Args:
        file_path (str): Path to XML file
        options (ParseFlags, optional): Parse flags
            (default: ``ParseFlags.DEFAULT``).
            Combine flags with bitwise OR.  Use ``ParseFlags.MINIMAL``
            for fastest parsing when you don't need comments, CDATA,
            or escape processing.

    Returns:
        XMLDocument: Parsed XML document

    Raises:
        PygiXMLError: If parsing fails

    Example:
        >>> import pygixml
        >>> doc = pygixml.parse_file('data.xml')
        >>> doc = pygixml.parse_file('data.xml', pygixml.ParseFlags.MINIMAL)
    """
    doc = XMLDocument()
    if doc.load_file(file_path, options):
        return doc
    else:
        raise PygiXMLError(f"Failed to parse XML file: {file_path}")
