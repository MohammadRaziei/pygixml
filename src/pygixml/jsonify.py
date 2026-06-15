"""
pygixml.jsonify — direct XML → JSON serialization.

All heavy lifting is done in C++ (jsonify.pxi compiled into pygixml_cy.so).
No Python dict/list is allocated during traversal — only one str at the end.

Usage::

    from pygixml import jsonify

    # smart dispatcher — str or ObjectifiedElement or XMLNode
    jsonify.dumps("<root/>")
    jsonify.dumps(root.user_profile)          # ObjectifiedElement
    jsonify.dumps(doc.root)                   # XMLNode

    # typed entry points
    jsonify.dumps_str("<root/>")
    jsonify.dumps_file("data.xml")
    jsonify.dumps_obj(root.user_profile)
    jsonify.dumps_node(doc.root)

    # options
    jsonify.dumps(xml, pretty=True, indent="  ", encoding="utf-8")
    jsonify.dumps(xml, attr_prefix="", cdata_key="text")
    jsonify.dumps(xml, force_list={"item"})

    # streaming (gigantic files — constant memory):
    jsonify.xml_to_json_file("huge.xml", "out.json")
    jsonify.xml_to_json_file(
        "huge.xml", "out.json",
        record_tag="record",       # only these elements are emitted
        attr_prefix="@",
        cdata_key="#text",
        force_list={"tag"},        # always a JSON array
        pretty=True,
        indent="  ",
        chunk_size=65536,
    )
"""

import io
import json
import os

from .pygixml_cy import (
    iterparse as _iterparse,
    iterfind as _iterfind,
    jsonify_dumps      as dumps,
    jsonify_dumps_str  as dumps_str,
    jsonify_dumps_file as dumps_file,
    jsonify_dumps_obj  as dumps_obj,
    jsonify_dumps_node as dumps_node,
)

__all__ = [
    "dumps", "dumps_str", "dumps_file", "dumps_obj", "dumps_node",
    "xml_to_json_file",
]


# ---------------------------------------------------------------------------
# StreamElement → Python dict (mirrors the same convention as C++ serialiser)
# ---------------------------------------------------------------------------

def _elem_to_dict(elem, attr_prefix, cdata_key, force_list):
    """Recursively convert a :class:`StreamElement` to a nested dict.

    Convention (identical to the C++ serialiser in jsonify.pxi):

    * Attributes → ``{attr_prefix + name: value}``
    * Text content (when no child elements exist) → ``{cdata_key: text}``
    * Child elements → ``{tag: value}`` where *value* is a dict or a list
      of dicts when the tag appears more than once **or** is in *force_list*.
    * If the element has only text and no attributes/children, the value
      itself is returned as a plain string (scalar shortcut).
    """
    obj = {}

    # --- attributes --------------------------------------------------------
    for k, v in elem.items():
        obj[attr_prefix + k] = v

    # --- child elements ----------------------------------------------------
    # count tag occurrences so we know when to force a list
    tag_counts = {}
    for child in elem:
        tag_counts[child.tag] = tag_counts.get(child.tag, 0) + 1

    # track which tags we have already started writing so we can append
    seen = {}
    for child in elem:
        tag = child.tag
        val = _elem_to_dict(child, attr_prefix, cdata_key, force_list)
        if tag in seen:
            # already in obj as a list — append
            obj[tag].append(val)
        elif tag_counts[tag] > 1 or (force_list and tag in force_list):
            obj[tag] = [val]
            seen[tag] = True
        else:
            obj[tag] = val

    # --- text content ------------------------------------------------------
    text = (elem.text or "").strip()
    if text:
        if obj:
            obj[cdata_key] = text
        else:
            # scalar shortcut: <score>42</score> → "42" (or just the str)
            return text

    return obj


# ---------------------------------------------------------------------------
# Public streaming converter
# ---------------------------------------------------------------------------

def xml_to_json_file(
    xml_source,
    json_path,
    *,
    record_tag=None,
    attr_prefix="@",
    cdata_key="#text",
    force_list=None,
    pretty=False,
    indent="  ",
    chunk_size=65536,
    stack_size=4096,
    encoding="utf-8",
):
    """Convert a (potentially gigantic) XML file to JSON — in constant memory.

    Unlike :func:`dumps_file`, this function **never** loads the whole XML
    document into a pugixml DOM. It uses :func:`pygixml.iterparse` (the
    yxml-backed streaming parser) to process the file in chunks of
    *chunk_size* bytes and writes JSON incrementally to *json_path* via a
    buffered file handle. Peak memory usage is proportional to the size of
    the largest single element subtree, not the whole document.

    Schema
    ------
    * When *record_tag* is **None** (default), the root element becomes the
      top-level JSON object and its direct children each become an item in
      a ``"<root-tag>"`` array::

          <db>
            <record id="1"><name>Ali</name></record>
            <record id="2"><name>Sara</name></record>
          </db>

          → {"db": [{"@id": "1", "name": "Ali"},
                     {"@id": "2", "name": "Sara"}]}

    * When *record_tag* is given, only elements with that tag name produce
      entries. The output is a JSON array (``[…]``) directly::

          xml_to_json_file("big.xml", "out.json", record_tag="record")
          # → [{"@id": "1", "name": "Ali"}, …]

    Parameters
    ----------
    xml_source : str | os.PathLike | bytes | bytearray | file-like
        XML input — anything accepted by :func:`pygixml.iterparse`.
    json_path : str | os.PathLike
        Destination file path. **Overwritten if it exists.**
    record_tag : str | None
        Element tag whose ``end`` events produce JSON entries. When
        *None*, the direct children of the root element are used.
    attr_prefix : str
        Prefix for XML attributes in JSON keys. Default ``"@"``.
    cdata_key : str
        JSON key for element text content when mixed with child elements.
        Default ``"#text"``.
    force_list : set | None
        Tag names that are *always* serialised as JSON arrays (even when
        only one sibling exists). Pass ``None`` to auto-detect (a list is
        used whenever a tag appears more than once under the same parent).
    pretty : bool
        Indent the JSON output. Default ``False``.
    indent : str
        Indentation string when *pretty* is ``True``. Default ``"  "``.
    chunk_size : int
        Bytes read per :func:`iterparse` chunk. Default ``65 536`` (64 KB).
    stack_size : int
        yxml internal stack size — increase for extremely deep nesting or
        very long tag names. Default ``4096``.
    encoding : str
        Encoding for the output JSON file. Default ``"utf-8"``.

    Returns
    -------
    int
        Number of JSON records written.

    Raises
    ------
    PygiXMLError
        On malformed XML.
    OSError
        On I/O failure.

    Examples
    --------
    Basic conversion — 1 GB XML → JSON::

        from pygixml import jsonify
        n = jsonify.xml_to_json_file("dump.xml", "dump.json", pretty=True)
        print(f"Wrote {n} records")

    Only extract ``<order>`` elements::

        jsonify.xml_to_json_file(
            "orders.xml", "orders.json",
            record_tag="order",
            force_list={"item"},
        )
    """
    _indent = indent if pretty else None
    _fl = set(force_list) if force_list else None

    # -----------------------------------------------------------------------
    # Mode A: record_tag given — stream only matching elements into a top-
    # level JSON array.  Each record is serialised one line at a time.
    # -----------------------------------------------------------------------
    if record_tag is not None:
        count = 0
        with open(json_path, "w", encoding=encoding) as fout:
            fout.write("[\n" if pretty else "[")
            first = True
            for elem in _iterfind(
                xml_source, record_tag,
                stack_size=stack_size, chunk_size=chunk_size,
            ):
                d = _elem_to_dict(elem, attr_prefix, cdata_key, _fl)
                elem.clear()
                chunk = json.dumps(d, ensure_ascii=False, indent=_indent)
                if not first:
                    fout.write(",\n" if pretty else ",")
                fout.write(chunk)
                first = False
                count += 1
            fout.write("\n]" if pretty else "]")
        return count

    # -----------------------------------------------------------------------
    # Mode B: no record_tag — collect direct children of the root element,
    # and build { "root-tag": [child1, child2, ...] }.
    # The root's own attributes are preserved as top-level keys.
    # -----------------------------------------------------------------------
    count = 0
    root_tag = None
    root_attrs = {}
    first_child = True

    with open(json_path, "w", encoding=encoding) as fout:
        # We'll stream-write the outer wrapper manually so we never hold
        # more than one child dict in memory.

        # First pass: capture root element's start to get its tag/attrs,
        # then emit children one by one on "end".
        gen = _iterparse(
            xml_source, events=("start", "end"),
            stack_size=stack_size, chunk_size=chunk_size,
        )
        root_depth = 0   # depth counter to know which "end" is root's end

        for event, elem in gen:
            if event == "start":
                root_depth += 1
                if root_depth == 1:
                    # root element — capture tag and attributes
                    root_tag = elem.tag
                    for k, v in elem.items():
                        root_attrs[attr_prefix + k] = v

                    # open the output JSON
                    fout.write("{\n" if pretty else "{")
                    # write root attributes first (if any)
                    sep = ""
                    for jk, jv in root_attrs.items():
                        chunk = json.dumps(jk, ensure_ascii=False)
                        val_chunk = json.dumps(jv, ensure_ascii=False)
                        fout.write(sep)
                        if pretty:
                            fout.write(f'  {chunk}: {val_chunk}')
                        else:
                            fout.write(f'{chunk}:{val_chunk}')
                        sep = ",\n" if pretty else ","

                    # open the children array
                    root_key = json.dumps(root_tag, ensure_ascii=False)
                    fout.write(sep)
                    if pretty:
                        fout.write(f'  {root_key}: [\n')
                    else:
                        fout.write(f'{root_key}:[')

            elif event == "end":
                root_depth -= 1
                if root_depth == 0:
                    # root closed — close the children array and the object
                    fout.write("\n  ]" if pretty else "]")
                    fout.write("\n}" if pretty else "}")
                elif root_depth == 1:
                    # direct child of root — serialise and stream
                    d = _elem_to_dict(elem, attr_prefix, cdata_key, _fl)
                    elem.clear()
                    chunk = json.dumps(d, ensure_ascii=False, indent=_indent)
                    if _indent and pretty:
                        # re-indent so it nests nicely under the root key
                        chunk = "\n".join(
                            ("    " + line) if line.strip() else line
                            for line in chunk.splitlines()
                        )
                    if not first_child:
                        fout.write(",\n" if pretty else ",")
                    fout.write(chunk)
                    first_child = False
                    count += 1
                # deeper "end" events belong to children that clear() handles

        if root_tag is None:
            # empty / no-root document — write an empty object
            with open(json_path, "w", encoding=encoding) as fout2:
                fout2.write("{}")

    return count