API Reference
=============

This page documents every public class, method, property, and function in
pygixml.  For high-level usage guides see :doc:`quickstart`, :doc:`objectify`,
and :doc:`dictify`.

----

Core Module
-----------

.. automodule:: pygixml
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: groupwise
   :exclude-members: StreamElement, PullParser

----

objectify
---------

.. automodule:: pygixml.objectify
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: ObjectifiedElement, NodeSequence

.. autoclass:: pygixml.objectify.ObjectifiedElement
   :members:
   :undoc-members:
   :special-members: __call__, __str__, __iter__, __len__, __bool__, __eq__

.. autoclass:: pygixml.objectify.NodeSequence
   :members:
   :undoc-members:
   :special-members: __call__, __str__, __iter__, __len__, __bool__, __getitem__

----

dictify
-------

.. automodule:: pygixml.dictify
   :members:
   :undoc-members:
   :show-inheritance:

----

jsonify
-------

.. automodule:: pygixml.jsonify
   :members:
   :undoc-members:
   :show-inheritance:

----

Streaming
---------

.. autoclass:: pygixml.StreamElement
   :members:
   :undoc-members:
   :special-members: __repr__, __len__, __bool__, __iter__, __getitem__

.. autoclass:: pygixml.PullParser
   :members:
   :undoc-members:
