Examples
========

This page contains practical examples of using pygixml for common XML processing tasks.

Basic Examples
--------------

Parsing and Navigating
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pygixml

   # Example XML
   xml_data = '''
   <catalog>
       <book id="bk101">
           <author>Gambardella, Matthew</author>
           <title>XML Developer's Guide</title>
           <genre>Computer</genre>
           <price>44.95</price>
           <publish_date>2000-10-01</publish_date>
           <description>An in-depth look at creating applications with XML.</description>
       </book>
       <book id="bk102">
           <author>Ralls, Kim</author>
           <title>Midnight Rain</title>
           <genre>Fantasy</genre>
           <price>5.95</price>
           <publish_date>2000-12-16</publish_date>
           <description>A former architect battles corporate zombies.</description>
       </book>
   </catalog>
   '''

   # Parse XML
   doc = pygixml.parse_string(xml_data)
   catalog = doc.first_child()

   # Print all books
   books = catalog.select_nodes("book")
   for book in books:
       title = book.node().child("title").child_value()
       author = book.node().child("author").child_value()
       price = book.node().child("price").child_value()
       print(f"{title} by {author} - ${price}")

Creating XML Documents
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pygixml

   # Create new document
   doc = pygixml.XMLDocument()

   # Add catalog root
   catalog = doc.append_child("catalog")

   # Add first book
   book1 = catalog.append_child("book")
   book1.set_attribute("id", "bk101")
   
   book1.append_child("author").set_value("Gambardella, Matthew")
   book1.append_child("title").set_value("XML Developer's Guide")
   book1.append_child("genre").set_value("Computer")
   book1.append_child("price").set_value("44.95")
   book1.append_child("publish_date").set_value("2000-10-01")
   book1.append_child("description").set_value("An in-depth look at creating applications with XML.")

   # Add second book
   book2 = catalog.append_child("book")
   book2.set_attribute("id", "bk102")
   
   book2.append_child("author").set_value("Ralls, Kim")
   book2.append_child("title").set_value("Midnight Rain")
   book2.append_child("genre").set_value("Fantasy")
   book2.append_child("price").set_value("5.95")
   book2.append_child("publish_date").set_value("2000-12-16")
   book2.append_child("description").set_value("A former architect battles corporate zombies.")

   # Save to file
   doc.save_file("catalog.xml")

Advanced Examples
-----------------

XML Data Processing
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pygixml

   # Process sales data
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
   sales = doc.first_child()

   # Calculate total revenue by region
   regions = sales.select_nodes("region")
   for region in regions:
       region_name = region.node().attribute("name").value()
       products = region.node().select_nodes("product")
       
       total_revenue = 0
       for product in products:
           price = float(product.node().child("price").child_value())
           units = int(product.node().child("units_sold").child_value())
           total_revenue += price * units
       
       print(f"Region {region_name}: ${total_revenue:.2f}")

   # Find best-selling product
   all_products = sales.select_nodes("//product")
   best_product = None
   max_units = 0

   for product in all_products:
       units = int(product.node().child("units_sold").child_value())
       if units > max_units:
           max_units = units
           best_product = product.node()

   if best_product:
       name = best_product.child("name").child_value()
       print(f"Best-selling product: {name} ({max_units} units)")

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
           <password>secret</password>
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
   config = doc.first_child()

   # Extract database configuration
   db_config = {}
   database = config.child("database")
   db_config['host'] = database.child("host").child_value()
   db_config['port'] = int(database.child("port").child_value())
   db_config['name'] = database.child("name").child_value()
   db_config['user'] = database.child("user").child_value()
   db_config['password'] = database.child("password").child_value()

   print("Database Config:", db_config)

   # Extract server configuration
   server_config = {}
   server = config.child("server")
   server_config['host'] = server.child("host").child_value()
   server_config['port'] = int(server.child("port").child_value())
   server_config['debug'] = server.child("debug").child_value().lower() == 'true'
   server_config['log_level'] = server.child("log_level").child_value()

   print("Server Config:", server_config)

   # Check enabled features
   enabled_features = []
   features = config.select_nodes("features/feature[@enabled='true']")
   for feature in features:
       feature_name = feature.node().attribute("name").value()
       enabled_features.append(feature_name)

   print("Enabled features:", enabled_features)

XPath Complex Queries
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pygixml

   # Complex XML with nested structure
   complex_xml = '''
   <company>
       <department name="Engineering">
           <team name="Frontend">
               <employee id="101" level="senior">
                   <name>Alice Smith</name>
                   <salary>120000</salary>
                   <skills>
                       <skill>JavaScript</skill>
                       <skill>React</skill>
                       <skill>TypeScript</skill>
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
                       <skill>PostgreSQL</skill>
                   </skills>
               </employee>
           </team>
       </department>
       <department name="Sales">
           <team name="Enterprise">
               <employee id="301" level="senior">
                   <name>Diana Prince</name>
                   <salary>110000</salary>
                   <skills>
                       <skill>Negotiation</skill>
                       <skill>CRM</skill>
                   </skills>
               </employee>
           </team>
       </department>
   </company>
   '''

   doc = pygixml.parse_string(complex_xml)
   company = doc.first_child()

   # Find all senior employees
   senior_employees = company.select_nodes("//employee[@level='senior']")
   print(f"Senior employees: {len(senior_employees)}")

   # Find employees with specific skills
   python_devs = company.select_nodes("//employee[skills/skill='Python']")
   print(f"Python developers: {len(python_devs)}")

   # Calculate average salary by department
   departments = company.select_nodes("department")
   for dept in departments:
       dept_name = dept.node().attribute("name").value()
       employees = dept.node().select_nodes(".//employee")
       
       if employees:
           total_salary = 0
           for emp in employees:
               salary = float(emp.node().child("salary").child_value())
               total_salary += salary
           
           avg_salary = total_salary / len(employees)
           print(f"{dept_name} average salary: ${avg_salary:.2f}")

   # Find employees earning more than 100k
   high_earners = company.select_nodes("//employee[salary > 100000]")
   for emp in high_earners:
       name = emp.node().child("name").child_value()
       salary = emp.node().child("salary").child_value()
       print(f"High earner: {name} (${salary})")

Real-World Use Cases
--------------------

Web Scraping Data Extraction
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pygixml

   # Example: Extract product information from HTML/XML
   html_content = '''
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

   doc = pygixml.parse_string(html_content)
   products = doc.first_child()

   # Extract product data
   product_list = []
   for product in products.select_nodes("product"):
       name = product.node().child("name").child_value()
       price = float(product.node().child("price").child_value())
       currency = product.node().child("price").attribute("currency").value()
       rating = float(product.node().child("rating").child_value())
       reviews = int(product.node().child("reviews").child_value())
       
       product_list.append({
           'name': name,
           'price': price,
           'currency': currency,
           'rating': rating,
           'reviews': reviews
       })

   # Sort by rating
   product_list.sort(key=lambda x: x['rating'], reverse=True)
   
   for product in product_list:
       print(f"{product['name']}: ${product['price']} ({product['rating']} stars)")

API Response Processing
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pygixml

   # Example: Process XML API response
   api_response = '''
   <weather>
       <location>
           <city>New York</city>
           <country>US</country>
           <timezone>America/New_York</timezone>
       </location>
       <current>
           <temperature unit="celsius">22</temperature>
           <humidity unit="percent">65</humidity>
           <wind>
               <speed unit="kmh">15</speed>
               <direction>NE</direction>
           </wind>
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

   doc = pygixml.parse_string(api_response)
   weather = doc.first_child()

   # Extract current weather
   location = weather.child("location")
   current = weather.child("current")
   
   city = location.child("city").child_value()
   temp = current.child("temperature").child_value()
   condition = current.child("condition").child_value()
   
   print(f"Current weather in {city}: {temp}°C, {condition}")

   # Extract forecast
   forecast_days = weather.select_nodes("forecast/day")
   print("Forecast:")
   for day in forecast_days:
       date = day.node().attribute("date").value()
       high = day.node().child("high").child_value()
       low = day.node().child("low").child_value()
       condition = day.node().child("condition").child_value()
       print(f"  {date}: {high}°C / {low}°C, {condition}")

Running Examples
----------------

All examples in this documentation can be run directly. Make sure you have pygixml installed:

.. code-block:: bash

   pip install pygixml

Then copy any example into a Python file and run it:

.. code-block:: bash

   python example.py

For more interactive examples, check the ``examples/`` directory in the pygixml repository.
