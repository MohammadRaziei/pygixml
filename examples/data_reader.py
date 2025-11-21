import os
import pygixml

# Path to XML file next to this script
current_dir = os.path.dirname(__file__)
xml_path = os.path.join(current_dir, "data.xml")

# Parse XML
doc = pygixml.parse_file(xml_path)

root = doc.root
print(root.xml)

# Iterate over nodes
for node in doc:
    print("---")
    print("TAG:", node.name)
    print("XPATH:", node.xpath)
    print("type:", node.type)
    print("TEXT:", node.text(recursive=False))
    print("XML:", node.xml)
    print("mem_id:", node.mem_id)
