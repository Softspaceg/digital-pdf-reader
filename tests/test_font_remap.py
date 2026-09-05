"""
Unit tests for font_remap page coverage.

Recovery runs over the pages that were actually read. Correcting a fixed
prefix instead would hand the caller pages it never asked for. The selection
rule itself is covered in test_page_selection.py; these check that
font_corrected_document_text honors it against a real PDF.
"""

from __future__ import annotations

import fitz

from digital_pdf_reader.font_remap import font_corrected_document_text
from digital_pdf_reader.page_selection import PageSelection


def _pdf_with_text_per_page(page_count: int) -> bytes:
    doc = fitz.open()
    for page_number in range(1, page_count + 1):
        page = doc.new_page()
        page.insert_text((72, 72), f"PAGE{page_number}MARKER")
    data = doc.tobytes()
    doc.close()
    return data


def _markers_in(text: str, page_count: int) -> list[int]:
    return [n for n in range(1, page_count + 1) if f"PAGE{n}MARKER" in text]


class TestPageCoverage:
    def test_explicit_pages_are_the_only_ones_corrected(self):
        text, _ = font_corrected_document_text(_pdf_with_text_per_page(5), PageSelection.of([2, 4]))

        assert _markers_in(text, 5) == [2, 4]

    def test_a_prefix_selection_corrects_that_prefix(self):
        text, _ = font_corrected_document_text(
            _pdf_with_text_per_page(5), PageSelection(max_pages=3)
        )

        assert _markers_in(text, 5) == [1, 2, 3]

    def test_no_selection_corrects_the_whole_document(self):
        text, _ = font_corrected_document_text(_pdf_with_text_per_page(4))

        assert _markers_in(text, 4) == [1, 2, 3, 4]
