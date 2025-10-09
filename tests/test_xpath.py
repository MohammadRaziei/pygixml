"""
Tests for XPath functionality in pygixml
"""

import pytest
import pygixml


class TestXPath:
    """Test XPath query functionality"""
    
    def test_select_nodes_basic(self):
        """Test basic XPath node selection"""
        xml_string = """
        <library>
            <book id="1">
                <title>The Great Gatsby</title>
                <author>F. Scott Fitzgerald</author>
                <year>1925</year>
            </book>
            <book id="2">
                <title>1984</title>
                <author>George Orwell</author>
                <year>1949</year>
            </book>
        </library>
        """
        
        doc = pygixml.parse_string(xml_string)
        root = doc.first_child()
        
        # Select all book nodes
        books = root.select_nodes("book")
        assert len(books) == 2
        
        # Check book titles
        titles = []
        for book in books:
            title_node = book.node().child("title")
            titles.append(title_node.child_value())
        
        assert "The Great Gatsby" in titles
        assert "1984" in titles
    
    def test_select_node_single(self):
        """Test selecting a single node with XPath"""
        xml_string = """
        <library>
            <book id="1">
                <title>The Great Gatsby</title>
                <author>F. Scott Fitzgerald</author>
            </book>
            <book id="2">
                <title>1984</title>
                <author>George Orwell</author>
            </book>
        </library>
        """
        
        doc = pygixml.parse_string(xml_string)
        root = doc.first_child()
        
        # Select first book
        first_book = root.select_node("book[1]")
        assert first_book.node().child("title").child_value() == "The Great Gatsby"
        
        # Select book by attribute
        book_by_id = root.select_node("book[@id='2']")
        assert book_by_id.node().child("title").child_value() == "1984"
    
    def test_select_by_attribute(self):
        """Test XPath queries using attributes"""
        xml_string = """
        <employees>
            <employee id="101" department="IT">
                <name>Alice</name>
                <salary>50000</salary>
            </employee>
            <employee id="102" department="HR">
                <name>Bob</name>
                <salary>45000</salary>
            </employee>
            <employee id="103" department="IT">
                <name>Charlie</name>
                <salary>55000</salary>
            </employee>
        </employees>
        """
        
        doc = pygixml.parse_string(xml_string)
        root = doc.first_child()
        
        # Select IT employees
        it_employees = root.select_nodes("employee[@department='IT']")
        assert len(it_employees) == 2
        
        # Select employee by ID
        employee_102 = root.select_node("employee[@id='102']")
        assert employee_102.node().child("name").child_value() == "Bob"
    
    def test_select_child_values(self):
        """Test XPath queries for child values"""
        xml_string = """
        <catalog>
            <product>
                <name>Laptop</name>
                <price>999.99</price>
                <category>Electronics</category>
            </product>
            <product>
                <name>Book</name>
                <price>19.99</price>
                <category>Education</category>
            </product>
            <product>
                <name>Phone</name>
                <price>699.99</price>
                <category>Electronics</category>
            </product>
        </catalog>
        """
        
        doc = pygixml.parse_string(xml_string)
        root = doc.first_child()
        
        # Select electronics products
        electronics = root.select_nodes("product[category='Electronics']")
        assert len(electronics) == 2
        
        # Get product names
        names = []
        for product in electronics:
            name = product.node().child("name").child_value()
            names.append(name)
        
        assert "Laptop" in names
        assert "Phone" in names
        assert "Book" not in names
    
    def test_xpath_query_object(self):
        """Test using XPathQuery object for repeated queries"""
        xml_string = """
        <inventory>
            <item>
                <name>Widget A</name>
                <stock>50</stock>
            </item>
            <item>
                <name>Widget B</name>
                <stock>25</stock>
            </item>
            <item>
                <name>Widget C</name>
                <stock>75</stock>
            </item>
        </inventory>
        """
        
        doc = pygixml.parse_string(xml_string)
        root = doc.first_child()
        
        # Create XPath query
        query = pygixml.XPathQuery("item[stock > 30]")
        
        # Evaluate query
        result = query.evaluate_node_set(root)
        assert len(result) == 2
        
        # Get item names
        names = []
        for item in result:
            name = item.node().child("name").child_value()
            names.append(name)
        
        assert "Widget A" in names
        assert "Widget C" in names
        assert "Widget B" not in names
    
    def test_xpath_boolean_evaluation(self):
        """Test XPath boolean evaluation"""
        xml_string = """
        <data>
            <value>42</value>
            <flag>true</flag>
        </data>
        """
        
        doc = pygixml.parse_string(xml_string)
        root = doc.first_child()
        
        query = pygixml.XPathQuery("value = 42")
        result = query.evaluate_boolean(root)
        assert result is True
        
        query = pygixml.XPathQuery("value > 50")
        result = query.evaluate_boolean(root)
        assert result is False
    
    def test_xpath_number_evaluation(self):
        """Test XPath number evaluation"""
        xml_string = """
        <data>
            <value>42</value>
            <price>19.99</price>
        </data>
        """
        
        doc = pygixml.parse_string(xml_string)
        root = doc.first_child()
        
        query = pygixml.XPathQuery("value")
        result = query.evaluate_number(root)
        assert result == 42.0
        
        query = pygixml.XPathQuery("price")
        result = query.evaluate_number(root)
        assert result == 19.99
    
    def test_xpath_string_evaluation(self):
        """Test XPath string evaluation"""
        xml_string = """
        <data>
            <message>Hello, World!</message>
            <empty></empty>
        </data>
        """
        
        doc = pygixml.parse_string(xml_string)
        root = doc.first_child()
        
        query = pygixml.XPathQuery("message")
        result = query.evaluate_string(root)
        assert result == "Hello, World!"
        
        query = pygixml.XPathQuery("empty")
        result = query.evaluate_string(root)
        assert result is None or result == ""
    
    def test_xpath_node_attributes(self):
        """Test XPath queries involving attributes"""
        xml_string = """
        <users>
            <user id="1" active="true">
                <name>John</name>
            </user>
            <user id="2" active="false">
                <name>Jane</name>
            </user>
            <user id="3" active="true">
                <name>Bob</name>
            </user>
        </users>
        """
        
        doc = pygixml.parse_string(xml_string)
        root = doc.first_child()
        
        # Select active users
        active_users = root.select_nodes("user[@active='true']")
        assert len(active_users) == 2
        
        # Select user by ID
        user_2 = root.select_node("user[@id='2']")
        assert user_2.node().child("name").child_value() == "Jane"
        
        # Select inactive users
        inactive_users = root.select_nodes("user[@active='false']")
        assert len(inactive_users) == 1
        assert inactive_users[0].node().child("name").child_value() == "Jane"
    
    def test_xpath_position_functions(self):
        """Test XPath position functions"""
        xml_string = """
        <items>
            <item>First</item>
            <item>Second</item>
            <item>Third</item>
            <item>Fourth</item>
        </items>
        """
        
        doc = pygixml.parse_string(xml_string)
        root = doc.first_child()
        
        # Select first item
        first_item = root.select_node("item[1]")
        assert first_item.node().child_value() == "First"
        
        # Select last item
        last_item = root.select_node("item[last()]")
        assert last_item.node().child_value() == "Fourth"
        
        # Select items by position
        items = root.select_nodes("item[position() > 2]")
        assert len(items) == 2
        values = [item.node().child_value() for item in items]
        assert "Third" in values
        assert "Fourth" in values
