#!/usr/bin/env python3
"""
Tests for ParseFlags enum in pygixml
"""

import pytest
import pygixml


class TestParseFlagsEnum:
    """Test ParseFlags enum"""

    def test_parse_flags_is_intflag(self):
        """ParseFlags should be an IntFlag subclass"""
        from enum import IntFlag
        assert issubclass(pygixml.ParseFlags, IntFlag)

    def test_minimal_flag_value(self):
        """MINIMAL should have a valid integer value"""
        assert int(pygixml.ParseFlags.MINIMAL) > 0 or int(pygixml.ParseFlags.MINIMAL) == 0

    def test_full_flag_value(self):
        """FULL should have a valid integer value"""
        assert int(pygixml.ParseFlags.FULL) > 0

    def test_default_flag_value(self):
        """DEFAULT should have a valid integer value"""
        assert int(pygixml.ParseFlags.DEFAULT) > 0 or int(pygixml.ParseFlags.DEFAULT) == 0

    def test_bitwise_or(self):
        """Flags should combine with bitwise OR"""
        flags = pygixml.ParseFlags.COMMENTS | pygixml.ParseFlags.CDATA
        expected = int(pygixml.ParseFlags.COMMENTS) | int(pygixml.ParseFlags.CDATA)
        assert int(flags) == expected

    def test_bitwise_or_multiple(self):
        """Multiple flags should combine correctly"""
        flags = (pygixml.ParseFlags.COMMENTS |
                 pygixml.ParseFlags.CDATA |
                 pygixml.ParseFlags.PI)
        expected = (int(pygixml.ParseFlags.COMMENTS) |
                    int(pygixml.ParseFlags.CDATA) |
                    int(pygixml.ParseFlags.PI))
        assert int(flags) == expected

    def test_all_flags_have_values(self):
        """All ParseFlags members should have non-zero values"""
        for flag in pygixml.ParseFlags:
            assert int(flag) > 0, f"{flag.name} has zero value"

    def test_parse_flags_exported(self):
        """ParseFlags should be in __all__"""
        assert "ParseFlags" in pygixml.__all__


class TestParseFlagsUsage:
    """Test ParseFlags with actual parsing"""

    def test_parse_with_minimal_flag(self):
        """Parsing with MINIMAL flag should work"""
        xml = "<root><item>text</item></root>"
        doc = pygixml.parse_string(xml, pygixml.ParseFlags.MINIMAL)
        assert doc.root.child("item").text() == "text"

    def test_parse_with_default_flag(self):
        """Parsing with DEFAULT flag should work"""
        xml = "<root><item>text</item></root>"
        doc = pygixml.parse_string(xml, pygixml.ParseFlags.DEFAULT)
        assert doc.root.child("item").text() == "text"

    def test_parse_with_full_flag(self):
        """Parsing with FULL flag should work"""
        xml = "<root><item>text</item></root>"
        doc = pygixml.parse_string(xml, pygixml.ParseFlags.FULL)
        assert doc.root.child("item").text() == "text"

    def test_parse_with_combined_flags(self):
        """Parsing with combined flags should work"""
        flags = pygixml.ParseFlags.COMMENTS | pygixml.ParseFlags.CDATA
        xml = "<root><item>text</item><!--comment--></root>"
        doc = pygixml.parse_string(xml, flags)
        assert doc.root.child("item").text() == "text"

    def test_parse_file_with_enum(self):
        """parse_file should accept ParseFlags"""
        import tempfile
        import os

        xml = "<root><item>text</item></root>"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml)
            path = f.name

        try:
            doc = pygixml.parse_file(path, pygixml.ParseFlags.MINIMAL)
            assert doc.root.child("item").text() == "text"
        finally:
            os.unlink(path)

    def test_load_string_with_enum(self):
        """XMLDocument.load_string should accept ParseFlags"""
        doc = pygixml.XMLDocument()
        xml = "<root><item>text</item></root>"
        result = doc.load_string(xml, pygixml.ParseFlags.MINIMAL)
        assert result is True
        assert doc.root.child("item").text() == "text"

    def test_load_file_with_enum(self):
        """XMLDocument.load_file should accept ParseFlags"""
        import tempfile
        import os

        xml = "<root><item>text</item></root>"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml)
            path = f.name

        try:
            doc = pygixml.XMLDocument()
            result = doc.load_file(path, pygixml.ParseFlags.MINIMAL)
            assert result is True
            assert doc.root.child("item").text() == "text"
        finally:
            os.unlink(path)
