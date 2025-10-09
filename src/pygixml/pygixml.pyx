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
