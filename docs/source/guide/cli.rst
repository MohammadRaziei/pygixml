.. _cli:

Command Line Tools
===================

pygixml installs one entry point, ``pygixml``, with five subcommands —
no Python code required for one-off queries, conversions, pretty-printing,
or filtering giant files from a shell pipeline. Every subcommand also
works spelled out as ``python -m pygixml <subcommand>``, which is handy
when ``pygixml`` isn't on your ``PATH`` (e.g. inside a virtualenv you
haven't activated).

.. code-block:: bash

   pygixml <subcommand> [OPTIONS] [ARGS]
   python -m pygixml <subcommand> [OPTIONS] [ARGS]

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Subcommand
     - Loads
     - Use it for
   * - ``pygixml cat``
     - full DOM
     - pretty-print (and colorize) an XML file for the terminal — the
       XML analog of ``bat``/``jq -C``
   * - ``pygixml query``
     - full DOM
     - ad-hoc XPath / dotted queries — a ``jq``/``xq``-style tool for
       XML you can fit in memory
   * - ``pygixml jsonify`` (``json`` alias)
     - DOM *or* streamed
     - converting a whole file to JSON, ``.json`` in / out
   * - ``pygixml convert``
     - full DOM
     - converting between XML, JSON, YAML, and TOON, any direction
   * - ``pygixml stream``
     - one record at a time
     - filtering matches out of a file **too big to load**, bounded
       memory

If you're not sure which one you need: ``cat``/``query``/``convert``
load the whole document, same as :func:`pygixml.parse_file` would —
fine for anything that comfortably fits in RAM. ``jsonify`` switches to
a constant-memory streamed conversion automatically once a file crosses
64MB (see :doc:`/guide/jsonify`). ``stream`` never loads more than one matched
element at a time, so it's the only one of the five safe for a file
that's genuinely too large to fit in memory — see :doc:`/guide/streaming` for
the underlying constant-memory parsing layer it's built on.

----

``pygixml cat``
----------------

Pretty-print an XML file, with syntax coloring on a real terminal if
`colorama <https://pypi.org/project/colorama/>`_ is installed. This is
the XML analog of tools like ``bat`` or ``jq -C`` — you're looking at a
file, not piping it into something else.

.. code-block:: bash

   pygixml cat data.xml                    # pretty + colorized (auto: only
                                            # on a real terminal, and only
                                            # if colorama is installed)
   cat data.xml | pygixml cat -            # from stdin
   pygixml cat data.xml --color always     # force color even when piped
   pygixml cat data.xml --color never      # force plain, no color
   pygixml cat data.xml --indent 4         # 4-space indent instead of 2
   pygixml cat data.xml -o pretty.xml      # write to a file instead of
                                           # stdout (never colorized by
                                           # 'auto' -- a file isn't a tty)

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Flag
     - Meaning
   * - ``FILE``
     - XML file to display. ``-`` reads from stdin.
   * - ``--indent N``
     - Spaces per indent level. Default ``2``; must be ``>= 0``.
   * - ``--color {auto,always,never}``
     - ``auto`` (default) colorizes only on a real terminal *and* only
       if colorama is installed. ``always``/``never`` force it on/off
       regardless.
   * - ``--output PATH``, ``-o PATH``
     - Write the result here instead of stdout.

If colorama isn't installed, ``cat`` still works exactly the same,
just without color — plain, pretty-printed XML, same as
``--color never``. Install it (along with YAML/TOON support for
``convert``) with ``pip install pygixml[all]``.

The XML declaration (``<?xml version="1.0"?>``) is preserved from the
source even though pugixml's own serializer doesn't round-trip it.

----

``pygixml query``
------------------

Query an XML file with either XPath or a ``lxml.objectify``-style
dotted path — a ``jq``/``xq`` for XML you can fit in memory. See
:doc:`/guide/xpath` and :doc:`/guide/objectify` for the underlying query languages.

.. code-block:: bash

   # XPath (starts with / or //)
   pygixml query data.xml "//user-profile[@id='101']/first_name"

   # dotted, objectify-style (starts with .) -- first segment names the root
   pygixml query data.xml ".database.user_profile.first_name"
   pygixml query data.xml ".database.user_profile.@id"      # attribute
   pygixml query data.xml ".database.entry[1]"              # index
   pygixml query data.xml ".database.entry[*]"              # all siblings
   pygixml query data.xml ".database.user_profile.text()"   # text content

   # output formats
   pygixml query data.xml ".database" --format xml
   pygixml query data.xml ".database" --format json --pretty

   # just the count, exit code like grep (0 = match, 1 = no match)
   pygixml query data.xml ".database.entry[*]" --count

   # multiple files, stdin, NUL-separated for xargs -0
   pygixml query *.xml ".config.host"
   cat data.xml | pygixml query - ".config.host"
   pygixml query data.xml ".database.entry[*]" --null | xargs -0 -n1 echo

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Flag
     - Meaning
   * - ``FILE...``
     - One or more XML files (or ``-`` for stdin). The query is always
       the *last* argument.
   * - ``--format {value,text,xml,json}``
     - How to render each match. Default ``value``.
   * - ``--pretty``
     - Pretty-print ``--format json``/``xml`` output.
   * - ``--separator SEP``
     - Separator between multiple results. Default newline.
   * - ``--null``
     - ``\0``-separate results instead, for piping into ``xargs -0``.
   * - ``--count``
     - Print only the number of matches.
   * - ``--quiet``
     - Suppress per-file error messages (still reflected in the exit code).

Exit code is ``0`` if at least one match was found (across all files),
``1`` otherwise — the same convention as ``grep``.

----

``pygixml jsonify``
--------------------

Convert a whole XML file to JSON. ``json`` is a short alias for the
same subcommand.

.. code-block:: bash

   pygixml jsonify data.xml                        # compact JSON to stdout
   pygixml jsonify data.xml -p                     # pretty (2-space indent)
   pygixml jsonify data.xml -o data.json           # write to a file
   pygixml jsonify data.xml --force-list item      # always make <item> a list
   cat data.xml | pygixml jsonify -                # read from stdin

   pygixml json data.xml                           # `json` is a short alias

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Flag
     - Meaning
   * - ``FILE``
     - XML file to convert. ``-`` reads from stdin.
   * - ``--output PATH``, ``-o PATH``
     - Write JSON here instead of stdout.
   * - ``--pretty``, ``-p``
     - Pretty-print with a 2-space indent.
   * - ``--indent N``
     - Pretty-print with an *N*-space indent (implies ``--pretty``);
       must be ``>= 0``.
   * - ``--force-list TAG``
     - Always serialize this child tag as a list, even with a single
       occurrence. Repeatable.
   * - ``--attr-prefix STR``, ``--cdata-key STR``
     - Same meaning as :func:`pygixml.jsonify.dumps_file`.
   * - ``--stream`` / ``--no-stream``
     - Force streaming mode / force in-memory DOM mode, overriding the
       automatic size-based choice below.

Automatically switches to :func:`~pygixml.jsonify.stream_dump`
(constant memory — see :doc:`/guide/jsonify` for its complexity
characteristics) for files over 64MB; ``--stream``/``--no-stream``
force one mode or the other regardless of size. Both modes produce
byte-identical output for the same input and options.

----

``pygixml stream``
-------------------

Read a (possibly giant) file once, tag by tag, via
:func:`pygixml.iterparse`, and emit matching elements as JSON — never
holding more than one matched element's subtree in memory at a time.
This is the tool for a file too large for ``pygixml query``/``jsonify``'s
DOM mode.

.. code-block:: bash

   # every <order>, one JSON object per line (JSONL)
   pygixml stream orders.xml --tag order

   # simple filters -- numeric or string, on a child path or an @attribute
   pygixml stream orders.xml --tag order --where "total>100"
   pygixml stream orders.xml --tag order --where "@status=shipped"

   # multiple --where are AND'ed together
   pygixml stream orders.xml --tag order \
       --where "@status=shipped" --where "customer=acme"

   # a real JSON array instead of JSONL -- still one pass, still bounded memory
   pygixml stream orders.xml --tag order --where "total>100" --format array -p

   # just count, or stop after N matches -- handy for sanity-checking a
   # filter against the first few records of a multi-GB file
   pygixml stream orders.xml --tag order --where "@status=shipped" --count
   pygixml stream huge.xml --tag order --where "total>100" --limit 10

   cat orders.xml | pygixml stream - --tag order

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Flag
     - Meaning
   * - ``FILE``
     - XML file to scan. ``-`` reads from stdin.
   * - ``--tag TAG``, ``-t TAG``
     - **Required.** Only elements with this tag are considered.
   * - ``--where EXPR``, ``-w EXPR``
     - Filter, e.g. ``"price>10"`` or ``"@status=shipped"``. Repeatable;
       all conditions must hold (AND). Supports ``=``, ``!=``, ``>``,
       ``<``, ``>=``, ``<=``. The left-hand side is either ``@attr`` or
       a child path (``customer``, ``items/item/sku`` — same syntax as
       :meth:`pygixml.StreamElement.findtext`).
   * - ``--format {jsonl,array}``, ``-f``
     - ``jsonl`` (default): one JSON object per line. ``array``: a
       single JSON array, still streamed one match at a time.
   * - ``--pretty``, ``-p``
     - Pretty-print each matched object.
   * - ``--force-list TAG``
     - Same meaning as ``pygixml jsonify``'s flag, applied per match.
   * - ``--limit N``, ``-n N``
     - Stop after *N* matches; must be ``>= 0``.
   * - ``--count``, ``-c``
     - Print only the number of matches.
   * - ``--output PATH``, ``-o PATH``
     - Write output here instead of stdout.

Exit code is ``0`` if at least one match was found, ``1`` otherwise
(``--limit 0`` matches nothing on purpose, so it exits ``1`` too).

----

``pygixml convert``
--------------------

Convert a file between XML, JSON, YAML, and TOON, in any direction.

.. code-block:: bash

   pygixml convert data.xml -o data.json         # format guessed from extensions
   pygixml convert data.xml -o data.yaml
   pygixml convert data.json -o data.xml -p      # pretty XML
   pygixml convert data.yaml --to toon           # stdout needs --to explicitly
   cat data.xml | pygixml convert - --from xml --to json   # stdin needs --from too

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Flag
     - Meaning
   * - ``INPUT``
     - File to convert. ``-`` reads from stdin (requires ``--from``,
       since there's no extension to guess from).
   * - ``--output PATH``, ``-o PATH``
     - Write the result here instead of stdout (which requires ``--to``,
       for the same reason).
   * - ``--from {json,xml,yaml,toon}``
     - Input format. Auto-detected from ``INPUT``'s extension if omitted.
   * - ``--to {json,xml,yaml,toon}``
     - Output format. Auto-detected from ``--output``'s extension if
       omitted.
   * - ``--pretty``, ``-p``
     - Pretty-print, where the target format supports it (json, xml).
   * - ``--indent N_OR_STR``
     - Indent for json (a number of spaces) or xml (a literal string,
       e.g. a tab).

Built on :class:`pygixml.formats.FormatDocument` -- a small class
wrapping a plain dict (the same ``@attr``/``#text``/list shape
:func:`pygixml.dictify.parse` produces), with ``to_json``/``to_xml``/
``to_yaml``/``to_toon`` methods and matching ``from_*`` classmethods,
importable directly for use in your own code:

.. code-block:: python

   from pygixml.formats import FormatDocument

   doc = FormatDocument.from_xml(open("data.xml").read())
   open("data.yaml", "w").write(doc.to_yaml())
   open("data.toon", "w").write(doc.to_toon())

JSON and XML always work (stdlib ``json`` + this package's own
``dictify``); YAML needs `PyYAML <https://pypi.org/project/PyYAML/>`_
and TOON needs `ctoon <https://pypi.org/project/ctoon/>`_ (also
written by the author of pygixml) -- both optional, and asking for a
format you don't have the package for gives a clear
``pip install ...`` error instead of a crash:

.. code-block:: bash

   pip install pygixml[all]   # colorama (for `cat`) + PyYAML + ctoon

Like ``cat``/``query``, this loads the whole document -- for XML too
big to fit in memory, convert with ``pygixml jsonify --stream`` or
``pygixml stream`` instead.

----

Exit codes
----------

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Code
     - Meaning
   * - ``0``
     - Success (for ``query``/``stream``: at least one match found)
   * - ``1``
     - No match (``query``/``stream``), or a per-file error occurred
       (``query``)
   * - ``2``
     - Argument error (bad flag, bad ``--where`` expression, negative
       ``--indent``/``--limit``, etc.) -- same convention ``argparse``
       itself uses
   * - ``3``
     - A required optional dependency is missing (``convert`` asked
       for YAML/TOON without PyYAML/ctoon installed)
