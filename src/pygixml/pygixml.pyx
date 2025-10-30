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
    cdef cppclass xml_document:
        xml_document() except +
        xml_node append_child(const char* name)
        xml_node prepend_child(const char* name)
        xml_node first_child()
        xml_node last_child()
        xml_node child(const char* name)
        bool load_string(const char* contents)
        bool load_file(const char* path)
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



class PygiXMLError(ValueError):
    """General exception raised by pygixml."""
    pass


class PygiXMLNullNodeError(PygiXMLError):
    pass



# Python wrapper classes
cdef class XMLDocument:
    """XML document wrapper providing document-level operations.
    
    This class represents an XML document and provides methods for loading,
    saving, and manipulating the document structure.
    
    Example:
        >>> import pygixml
        >>> doc = pygixml.parse_string('<root><item>value</item></root>')
        >>> root = doc.first_child()
        >>> print(root.name)
        'root'
    """
    cdef xml_document* _doc
    
    def __cinit__(self):
        self._doc = new xml_document()
    
    def __dealloc__(self):
        if self._doc != NULL:
            del self._doc
    
    def load_string(self, str content):
        """Load XML from string.
        
        Args:
            content (str): XML content as string
            
        Returns:
            bool: True if parsing succeeded, False otherwise
            
        Example:
            >>> doc = pygixml.XMLDocument()
            >>> success = doc.load_string('<root>content</root>')
            >>> print(success)
            True
        """
        cdef bytes content_bytes = content.encode('utf-8')
        return self._doc.load_string(content_bytes)
    
    def load_file(self, str path):
        """Load XML from file.
        
        Args:
            path (str): Path to XML file
            
        Returns:
            bool: True if loading succeeded, False otherwise
            
        Example:
            >>> doc = pygixml.XMLDocument()
            >>> success = doc.load_file('data.xml')
            >>> print(success)
            True
        """
        cdef bytes path_bytes = path.encode('utf-8')
        return self._doc.load_file(path_bytes)
    
    def save_file(self, str path, str indent="  "):
        """Save XML to file.
        
        Args:
            path (str): Path where to save the file
            indent (str): Indentation string (default: two spaces)
            
        Example:
            >>> doc = pygixml.parse_string('<root>content</root>')
            >>> doc.save_file('output.xml', indent='    ')
        """
        cdef bytes path_bytes = path.encode('utf-8')
        cdef bytes indent_bytes = indent.encode('utf-8')
        self._doc.save_file(path_bytes, indent_bytes)
    
    
    def reset(self):
        """Reset the document to empty state.
        
        Clears all content and resets the document to its initial state.
        
        Example:
            >>> doc = pygixml.parse_string('<root>content</root>')
            >>> doc.reset()  # Document is now empty
        """
        self._doc.reset()
    
    def append_child(self, str name):
        """Append a child node to the document.
        
        Args:
            name (str): Name of the new element
            
        Returns:
            XMLNode: The newly created node
            
        Example:
            >>> doc = pygixml.XMLDocument()
            >>> root = doc.append_child('root')
            >>> item = root.append_child('item')
        """
        cdef bytes name_bytes = name.encode('utf-8')
        cdef xml_node node = self._doc.append_child(name_bytes)
        return XMLNode.create_from_cpp(node)
    
    def first_child(self):
        """Get first child node of the document.
        
        Returns:
            XMLNode: First child node or None if no children
            
        Example:
            >>> doc = pygixml.parse_string('<root><child/></root>')
            >>> first = doc.first_child()
            >>> print(first.name)
            'root'
        """
        cdef xml_node node = self._doc.first_child()
        return XMLNode.create_from_cpp(node)
    
    def child(self, str name):
        """Get child node by name.
        
        Args:
            name (str): Name of the child element to find
            
        Returns:
            XMLNode: Child node with specified name or None if not found
            
        Example:
            >>> doc = pygixml.parse_string('<root><item>value</item></root>')
            >>> item = doc.child('item')
            >>> print(item.text())
            'value'
        """
        cdef bytes name_bytes = name.encode('utf-8')
        cdef xml_node node = self._doc.child(name_bytes)
        return XMLNode.create_from_cpp(node)

    def to_string(self, indent="  "):
        """Serialize the document to XML string with custom indentation.
        
        Args:
            indent (str or int): Indentation string or number of spaces 
                                (default: two spaces)
            
        Returns:
            str: XML content as string
            
        Example:
            >>> doc = pygixml.parse_string('<root><item>value</item></root>')
            >>> # Default indentation (2 spaces)
            >>> xml_string = doc.to_string()
            >>> # Custom string indentation
            >>> xml_string = doc.to_string('    ')
            >>> # Number of spaces
            >>> xml_string = doc.to_string(4)
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
        """Iterate over all nodes in the document.
        
        Yields:
            XMLNode: Each node in depth-first order
            
        Example:
            >>> doc = pygixml.parse_string('<root><a><b/></a></root>')
            >>> for node in doc:
            ...     print(node.name)
            root
            a
            b
        """
        root = self.first_child()
        return iter(root) if root else iter(())


cdef class XMLNode:
    """XML node wrapper providing node-level operations.
    
    This class represents an XML node and provides methods for accessing
    and manipulating node properties, children, attributes, and text content.
    
    Example:
        >>> import pygixml
        >>> doc = pygixml.parse_string('<root><item>value</item></root>')
        >>> root = doc.first_child()
        >>> item = root.child('item')
        >>> print(item.text())
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
    def name(self):
        """Get node name.
        
        Returns:
            str: Node name or None if no name
            
        Example:
            >>> node = doc.first_child()
            >>> print(node.name)
            'root'
        """
        cdef string name = self._node.name()
        return name.decode('utf-8') if not name.empty() else None
    
    
    @property
    def value(self):
        """Get node value.
        
        Returns:
            str: Node value or None if no value
            
        Example:
            >>> text_node = node.first_child()
            >>> print(text_node.value)
            'text content'
        """
        cdef string value = self._node.value()
        return value.decode('utf-8') if not value.empty() else None
    
    def set_name(self, str name):
        """Set node name.
        
        Args:
            name (str): New name for the node
            
        Returns:
            bool: True if successful, False if node is null or invalid
            
        Example:
            >>> success = node.set_name('new_name')
            >>> print(success)
            True
        """
        cdef bytes name_bytes = name.encode('utf-8')
        return self._node.set_name(name_bytes)

    def set_value(self, str value):
        """Set node value.
        
        Args:
            value (str): New value for the node
            
        Returns:
            bool: True if successful, False if node is null or invalid
            
        Example:
            >>> success = node.set_value('new value')
            >>> print(success)
            True
        """
        cdef bytes value_bytes = value.encode('utf-8')
        return self._node.set_value(value_bytes)

    @name.setter
    def name(self, str name):
        """Set node name.
        
        Args:
            name (str): New name for the node
            
        Raises:
            PygiXMLError: If node is null or invalid
            
        Example:
            >>> node.name = 'new_name'
        """
        if not self.set_name(name):
            raise PygiXMLError("Cannot set name: node is null or invalid")

    
    @value.setter
    def value(self, str value):
        """Set node value.
        
        Args:
            value (str): New value for the node
            
        Raises:
            PygiXMLError: If node is null or invalid
            
        Example:
            >>> node.value = 'new value'
        """
        if not self.set_value(value):
            raise PygiXMLError("Cannot set value: node is null or invalid")
    
    def first_child(self):
        """Get first child node.
        
        Returns:
            XMLNode: First child node or None if no children
            
        Example:
            >>> root = doc.first_child()
            >>> first_child = root.first_child()
            >>> print(first_child.name)
            'child'
        """
        cdef xml_node node = self._node.first_child()
        return XMLNode.create_from_cpp(node)
    
    def child(self, str name):
        """Get child node by name.
        
        Args:
            name (str): Name of the child element to find
            
        Returns:
            XMLNode: Child node with specified name or None if not found
            
        Example:
            >>> root = doc.first_child()
            >>> item = root.child('item')
            >>> print(item.text())
            'value'
        """
        cdef bytes name_bytes = name.encode('utf-8')
        cdef xml_node node = self._node.child(name_bytes)
        return XMLNode.create_from_cpp(node)
    
    def append_child(self, str name):
        """Append a child node.
        
        Args:
            name (str): Name of the new child element
            
        Returns:
            XMLNode: The newly created child node
            
        Example:
            >>> root = doc.first_child()
            >>> new_child = root.append_child('new_element')
        """
        cdef bytes name_bytes = name.encode('utf-8')
        cdef xml_node node = self._node.append_child(name_bytes)
        return XMLNode.create_from_cpp(node)
    
    def child_value(self, str name=None):
        """Get child value.
        
        Args:
            name (str, optional): Name of specific child element. 
                                 If None, returns direct text content.
            
        Returns:
            str: Text content or None if no content
            
        Example:
            >>> # Get direct text content
            >>> text = node.child_value()
            >>> # Get text from specific child
            >>> title = node.child_value('title')
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
        """Get next sibling node"""
        cdef xml_node node = self._node.next_sibling()
        if node.type() == node_null:
            return None
        return XMLNode.create_from_cpp(node)

    
    @property
    def previous_sibling(self):
        """Get previous sibling node"""
        cdef xml_node node = self._node.previous_sibling()
        if node.type() == node_null:
            return None
        return XMLNode.create_from_cpp(node)

    @property
    def next_element_sibling(self):
        """Get next sibling that is an element node."""
        sibling = self.next_sibling
        while sibling and sibling.type != node_element:
            sibling = sibling.next_sibling
        return sibling
        
    @property
    def previous_element_sibling(self):
        """Get previous sibling that is an element node."""
        sibling = self.previous_sibling
        while sibling and sibling.type != node_element:
            sibling = sibling.previous_sibling
        return sibling

    @property
    def parent(self):
        """Get parent node"""
        cdef xml_node node = self._node.parent()
        return XMLNode.create_from_cpp(node)
    
    def first_attribute(self):
        """Get first attribute"""
        cdef xml_attribute attr = self._node.first_attribute()
        return XMLAttribute.create_from_cpp(attr)
    
    def attribute(self, str name):
        """Get attribute by name"""
        cdef bytes name_bytes = name.encode('utf-8')
        cdef xml_attribute attr = self._node.attribute(name_bytes)
        return XMLAttribute.create_from_cpp(attr)
    
    # XPath methods using XPathQuery internally
    def select_nodes(self, str query):
        """Select nodes using XPath query"""
        cdef XPathQuery xpath_query = XPathQuery(query)
        return xpath_query.evaluate_node_set(self)
    
    def select_node(self, str query):
        """Select single node using XPath query"""
        cdef XPathQuery xpath_query = XPathQuery(query)
        return xpath_query.evaluate_node(self)

    def is_null(self):
        """Return True if this node is null."""
        return self._node.type() == node_null
    
    @property
    def xpath(self):
        """Return the absolute XPath of this node (e.g., '/root/item[1]/name[1]')."""
        if self._node.type() != node_element:
            return ""
        cdef string xpath_str = get_xpath_for_node(self._node)
        return xpath_str.decode('utf-8')

    def to_string(self, indent="  "):
        """Serialize this node to XML string with custom indentation.
        
        Args:
            indent (str or int): Indentation string or number of spaces 
                                (default: two spaces)
            
        Returns:
            str: XML content as string
            
        Example:
            >>> node = doc.first_child()
            >>> # Default indentation (2 spaces)
            >>> xml_string = node.to_string()
            >>> # Custom string indentation
            >>> xml_string = node.to_string('    ')
            >>> # Number of spaces
            >>> xml_string = node.to_string(4)
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
        """XML representation with default indent (two spaces)."""
        return self.to_string()    
        
    def find_mem_id(self, size_t mem_id):
        cdef xml_node node = find_node_by_address(self._node, mem_id)
        return XMLNode.create_from_cpp(node)

    def text(self, bint recursive=True, str join="\n"):
        """Get the text content of this node."""
        if self._node.type() == node_null:
            return ""

        cdef list out = []  
        cdef xml_node current
        cdef xml_node_type ct
        cdef vector[xml_node] stack
        cdef xml_node child
        cdef string val

        if not recursive:
            current = self._node.first_child()
            while current.type() != node_null:
                ct = current.type()
                if ct == node_pcdata or ct == node_cdata:
                    val = current.value()
                    if not val.empty():
                        out.append(val.decode('utf-8'))
                current = current.next_sibling()
        else:
            current = self._node.first_child()
            while current.type() != node_null:
                stack.push_back(current)
                current = current.next_sibling()

            while stack.size() > 0:
                current = stack.back()
                stack.pop_back()

                ct = current.type()
                if ct == node_pcdata or ct == node_cdata:
                    val = current.value()
                    if not val.empty():
                        out.append(val.decode('utf-8'))
                elif ct in (node_element, node_document, node_declaration, node_doctype):
                    child = current.last_child()
                    while child.type() != node_null:
                        stack.push_back(child)
                        child = child.previous_sibling()

        return join.join(out)

    @property
    def mem_id(self):
        if self._node.type() == node_null:
            return 0
        return get_pugi_node_address(self._node)

    def __eq__(self, other: XMLNode) -> bool:
        if not isinstance(other, XMLNode):
            return False
        return self._node == other._node

    def __bool__(self):
        return self._node.type() != node_null

    def __iter__(self):
        """Iterate over all descendant nodes in DFS preorder."""
        if self._node.type() == node_null:
            return
        cdef vector[xml_node] stack
        stack.push_back(self._node)
        cdef xml_node current
        cdef xml_node child
        while stack.size() > 0:
            current = stack.back()
            stack.pop_back()
            yield XMLNode.create_from_cpp(current)
            # Traverse children in reverse order (right to left)
            child = current.last_child()
            while child.type() != node_null:
                stack.push_back(child)
                child = child.previous_sibling()
    

cdef class XMLAttribute:
    """XML attribute wrapper providing attribute operations.
    
    This class represents an XML attribute and provides methods for accessing
    and manipulating attribute properties.
    
    Example:
        >>> import pygixml
        >>> doc = pygixml.parse_string('<root id="123" name="test"/>')
        >>> root = doc.first_child()
        >>> attr = root.attribute('id')
        >>> print(attr.value)
        '123'
    """
    cdef xml_attribute _attr
    
    @staticmethod
    cdef XMLAttribute create_from_cpp(xml_attribute attr):
        cdef XMLAttribute wrapper = XMLAttribute()
        wrapper._attr = attr
        return wrapper
    
    @property
    def name(self):
        """Get attribute name.
        
        Returns:
            str: Attribute name or None if no name
            
        Example:
            >>> attr = node.attribute('id')
            >>> print(attr.name)
            'id'
        """
        cdef string name = self._attr.name()
        return name.decode('utf-8') if not name.empty() else None
    
    @property
    def value(self):
        """Get attribute value.
        
        Returns:
            str: Attribute value or None if no value
            
        Example:
            >>> attr = node.attribute('id')
            >>> print(attr.value)
            '123'
        """
        cdef string value = self._attr.value()
        return value.decode('utf-8') if not value.empty() else None
    
    def set_name(self, str name):
        """Set attribute name.
        
        Args:
            name (str): New name for the attribute
            
        Returns:
            bool: True if successful, False if attribute is null or invalid
            
        Example:
            >>> success = attr.set_name('new_name')
            >>> print(success)
            True
        """
        cdef bytes name_bytes = name.encode('utf-8')
        return self._attr.set_name(name_bytes)

    def set_value(self, str value):
        """Set attribute value.
        
        Args:
            value (str): New value for the attribute
            
        Returns:
            bool: True if successful, False if attribute is null or invalid
            
        Example:
            >>> success = attr.set_value('new_value')
            >>> print(success)
            True
        """
        cdef bytes value_bytes = value.encode('utf-8')
        return self._attr.set_value(value_bytes)

    @name.setter
    def name(self, str name):
        """Set attribute name.
        
        Args:
            name (str): New name for the attribute
            
        Raises:
            PygiXMLError: If attribute is null or invalid
            
        Example:
            >>> attr.name = 'new_name'
        """
        if not self.set_name(name):
            raise PygiXMLError("Cannot set attribute name")

    @value.setter
    def value(self, str value):
        """Set attribute value.
        
        Args:
            value (str): New value for the attribute
            
        Raises:
            PygiXMLError: If attribute is null or invalid
            
        Example:
            >>> attr.value = 'new_value'
        """
        if not self.set_value(value):
            raise PygiXMLError("Cannot set attribute value")

# XPath wrapper classes
cdef class XPathNode:
    """XPath node wrapper containing either an XML node or attribute.
    
    This class represents the result of an XPath query and can contain
    either an XML node or an XML attribute.
    
    Example:
        >>> import pygixml
        >>> doc = pygixml.parse_string('<root><item id="1">value</item></root>')
        >>> node = doc.select_node('//item')
        >>> print(node.node.name)
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
        """Get XML node from XPath node.
        
        Returns:
            XMLNode: XML node or None if this XPath node contains an attribute
            
        Example:
            >>> xpath_node = doc.select_node('//item')
            >>> node = xpath_node.node
            >>> print(node.name)
            'item'
        """
        cdef xml_node node = self._xpath_node.node()
        return XMLNode.create_from_cpp(node)
    
    @property
    def attribute(self):
        """Get XML attribute from XPath node.
        
        Returns:
            XMLAttribute: XML attribute or None if this XPath node contains a node
            
        Example:
            >>> xpath_node = doc.select_node('//item/@id')
            >>> attr = xpath_node.attribute
            >>> print(attr.value)
            '1'
        """
        cdef xml_attribute attr = self._xpath_node.attribute()
        return XMLAttribute.create_from_cpp(attr)
    
    @property
    def parent(self):
        """Get parent node of this XPath node.
        
        Returns:
            XMLNode: Parent node
            
        Example:
            >>> xpath_node = doc.select_node('//item/@id')
            >>> parent = xpath_node.parent
            >>> print(parent.name)
            'item'
        """
        cdef xml_node node = self._xpath_node.parent()
        return XMLNode.create_from_cpp(node)

cdef class XPathNodeSet:
    """XPath node set containing multiple XPath nodes.
    
    This class represents a collection of XPath nodes returned by
    an XPath query that matches multiple nodes.
    
    Example:
        >>> import pygixml
        >>> doc = pygixml.parse_string('<root><item>1</item><item>2</item></root>')
        >>> nodes = doc.select_nodes('//item')
        >>> for node in nodes:
        ...     print(node.node.text())
        1
        2
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
        """Get number of nodes in the set.
        
        Returns:
            int: Number of XPath nodes in the set
            
        Example:
            >>> nodes = doc.select_nodes('//item')
            >>> print(len(nodes))
            2
        """
        return self._xpath_node_set.size()
    
    def __getitem__(self, size_t index):
        """Get node at specified index.
        
        Args:
            index (int): Index of the node to retrieve
            
        Returns:
            XPathNode: XPath node at specified index
            
        Raises:
            IndexError: If index is out of range
            
        Example:
            >>> nodes = doc.select_nodes('//item')
            >>> first_node = nodes[0]
            >>> print(first_node.node.text())
            '1'
        """
        if index >= self._xpath_node_set.size():
            raise IndexError("XPath node set index out of range")
        cdef xpath_node node = self._xpath_node_set[index]
        return XPathNode.create_from_cpp(node)
    
    def __iter__(self):
        """Iterate over nodes in the set.
        
        Yields:
            XPathNode: Each XPath node in the set
            
        Example:
            >>> nodes = doc.select_nodes('//item')
            >>> for node in nodes:
            ...     print(node.node.text())
        """
        cdef size_t i
        for i in range(self._xpath_node_set.size()):
            yield self[i]

cdef class XPathQuery:
    """XPath query wrapper for evaluating XPath expressions.
    
    This class represents a compiled XPath query that can be evaluated
    against XML nodes to retrieve nodes, attributes, or values.
    
    Example:
        >>> import pygixml
        >>> doc = pygixml.parse_string('<root><item>value</item></root>')
        >>> query = pygixml.XPathQuery('//item')
        >>> result = query.evaluate_node(doc.first_child())
        >>> print(result.node.text())
        'value'
    """
    cdef xpath_query* _query
    
    def __cinit__(self, str query):
        """Create XPath query from string.
        
        Args:
            query (str): XPath expression string
            
        Example:
            >>> query = pygixml.XPathQuery('//item[@id="1"]')
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
def parse_string(str xml_string):
    """Parse XML from string and return XMLDocument.
    
    Args:
        xml_string (str): XML content as string
        
    Returns:
        XMLDocument: Parsed XML document
        
    Raises:
        PygiXMLError: If parsing fails
        
    Example:
        >>> import pygixml
        >>> doc = pygixml.parse_string('<root>content</root>')
        >>> print(doc.first_child().name)
        'root'
    """
    doc = XMLDocument()
    if doc.load_string(xml_string):
        return doc
    else:
        raise PygiXMLError("Failed to parse XML string")

def parse_file(str file_path):
    """Parse XML from file and return XMLDocument.
    
    Args:
        file_path (str): Path to XML file
        
    Returns:
        XMLDocument: Parsed XML document
        
    Raises:
        PygiXMLError: If parsing fails
        
    Example:
        >>> import pygixml
        >>> doc = pygixml.parse_file('data.xml')
        >>> print(doc.first_child().name)
        'root'
    """
    doc = XMLDocument()
    if doc.load_file(file_path):
        return doc
    else:
        raise PygiXMLError(f"Failed to parse XML file: {file_path}")
