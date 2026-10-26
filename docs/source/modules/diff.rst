.. _diff:

Tree Diff and Embeddings
========================

``pygixml.diff`` compares two *ordered trees* (XML or HTML) and returns an
edit script. ``pygixml.signature`` / ``pygixml.similarity`` embed the
*structure* of a tree as a sparse vector. Everything runs in C++ (verbatim blocks inside
``src/embedding.pxi`` and ``src/diff.pxi``, no extra dependency), one call per
function, and the diff uses the embedding to decide which changed nodes belong
together.

HTML needs no special support: parse it with :func:`pygixml.parse_html` and
diff the documents. What counts as "the same" is a normalisation step (the
idea behind `html-differ <https://github.com/bem/html-differ>`_), not a
different algorithm.

.. code-block:: python

   import pygixml

   a = pygixml.parse_html("<ul class='m'><li>Home<li>About us<li>Blog</ul>")
   b = pygixml.parse_html("<ul class='m'><li>Home<li>About<li>Blog<li>Contact</ul>")

   for action in pygixml.diff(a, b, text_diff=True):
       print(action)
   # Insert(parent='/ul[1]', position=3, xml='<li>Contact</li>')
   # UpdateText(path='/ul[1]/li[2]/text()[1]', text='About', old='About us',
   #            diff=[(0, 'About'), (-1, ' us')])

   pygixml.is_equal(a, b)                       # False
   pygixml.similarity(a, b)                     # 0.889: structural similarity, 0..1

Edit script
-----------

``diff(a, b)`` returns a list (empty when the trees are equivalent) of:

.. list-table::
   :header-rows: 1

   * - Action
     - Meaning
   * - ``Insert(parent, position, xml)``
     - add the node(s) in ``xml`` as child number ``position`` of ``parent``.
       A wholly new subtree is **one** action
   * - ``InsertText(parent, position, text)``
     - add a text node
   * - ``Delete(path)``
     - remove a node with everything under it
   * - ``Move(path, parent, position)``
     - detach the node, then insert it into ``parent`` (evaluated after the
       detach) at ``position``
   * - ``UpdateText(path, text, old, diff)``
     - replace the text of a text/comment node. ``diff`` holds
       ``(-1 | 0 | 1, piece)`` tuples when ``text_diff=True``
   * - ``SetAttrib(path, name, value, old)``
     - set an attribute (``old`` is ``None`` when it is new)
   * - ``DeleteAttrib(path, name, old)``
     - remove an attribute

Actions come in the order they must be applied (the new tree is walked
breadth-first, so inserts near the top come before edits deeper down).
Paths look like ``/ul[1]/li[2]/text()[1]``: the index counts siblings of the
same tag (or ``text()`` / ``comment()``), and a path refers to the tree **as it
is when that action runs**, after the earlier ones. They address the
*normalised* view (blank text and comments are not there by default).

The script is checked before it is returned: applying it to the first tree
must give the second, otherwise :class:`pygixml.PygiXMLDiffError` is raised
(that would be a bug). The tests also apply scripts with an independent
reference patcher on 15,000 random tree pairs.

Normalisation
-------------

========================= ========= ==========================================
option                    default   effect
========================= ========= ==========================================
``ignore_whitespace``     ``True``  drop blank text, trim and collapse runs
``ignore_comments``       ``True``  comments are not compared
``ignore_attrs``          ``()``    attribute names to ignore; ``"data-*"`` is
                                    a prefix; a single string is fine
``class_as_set``          ``True``  ``class="b a a"`` equals ``class="a b"``
attribute order           always    never matters
========================= ========= ==========================================

``is_equal(a, b, **options)`` answers "did anything change?" in one pass by
comparing subtree hashes, so it is the cheap check before a diff.

How the diff works
------------------

Two phases, as in Chawathe et al., *Change Detection in Hierarchically
Structured Information* (1996):

1. **Matching**, top-down, for every matched pair of parents. Children are
   paired by (a) ``keys`` (an ``id`` attribute: the same key means the same
   element wherever it sits); (b) identical subtree hash, with an LCS over the
   hash sequences; (c) what is left between those anchors, by similarity:
   pq-gram profiles for elements, character bigrams for text. A node that is
   the only one of its tag in its gap is treated as an update. With
   ``moves=True`` unmatched subtrees are also paired *across* parents,
   identical ones first, then ones at least ``move_threshold`` similar.
2. **Edit script**: breadth-first over the new tree, mutating a working copy of
   the old one (insert, update, move), aligning each node's children with a
   longest-increasing-subsequence, then deleting what is left.

The choice of per-level LCS over a global optimal matching follows Cobena,
Abdessalem and Hinnach's comparative study of XML change-detection tools: the
LCS approach ran in linear time and stayed close to the minimal edit cost,
while optimal algorithms (Zhang-Shasha, APTED/RTED) are quadratic or worse.

Limits (also marked ``ponytail:`` in ``src/diff.pxi``):

* the LCS is an exact table below a size cap and a greedy monotone match above
  it. Upgrade path: Myers / Wu O(ND);
* elements are never renamed: a different tag is a delete plus an insert;
* a subtree that is both moved to another parent *and* edited is only found
  when it stays similar enough (``move_threshold``);
* the result is a good script, not a proven minimal one. Treat the exact
  output as unstable between versions.

Text diff
---------

``text_diff=True`` attaches a word-level diff to every ``UpdateText`` as a list
of ``(-1 | 0 | 1, piece)`` tuples (delete / keep / insert). Texts are split into
words, runs of whitespace, single punctuation marks and single CJK characters,
then compared with the same LCS the tree matching uses, so ``brave`` -> ``new``
is one replacement. It also works for scripts such as Persian. ``ponytail:``
a character-level Myers diff with semantic clean-up is the upgrade path.

Embeddings
----------

``signature(node, method="pqgram", p=2, q=3, content=False)`` returns a sparse
vector ``{hash: count}``; ``similarity(a, b, ...)`` is the Dice coefficient of
two such bags, ``2|A n B| / (|A| + |B|)``, computed in one C++ call.

* ``"pqgram"`` (Augsten, Bohlen, Gamper, *The pq-Gram Distance between Ordered
  Labeled Trees*, TODS 2010): every node anchors windows made of ``p``
  ancestors and ``q`` consecutive children. The distance approximates the tree
  edit distance and lower-bounds the fanout-weighted one.
* ``"paths"``: the bag of root-to-node tag paths. Cruder, cheaper, good for
  telling page templates apart.

Labels are tag names and text is one constant label, so the default compares
**structure only**: two pages built from the same template are 1.0 similar
whatever they say. ``content=True`` includes text. Both are linear in the size
of the tree, so ``similarity`` makes a cheap pre-filter in front of ``diff``.

Speed
-----

Measured on one Linux machine, single thread; treat the numbers as indicative.

* Catalog of 1,600 items (263 KB, 6,400 elements), 2 % of items edited:
  pygixml 15 ms and 32 actions for 32 edits; xmldiff 3.0 took 5.8 s (2.2 s with
  ``uniqueattrs=["id"]``) and emitted 916 (498) operations.
* A 487 KB real HTML page with 2 subtrees removed and 3 attributes added:
  pygixml 67 ms, 5 actions; xmldiff 3.0 with default settings 13.6 s, 816
  operations. xmldiff was not tuned for this input.
* 100,000 flat items (16 MB), 2 % edited: about 2.2 s.

Errors
------

Everything raises :class:`pygixml.PygiXMLDiffError`, a subclass of
:class:`pygixml.PygiXMLError`: something that is not a node or document, a null
node, an invalid option, or an internal consistency failure.

API
---

.. autofunction:: pygixml.diff

.. autofunction:: pygixml.is_equal

.. autofunction:: pygixml.signature

.. autofunction:: pygixml.similarity

.. autoexception:: pygixml.PygiXMLDiffError
