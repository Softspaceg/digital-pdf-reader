"""Field-value cleaning -- Arabic-character and markdown-markup stripping
for a single extracted field/table-cell value.

This is an opt-in policy, not a default behavior: nothing in DocumentReader
or TextCleaner calls this. Stripping Arabic entirely from a value is correct
only for a consumer whose structured output must be English-only -- a
bilingual EN/AR document (e.g. a UAE property/legal contract) may need
Arabic preserved in its full text, so this must never run by default over
whatever DocumentReader produces. Use it explicitly, only where your own
schema calls for English-only values.
"""

from __future__ import annotations

import re

from digital_pdf_reader.text_cleaner import TextCleaner

_MARKDOWN_MARKUP = re.compile(r"\*\*|<br\s*/?>|</?sup>|</?sub>|</?u>")


class FieldValueCleaner:
    def __init__(self, cleaner: TextCleaner | None = None) -> None:
        self._cleaner = cleaner or TextCleaner()

    def clean_fragment(self, value: object) -> str:
        """Strip cid garbage, Arabic characters, and markdown markup from a
        single field value or table cell, then collapse whitespace."""
        text = self._cleaner.strip_cid_and_control("" if value is None else str(value))
        text = _MARKDOWN_MARKUP.sub(" ", text)
        text = "".join(ch for ch in text if not self._cleaner.is_arabic_char(ch))
        return " ".join(text.split())

    def clean_table(self, table: list[list[str]]) -> list[list[str]]:
        return [[self.clean_fragment(cell) for cell in row] for row in table]

    def is_arabic_char(self, ch: str) -> bool:
        return self._cleaner.is_arabic_char(ch)
