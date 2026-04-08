#!/usr/bin/env python3
"""
Tests for ParseFlags enum in pygixml
"""

import pytest
import tempfile
import os
import pygixml


class TestParseFlagsEnum:
    """Test ParseFlags enum"""

    def test_parse_flags_is_intflag(self):
        """ParseFlags should be an IntFlag subclass"""
        from enum import IntFlag
        assert issubclass(pygixml.ParseFlags, IntFlag)

    @pytest.mark.parametrize("flag", [
        pygixml.ParseFlags.MINIMAL,
        pygixml.ParseFlags.FULL,
        pygixml.ParseFlags.DEFAULT,
        pygixml.ParseFlags.COMMENTS,
        pygixml.ParseFlags.CDATA,
        pygixml.ParseFlags.PI,
        pygixml.ParseFlags.ESCAPES,
        pygixml.ParseFlags.WS_PCDATA,
        pygixml.ParseFlags.EOL,
        pygixml.ParseFlags.WCONV_ATTRIBUTE,
        pygixml.ParseFlags.WNORM_ATTRIBUTE,
        pygixml.ParseFlags.DECLARATION,
        pygixml.ParseFlags.DOCTYPE,
    ])
    def test_all_flags_are_integers(self, flag):
        """Every ParseFlags member should be accessible as an int"""
        assert isinstance(int(flag), int)

    def test_bitwise_or_two(self):
        """Two flags should combine with bitwise OR"""
        flags = pygixml.ParseFlags.COMMENTS | pygixml.ParseFlags.CDATA
        expected = int(pygixml.ParseFlags.COMMENTS) | int(pygixml.ParseFlags.CDATA)
        assert int(flags) == expected

    def test_bitwise_or_three(self):
        """Three flags should combine with bitwise OR"""
        flags = (pygixml.ParseFlags.COMMENTS |
                 pygixml.ParseFlags.CDATA |
                 pygixml.ParseFlags.PI)
        expected = (int(pygixml.ParseFlags.COMMENTS) |
                    int(pygixml.ParseFlags.CDATA) |
                    int(pygixml.ParseFlags.PI))
        assert int(flags) == expected

    def test_parse_flags_exported(self):
        """ParseFlags should be in __all__"""
        assert "ParseFlags" in pygixml.__all__


class TestParseFlagsUsage:
    """Test ParseFlags with actual parsing"""

    @pytest.mark.parametrize("flag", [
        pygixml.ParseFlags.MINIMAL,
        pygixml.ParseFlags.DEFAULT,
        pygixml.ParseFlags.FULL,
    ])
    def test_parse_string_flags(self, flag):
        """parse_string should accept ParseFlags"""
        xml = "<root><item>text</item></root>"
        doc = pygixml.parse_string(xml, flag)
        assert doc.root.child("item").text() == "text"

    def test_parse_string_combined_flags(self):
        """parse_string should accept combined flags"""
        flags = pygixml.ParseFlags.COMMENTS | pygixml.ParseFlags.CDATA
        xml = "<root><item>text</item><!--comment--></root>"
        doc = pygixml.parse_string(xml, flags)
        assert doc.root.child("item").text() == "text"

    def test_parse_file(self):
        """parse_file should accept ParseFlags"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write("<root><item>text</item></root>")
            path = f.name
        try:
            doc = pygixml.parse_file(path, pygixml.ParseFlags.MINIMAL)
            assert doc.root.child("item").text() == "text"
        finally:
            os.unlink(path)

    @pytest.mark.parametrize("flag", [
        pygixml.ParseFlags.MINIMAL,
        pygixml.ParseFlags.COMMENTS | pygixml.ParseFlags.CDATA,
        None,  # default (no flags)
    ])
    def test_load_string(self, flag):
        """load_string should accept ParseFlags and combined flags"""
        doc = pygixml.XMLDocument()
        if flag is None:
            result = doc.load_string("<root><item>ok</item></root>")
        else:
            result = doc.load_string("<root><item>ok</item></root>", flag)
        assert result is True
        assert doc.root.child("item").text() == "ok"

    def test_load_file(self):
        """load_file should accept ParseFlags"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write("<root><item>text</item></root>")
            path = f.name
        try:
            doc = pygixml.XMLDocument()
            result = doc.load_file(path, pygixml.ParseFlags.MINIMAL)
            assert result is True
            assert doc.root.child("item").text() == "text"
        finally:
            os.unlink(path)
