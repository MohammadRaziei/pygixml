Examples
========

This page contains practical examples of using pygixml for common XML
processing tasks.

Basic Examples
--------------

Parsing and Navigating
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pygixml

   xml_data = '''
   <catalog>
       <book id="bk101">
           <author>Gambardella, Matthew</author>
           <title>XML Developer's Guide</title>
           <genre>Computer</genre>
           <price>44.95</price>
           <publish_date>2000-10-01</publish_date>
       </book>
       <book id="bk102">
           <author>Ralls, Kim</author>
           <title>Midnight Rain</title>
           <genre>Fantasy</genre>
           <price>5.95</price>
           <publish_date>2000-12-16</publish_date>
       </book>
   </catalog>
   '''

   doc = pygixml.parse_string(xml_data)
   catalog = doc.root

   # Walk through books using the document iterator
   for book in doc:
       if book.name == "book":
           title = book.child("title").text()
           author = book.child("author").text()
           price = book.child("price").text()
           print(f"{title} by {author} - ${price}")

   # Or use XPath to select all books directly
   for book in catalog.select_nodes("book"):
       title = book.node.child("title").text()
       author = book.node.child("author").text()
       print(f"{title} by {author}")

Working with Attributes
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pygixml

   doc = pygixml.parse_string(
       '<products>'
       '  <product id="1" name="Laptop" price="999.99"/>'
       '  <product id="2" name="Mouse" price="29.99"/>'
       '</products>'
   )
   root = doc.root

   product = root.child("product")
   print(product.attribute("id").value)       # → 1
   print(product.attribute("name").value)     # → Laptop

   # Iterate all attributes
   attr = product.first_attribute()
   while attr:
       print(f"  {attr.name} = {attr.value}")
       attr = attr.next_attribute

Creating XML Documents
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pygixml

   doc = pygixml.XMLDocument()
   catalog = doc.append_child("catalog")

   book1 = catalog.append_child("book")
   book1.append_child("author").set_value("Gambardella, Matthew")
   book1.append_child("title").set_value("XML Developer's Guide")
   book1.append_child("genre").set_value("Computer")
   book1.append_child("price").set_value("44.95")

   book2 = catalog.append_child("book")
   book2.append_child("author").set_value("Ralls, Kim")
   book2.append_child("title").set_value("Midnight Rain")
   book2.append_child("price").set_value("5.95")

   doc.save_file("catalog.xml")

.. note::
   Attribute *creation* is not yet exposed in the Python API.  When you need
   attributes, build the document by parsing a string instead:

   .. code-block:: python

      doc = pygixml.parse_string(
          '<catalog>'
          '  <book id="bk101">'
          '    <author>Gambardella, Matthew</author>'
          '  </book>'
          '</catalog>'
      )

Modifying Existing XML
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pygixml

   doc = pygixml.parse_string(
       '<employees>'
       '  <employee>'
       '    <name>John Doe</name>'
       '    <position>Developer</position>'
       '    <salary>50000</salary>'
       '  </employee>'
       '</employees>'
   )
   root = doc.root
   employee = root.child("employee")

   # Change values
   employee.child("name").set_value("Jane Smith")
   employee.child("salary").set_value("55000")

   # Add a new element
   employee.append_child("department").set_value("Engineering")

   # Rename an element
   employee.child("position").name = "role"

   # Print result
   print(root.to_string())

Advanced Examples
-----------------

XML Data Processing
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pygixml

   sales_xml = '''
   <sales>
       <region name="North">
           <product id="1" category="Electronics">
               <name>Laptop</name>
               <price>999.99</price>
               <units_sold>45</units_sold>
           </product>
           <product id="2" category="Books">
               <name>Python Programming</name>
               <price>49.99</price>
               <units_sold>120</units_sold>
           </product>
       </region>
       <region name="South">
           <product id="1" category="Electronics">
               <name>Laptop</name>
               <price>999.99</price>
               <units_sold>32</units_sold>
           </product>
           <product id="3" category="Clothing">
               <name>T-Shirt</name>
               <price>19.99</price>
               <units_sold>200</units_sold>
           </product>
       </region>
   </sales>
   '''

   doc = pygixml.parse_string(sales_xml)
   sales = doc.root

   # Total revenue by region
   regions = sales.select_nodes("region")
   for region in regions:
       region_name = region.node.attribute("name").value
       products = region.node.select_nodes("product")

       total_revenue = 0.0
       for product in products:
           price = float(product.node.child("price").text())
           units = int(product.node.child("units_sold").text())
           total_revenue += price * units

       print(f"Region {region_name}: ${total_revenue:,.2f}")

   # Best-selling product across all regions
   best_product = None
   max_units = 0

   for product in sales.select_nodes("//product"):
       units = int(product.node.child("units_sold").text())
       if units > max_units:
           max_units = units
           best_product = product.node

   if best_product:
       name = best_product.child("name").text()
       print(f"Best-selling: {name} ({max_units} units)")

XML Configuration Processing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pygixml

   config_xml = '''
   <config>
       <database>
           <host>localhost</host>
           <port>5432</port>
           <name>mydb</name>
           <user>admin</user>
       </database>
       <server>
           <host>0.0.0.0</host>
           <port>8080</port>
           <debug>true</debug>
           <log_level>INFO</log_level>
       </server>
       <features>
           <feature name="authentication" enabled="true"/>
           <feature name="caching" enabled="false"/>
           <feature name="compression" enabled="true"/>
       </features>
   </config>
   '''

   doc = pygixml.parse_string(config_xml)
   config = doc.root

   # Database configuration
   db = config.child("database")
   db_config = {
       "host": db.child("host").text(),
       "port": int(db.child("port").text()),
       "name": db.child("name").text(),
       "user": db.child("user").text(),
   }
   print("Database:", db_config)

   # Server configuration
   server = config.child("server")
   server_config = {
       "host": server.child("host").text(),
       "port": int(server.child("port").text()),
       "debug": server.child("debug").text().lower() == "true",
       "log_level": server.child("log_level").text(),
   }
   print("Server:", server_config)

   # Enabled features via XPath
   enabled = config.select_nodes("features/feature[@enabled='true']")
   print("Enabled:", [f.node.attribute("name").value for f in enabled])

XPath Complex Queries
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pygixml

   company_xml = '''
   <company>
       <department name="Engineering">
           <team name="Frontend">
               <employee id="101" level="senior">
                   <name>Alice Smith</name>
                   <salary>120000</salary>
                   <skills>
                       <skill>JavaScript</skill>
                       <skill>React</skill>
                   </skills>
               </employee>
               <employee id="102" level="junior">
                   <name>Bob Johnson</name>
                   <salary>80000</salary>
                   <skills>
                       <skill>HTML</skill>
                       <skill>CSS</skill>
                   </skills>
               </employee>
           </team>
           <team name="Backend">
               <employee id="201" level="senior">
                   <name>Charlie Brown</name>
                   <salary>130000</salary>
                   <skills>
                       <skill>Python</skill>
                       <skill>Django</skill>
                   </skills>
               </employee>
           </team>
       </department>
       <department name="Sales">
           <team name="Enterprise">
               <employee id="301" level="senior">
                   <name>Diana Prince</name>
                   <salary>110000</salary>
               </employee>
           </team>
       </department>
   </company>
   '''

   doc = pygixml.parse_string(company_xml)
   company = doc.root

   # All senior employees
   seniors = company.select_nodes("//employee[@level='senior']")
   print(f"Senior employees: {len(seniors)}")

   # Python developers
   python_devs = company.select_nodes("//employee[skills/skill='Python']")
   print(f"Python developers: {len(python_devs)}")

   # Average salary per department
   for dept in company.select_nodes("department"):
       dept_name = dept.node.attribute("name").value
       employees = dept.node.select_nodes(".//employee")

       if employees:
           total = sum(
               float(e.node.child("salary").text()) for e in employees
           )
           print(f"{dept_name} avg salary: ${total / len(employees):,.0f}")

   # High earners (>100k)
   for emp in company.select_nodes("//employee[salary > 100000]"):
       name = emp.node.child("name").text()
       salary = emp.node.child("salary").text()
       print(f"  {name}: ${salary}")

Real-World Use Cases
--------------------

Product Data Extraction
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pygixml

   xml_content = '''
   <products>
       <product>
           <name>Wireless Mouse</name>
           <price currency="USD">29.99</price>
           <category>Electronics</category>
           <rating>4.5</rating>
           <reviews>128</reviews>
       </product>
       <product>
           <name>Mechanical Keyboard</name>
           <price currency="USD">89.99</price>
           <category>Electronics</category>
           <rating>4.8</rating>
           <reviews>64</reviews>
       </product>
   </products>
   '''

   doc = pygixml.parse_string(xml_content)
   root = doc.root

   products = []
   for p in root.select_nodes("product"):
       n = p.node
       price_el = n.child("price")
       products.append({
           "name":     n.child("name").text(),
           "price":    float(price_el.text()),
           "currency": price_el.attribute("currency").value,
           "rating":   float(n.child("rating").text()),
           "reviews":  int(n.child("reviews").text()),
       })

   # Sort by rating
   products.sort(key=lambda x: x["rating"], reverse=True)
   for p in products:
       print(f"{p['name']}: ${p['price']} ({p['rating']} stars)")

API Response Processing
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pygixml

   weather_xml = '''
   <weather>
       <location>
           <city>New York</city>
           <country>US</country>
       </location>
       <current>
           <temperature unit="celsius">22</temperature>
           <humidity unit="percent">65</humidity>
           <condition>Partly Cloudy</condition>
       </current>
       <forecast>
           <day date="2025-10-10">
               <high>24</high>
               <low>18</low>
               <condition>Sunny</condition>
           </day>
           <day date="2025-10-11">
               <high>21</high>
               <low>16</low>
               <condition>Rain</condition>
           </day>
       </forecast>
   </weather>
   '''

   doc = pygixml.parse_string(weather_xml)
   w = doc.root

   location = w.child("location")
   current  = w.child("current")

   city = location.child("city").text()
   temp = current.child("temperature").text()
   cond = current.child("condition").text()
   print(f"Current in {city}: {temp}°C, {cond}")

   # Forecast
   for day in w.select_nodes("forecast/day"):
       d = day.node
       date = d.attribute("date").value
       high = d.child("high").text()
       low  = d.child("low").text()
       cnd  = d.child("condition").text()
       print(f"  {date}: {high}°C / {low}°C, {cnd}")

HTML-like Processing
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pygixml

   # pygixml can parse well-formed HTML/XML fragments
   html = '''
   <html>
       <head><title>My Page</title></head>
       <body>
           <h1>Welcome</h1>
           <p>Hello <b>world</b>!</p>
           <ul>
               <li>Item one</li>
               <li>Item two</li>
           </ul>
       </body>
   </html>
   '''

   doc = pygixml.parse_string(html)

   # Extract all text from <body>
   body = doc.select_node("//body").node
   print(body.text())        # → Welcome\nHello world!\nItem one\nItem two

   # Extract only direct text (non-recursive)
   print(body.text(recursive=False))   # → \n\n

   # Get all <li> items
   for li in body.select_nodes(".//li"):
       print(li.node.text())

Running Examples
----------------

All examples in this documentation can be run directly:

.. code-block:: bash

   pip install pygixml

Then copy any example into a Python file and run it:

.. code-block:: bash

   python example.py

For interactive examples, check the ``examples/`` directory in the pygixml
repository.
