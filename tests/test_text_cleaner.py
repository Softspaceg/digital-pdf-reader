"""Unit tests for TextCleaner -- doubled-char fix, Arabic-reversal fix,
cid/control stripping, and table-cell cleaning."""

from __future__ import annotations

from digital_pdf_reader.text_cleaner import TextCleaner


class TestFixDoubledText:
    def setup_method(self):
        self.cleaner = TextCleaner()

    def test_empty_string_returns_empty(self):
        assert self.cleaner._fix_doubled_text("") == ""

    def test_normal_word_unchanged(self):
        assert self.cleaner._fix_doubled_text("hello") == "hello"

    def test_word_with_natural_double_letters_unchanged(self):
        # "ll" in "hello" is only 1 out of 4 adjacent pairs -- below threshold
        assert self.cleaner._fix_doubled_text("hello") == "hello"
        assert self.cleaner._fix_doubled_text("coffee") == "coffee"

    def test_perfect_doubling_deduplicates(self):
        assert self.cleaner._fix_doubled_text("CCoonnttrraacctt") == "Contract"

    def test_two_char_doubled_deduplicates(self):
        assert self.cleaner._fix_doubled_text("aa") == "a"

    def test_single_char_token_unchanged(self):
        assert self.cleaner._fix_doubled_text("a") == "a"

    def test_two_char_no_duplication_unchanged(self):
        assert self.cleaner._fix_doubled_text("ab") == "ab"

    def test_below_threshold_unchanged(self):
        assert self.cleaner._fix_doubled_text("abcd") == "abcd"

    def test_multiline_each_line_handled_independently(self):
        result = self.cleaner._fix_doubled_text("CCoonnttrraacctt\nhello")
        lines = result.splitlines()
        assert lines[0] == "Contract"
        assert lines[1] == "hello"

    def test_empty_lines_preserved(self):
        result = self.cleaner._fix_doubled_text("word\n\nword")
        lines = result.splitlines()
        assert lines[0] == "word"
        assert lines[1] == ""
        assert lines[2] == "word"

    def test_arabic_word_not_corrupted(self):
        text = "مرحبا"
        result = self.cleaner._fix_doubled_text(text)
        assert isinstance(result, str)
        assert len(result) > 0


class TestIsArabicChar:
    def setup_method(self):
        self.cleaner = TextCleaner()

    def test_arabic_letter_meem(self):
        assert self.cleaner.is_arabic_char("م") is True

    def test_arabic_presentation_form(self):
        assert self.cleaner.is_arabic_char("ﺎ") is True

    def test_arabic_comma(self):
        assert self.cleaner.is_arabic_char("،") is True

    def test_latin_letter(self):
        assert self.cleaner.is_arabic_char("A") is False

    def test_digit(self):
        assert self.cleaner.is_arabic_char("5") is False

    def test_space(self):
        assert self.cleaner.is_arabic_char(" ") is False


class TestHasArabic:
    def setup_method(self):
        self.cleaner = TextCleaner()

    def test_standard_arabic_detected(self):
        assert self.cleaner.has_arabic("مرحبا") is True

    def test_presentation_form_detected(self):
        assert self.cleaner.has_arabic("ﺎ") is True

    def test_latin_text_not_detected(self):
        assert self.cleaner.has_arabic("hello world") is False

    def test_empty_string_not_detected(self):
        assert self.cleaner.has_arabic("") is False

    def test_mixed_latin_and_arabic_detected(self):
        assert self.cleaner.has_arabic("Invoice مبلغ 100") is True


class TestFixArabicReversed:
    def setup_method(self):
        self.cleaner = TextCleaner()

    def test_empty_string_returns_empty(self):
        assert self.cleaner._fix_arabic_reversed("") == ""

    def test_latin_only_unchanged(self):
        assert self.cleaner._fix_arabic_reversed("Invoice Total: 500") == "Invoice Total: 500"

    def test_pure_arabic_gets_reversed(self):
        original = "مرحبا"
        result = self.cleaner._fix_arabic_reversed(original)
        assert result == original[::-1]

    def test_pure_arabic_idempotent_via_double_apply(self):
        original = "مرحبا"
        once = self.cleaner._fix_arabic_reversed(original)
        twice = self.cleaner._fix_arabic_reversed(once)
        assert twice == original

    def test_mixed_arabic_latin_segments_are_interleaved(self):
        result = self.cleaner._fix_arabic_reversed("Invoice مبلغ 100")
        assert "غلبم" in result  # "مبلغ" reversed

    def test_multiline_each_line_handled_independently(self):
        result = self.cleaner._fix_arabic_reversed("hello\nمرحبا")
        lines = result.splitlines()
        assert lines[0] == "hello"
        assert lines[1] == "مرحبا"[::-1]


class TestCleanFullText:
    def setup_method(self):
        self.cleaner = TextCleaner()

    def test_empty_returns_empty(self):
        assert self.cleaner.clean_full_text("") == ""

    def test_applies_doubled_fix(self):
        assert self.cleaner.clean_full_text("CCoonnttrraacctt") == "Contract"

    def test_applies_arabic_reversal_only_when_present(self):
        result = self.cleaner.clean_full_text("hello world")
        assert result == "hello world"

    def test_strips_cid_tokens(self):
        assert self.cleaner.clean_full_text("Amount(cid:12)500") == "Amount500"

    def test_strips_control_chars_keeps_whitespace(self):
        result = self.cleaner.clean_full_text("line1\nline2\ttabbed \x00garbage")
        assert "\x00" not in result
        assert "line1" in result and "line2" in result


class TestCleanTable:
    def setup_method(self):
        self.cleaner = TextCleaner()

    def test_whitespace_normalized(self):
        result = self.cleaner.clean_table([["  hello   world  "]])
        assert result == [["hello world"]]

    def test_none_cell_becomes_empty(self):
        result = self.cleaner.clean_table([[None, "value"]])
        assert result == [["", "value"]]

    def test_arabic_preserved(self):
        # Table-cell cleaning here is layout-agnostic and preserves Arabic --
        # stripping Arabic from a specific field's value is an app-level
        # business rule, not a "reading a digital PDF" concern.
        result = self.cleaner.clean_table([["مرحبا"]])
        assert result == [["مرحبا"]]

    def test_cid_tokens_stripped(self):
        result = self.cleaner.clean_table([["Amount(cid:12)500"]])
        assert result == [["Amount500"]]
