"""
pygixml.dictify — XML to dict interface, compatible with xmltodict.

All logic lives in dictify.pxi, compiled into pygixml_cy.so.

Usage::

    from pygixml import dictify

    d = dictify.parse(xml_string)
    s = dictify.unparse(d, pretty=True)
    d = dictify.parse_file("data.xml")

    # streaming: yield one dict per element without loading the whole document
    for record in dictify.iterdict("big.xml", "record"):
        process(record)
"""

from .pygixml_cy import (
    dictify_parse      as parse,
    dictify_parse_file as parse_file,
    dictify_unparse    as unparse,
    dictify_iterdict as iterdict,
)

__all__ = ["parse", "parse_file", "unparse", "iterdict"]
