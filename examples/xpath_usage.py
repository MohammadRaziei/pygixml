#!/usr/bin/env python3
"""
Example demonstrating XPath functionality in pygixml
"""

import pygixml


def main():
    print("=== XPath Examples with pygixml ===\n")
    
    # Example XML data
    xml_string = """
    <library>
        <book id="1" category="fiction">
            <title>The Great Gatsby</title>
            <author>F. Scott Fitzgerald</author>
            <year>1925</year>
            <price>12.99</price>
        </book>
        <book id="2" category="fiction">
            <title>1984</title>
            <author>George Orwell</author>
            <year>1949</year>
            <price>10.99</price>
        </book>
        <book id="3" category="non-fiction">
            <title>A Brief History of Time</title>
            <author>Stephen Hawking</author>
            <year>1988</year>
            <price>15.99</price>
        </book>
        <book id="4" category="fiction">
            <title>To Kill a Mockingbird</title>
            <author>Harper Lee</author>
            <year>1960</year>
            <price>11.99</price>
        </book>
    </library>
    """
    
    # Parse XML
    doc = pygixml.parse_string(xml_string)
    root = doc.first_child()
    
    print("1. Select all books:")
    books = root.select_nodes("book")
    print(f"   Found {len(books)} books")
    
    print("\n2. Select fiction books:")
    fiction_books = root.select_nodes("book[@category='fiction']")
    print(f"   Found {len(fiction_books)} fiction books")
    for book in fiction_books:
        title = book.node().child("title").child_value()
        print(f"   - {title}")
    
    print("\n3. Select books published after 1950:")
    recent_books = root.select_nodes("book[year > 1950]")
    print(f"   Found {len(recent_books)} books published after 1950")
    for book in recent_books:
        title = book.node().child("title").child_value()
        year = book.node().child("year").child_value()
        print(f"   - {title} ({year})")
    
    print("\n4. Select expensive books (price > 12):")
    expensive_books = root.select_nodes("book[price > 12]")
    print(f"   Found {len(expensive_books)} expensive books")
    for book in expensive_books:
        title = book.node().child("title").child_value()
        price = book.node().child("price").child_value()
        print(f"   - {title} (${price})")
    
    print("\n5. Select specific book by ID:")
    book_2 = root.select_node("book[@id='2']")
    if book_2:
        title = book_2.node().child("title").child_value()
        author = book_2.node().child("author").child_value()
        print(f"   Book ID 2: {title} by {author}")
    
    print("\n6. Using XPathQuery object for repeated queries:")
    query = pygixml.XPathQuery("book[author='George Orwell']")
    orwell_books = query.evaluate_node_set(root)
    print(f"   Found {len(orwell_books)} books by George Orwell")
    for book in orwell_books:
        title = book.node().child("title").child_value()
        print(f"   - {title}")
    
    print("\n7. XPath boolean evaluation:")
    has_orwell = pygixml.XPathQuery("book[author='George Orwell']").evaluate_boolean(root)
    print(f"   Has George Orwell books: {has_orwell}")
    
    print("\n8. XPath number evaluation:")
    avg_price = pygixml.XPathQuery("sum(book/price) div count(book)").evaluate_number(root)
    print(f"   Average book price: ${avg_price:.2f}")
    
    print("\n9. XPath string evaluation:")
    first_title = pygixml.XPathQuery("book[1]/title").evaluate_string(root)
    print(f"   First book title: {first_title}")
    
    print("\n10. Complex XPath query:")
    # Books by Fitzgerald published before 1930
    complex_query = pygixml.XPathQuery("book[author='F. Scott Fitzgerald' and year < 1930]")
    fitzgerald_books = complex_query.evaluate_node_set(root)
    print(f"   Found {len(fitzgerald_books)} Fitzgerald books before 1930")
    for book in fitzgerald_books:
        title = book.node().child("title").child_value()
        year = book.node().child("year").child_value()
        print(f"   - {title} ({year})")
    
    print("\n🎉 All XPath examples completed successfully!")


if __name__ == "__main__":
    main()
