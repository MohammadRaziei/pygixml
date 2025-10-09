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
        
    # XPath methods for xml_node
    cdef cppclass xml_node:
        xpath_node select_node(const char* query, xpath_variable_set* variables = NULL) const
        xpath_node_set select_nodes(const char* query, xpath_variable_set* variables = NULL) const

# Python wrapper classes
cdef class XMLDocument:
    cdef xml_document* _doc
    
    def __cinit__(self):
        self._doc = new xml_document()
    
    def __dealloc__(self):
        if self._doc != NULL:
            del self._doc
    
    def load_string(self, str content):
        """Load XML from string"""
        cdef bytes content_bytes = content.encode('utf-8')
        return self._doc.load_string(content_bytes)
    
    def load_file(self, str path):
        """Load XML from file"""
        cdef bytes path_bytes = path.encode('utf-8')
        return self._doc.load_file(path_bytes)
    
    def save_file(self, str path, str indent="  "):
        """Save XML to file"""
        cdef bytes path_bytes = path.encode('utf-8')
        cdef bytes indent_bytes = indent.encode('utf-8')
        self._doc.save_file(path_bytes, indent_bytes)
    
    
    def reset(self):
        """Reset the document"""
        self._doc.reset()
    
    def append_child(self, str name):
        """Append a child node"""
        cdef bytes name_bytes = name.encode('utf-8')
        cdef xml_node node = self._doc.append_child(name_bytes)
        return XMLNode.create_from_cpp(node)
    
    def first_child(self):
        """Get first child node"""
        cdef xml_node node = self._doc.first_child()
        return XMLNode.create_from_cpp(node)
    
    def child(self, str name):
        """Get child node by name"""
        cdef bytes name_bytes = name.encode('utf-8')
        cdef xml_node node = self._doc.child(name_bytes)
        return XMLNode.create_from_cpp(node)

cdef class XMLNode:
    cdef xml_node _node
    
    @staticmethod
    cdef XMLNode create_from_cpp(xml_node node):
        cdef XMLNode wrapper = XMLNode()
        wrapper._node = node
        return wrapper
    
    def name(self):
        """Get node name"""
        cdef string name = self._node.name()
        return name.decode('utf-8') if not name.empty() else None
    
    def value(self):
        """Get node value"""
        cdef string value = self._node.value()
        return value.decode('utf-8') if not value.empty() else None
    
    def set_name(self, str name):
        """Set node name"""
        cdef bytes name_bytes = name.encode('utf-8')
        return self._node.set_name(name_bytes)
    
    def set_value(self, str value):
        """Set node value"""
        cdef bytes value_bytes = value.encode('utf-8')
        success = self._node.set_value(value_bytes)
        return success
    
    def first_child(self):
        """Get first child node"""
        cdef xml_node node = self._node.first_child()
        return XMLNode.create_from_cpp(node)
    
    def child(self, str name):
        """Get child node by name"""
        cdef bytes name_bytes = name.encode('utf-8')
        cdef xml_node node = self._node.child(name_bytes)
        return XMLNode.create_from_cpp(node)
    
    def append_child(self, str name):
        """Append a child node"""
        cdef bytes name_bytes = name.encode('utf-8')
        cdef xml_node node = self._node.append_child(name_bytes)
        return XMLNode.create_from_cpp(node)
    
    def child_value(self, str name=None):
        """Get child value"""
        cdef string value
        cdef bytes name_bytes
        
        if name is None:
            value = self._node.child_value()
            return value.decode('utf-8') if not value.empty() else None
        else:
            name_bytes = name.encode('utf-8')
            value = self._node.child_value(name_bytes)
            return value.decode('utf-8') if not value.empty() else None
    
    def next_sibling(self):
        """Get next sibling node"""
        cdef xml_node node = self._node.next_sibling()
        # Check if the node is empty (no more siblings) by checking if name is empty
        cdef string node_name = node.name()
        if node_name.empty():
            return None
        return XMLNode.create_from_cpp(node)
    
    def previous_sibling(self):
        """Get previous sibling node"""
        cdef xml_node node = self._node.previous_sibling()
        return XMLNode.create_from_cpp(node)
    
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
    

cdef class XMLAttribute:
    cdef xml_attribute _attr
    
    @staticmethod
    cdef XMLAttribute create_from_cpp(xml_attribute attr):
        cdef XMLAttribute wrapper = XMLAttribute()
        wrapper._attr = attr
        return wrapper
    
    def name(self):
        """Get attribute name"""
        cdef string name = self._attr.name()
        return name.decode('utf-8') if not name.empty() else None
    
    def value(self):
        """Get attribute value"""
        cdef string value = self._attr.value()
        return value.decode('utf-8') if not value.empty() else None
    
    def set_name(self, str name):
        """Set attribute name"""
        cdef bytes name_bytes = name.encode('utf-8')
        return self._attr.set_name(name_bytes)
    
    def set_value(self, str value):
        """Set attribute value"""
        cdef bytes value_bytes = value.encode('utf-8')
        return self._attr.set_value(value_bytes)

# XPath wrapper classes
cdef class XPathNode:
    cdef xpath_node _xpath_node
    
    @staticmethod
    cdef XPathNode create_from_cpp(xpath_node xpath_node):
        cdef XPathNode wrapper = XPathNode()
        wrapper._xpath_node = xpath_node
        return wrapper
    
    def node(self):
        """Get XML node from XPath node"""
        cdef xml_node node = self._xpath_node.node()
        return XMLNode.create_from_cpp(node)
    
    def attribute(self):
        """Get XML attribute from XPath node"""
        cdef xml_attribute attr = self._xpath_node.attribute()
        return XMLAttribute.create_from_cpp(attr)
    
    def parent(self):
        """Get parent node"""
        cdef xml_node node = self._xpath_node.parent()
        return XMLNode.create_from_cpp(node)

cdef class XPathNodeSet:
    cdef xpath_node_set _xpath_node_set
    
    def __cinit__(self):
        self._xpath_node_set = xpath_node_set()
    
    @staticmethod
    cdef XPathNodeSet create_from_cpp(xpath_node_set xpath_node_set):
        cdef XPathNodeSet wrapper = XPathNodeSet()
        wrapper._xpath_node_set = xpath_node_set
        return wrapper
    
    def __len__(self):
        """Get number of nodes in the set"""
        return self._xpath_node_set.size()
    
    def __getitem__(self, size_t index):
        """Get node at specified index"""
        if index >= self._xpath_node_set.size():
            raise IndexError("XPath node set index out of range")
        cdef xpath_node node = self._xpath_node_set[index]
        return XPathNode.create_from_cpp(node)
    
    def __iter__(self):
        """Iterate over nodes in the set"""
        cdef size_t i
        for i in range(self._xpath_node_set.size()):
            yield self[i]

cdef class XPathQuery:
    cdef xpath_query* _query
    
    def __cinit__(self, str query):
        """Create XPath query from string"""
        cdef bytes query_bytes = query.encode('utf-8')
        self._query = new xpath_query(query_bytes)
    
    def __dealloc__(self):
        if self._query != NULL:
            del self._query
    
    def evaluate_node_set(self, XMLNode context_node):
        """Evaluate query and return node set"""
        cdef xpath_node_set result = self._query.evaluate_node_set(context_node._node)
        return XPathNodeSet.create_from_cpp(result)
    
    def evaluate_node(self, XMLNode context_node):
        """Evaluate query and return first node"""
        cdef xpath_node result = self._query.evaluate_node(context_node._node)
        return XPathNode.create_from_cpp(result)
    
    def evaluate_boolean(self, XMLNode context_node):
        """Evaluate query and return boolean result"""
        return self._query.evaluate_boolean(context_node._node)
    
    def evaluate_number(self, XMLNode context_node):
        """Evaluate query and return numeric result"""
        return self._query.evaluate_number(context_node._node)
    
    def evaluate_string(self, XMLNode context_node):
        """Evaluate query and return string result"""
        cdef string result = self._query.evaluate_string(context_node._node)
        return result.decode('utf-8') if not result.empty() else None

# Convenience functions
def parse_string(str xml_string):
    """Parse XML from string and return XMLDocument"""
    doc = XMLDocument()
    if doc.load_string(xml_string):
        return doc
    else:
        raise ValueError("Failed to parse XML string")

def parse_file(str file_path):
    """Parse XML from file and return XMLDocument"""
    doc = XMLDocument()
    if doc.load_file(file_path):
        return doc
    else:
        raise ValueError(f"Failed to parse XML file: {file_path}")
