"""Unit tests for FieldValueCleaner -- Arabic/markdown/cid stripping for a
single field/cell value. This is opt-in policy, not a default text fix (see
module docstring in field_value_cleaner.py) -- these tests only cover its
own behavior, not any interaction with DocumentReader/TextCleaner defaults."""

from __future__ import annotations

from digital_pdf_reader.field_value_cleaner import FieldValueCleaner


class TestCleanFragment:
    def setup_method(self):
        self.cleaner = FieldValueCleaner()

    def test_strips_cid_garbage(self):
        assert self.cleaner.clean_fragment("784-1975(cid:941)-2426946-7") == "784-1975-2426946-7"

    def test_strips_arabic_characters(self):
        assert self.cleaner.clean_fragment("ASIC-2026-0006798 دقعلا مقر") == "ASIC-2026-0006798"

    def test_strips_markdown_markup(self):
        assert self.cleaner.clean_fragment("**ASIC-2026-0006798**<br>") == "ASIC-2026-0006798"

    def test_none_becomes_empty_string(self):
        assert self.cleaner.clean_fragment(None) == ""

    def test_collapses_whitespace(self):
        assert self.cleaner.clean_fragment("  hello   world  ") == "hello world"

    def test_non_string_value_converted(self):
        assert self.cleaner.clean_fragment(42) == "42"


class TestCleanTable:
    def setup_method(self):
        self.cleaner = FieldValueCleaner()

    def test_cleans_every_cell(self):
        result = self.cleaner.clean_table([["**Name**", "دقعلا مقر 100"]])
        assert result == [["Name", "100"]]


class TestIsArabicChar:
    def setup_method(self):
        self.cleaner = FieldValueCleaner()

    def test_detects_arabic(self):
        assert self.cleaner.is_arabic_char("د") is True

    def test_rejects_latin(self):
        assert self.cleaner.is_arabic_char("C") is False
