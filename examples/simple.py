import pygixml
import time


# Parse XML from string
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

print(root.name)


book = root.child("book")
title = book.child("title")
print(book.xml)
print(title.xml)


print(title.parent == book)

print(title.parent.mem_id == book.mem_id)


for tag in root:
    tstart = time.time_ns()
    xpath  = tag.xpath
    tstop  = time.time_ns()

    elapsed = tstop - tstart

    print(tag.name, xpath, f"{elapsed/1e3} us")
    if xpath: print(root.select_node(xpath).node.xml)