"""
Fitz (PyMuPDF) fallback text reader.

Used when pdfplumber's extraction (document_reader.DocumentReader) returns
empty on a page already known digital -- some pdfplumber failures on
malformed/unusual PDFs succeed under PyMuPDF instead. Returns a flat string,
not structured blocks: this is a last-resort path, not a primary reader, and
callers needing table structure should rely on DocumentReader succeeding
instead.

Costs a dependency: requires the `fitz` optional extra (PyMuPDF,
AGPL-3.0/Artifex Commercial dual-licensed) -- resolve that license before
shipping commercially.
"""

from __future__ import annotations

import fitz  # PyMuPDF

from digital_pdf_reader.page_selection import PageSelection
from digital_pdf_reader.text_cleaner import TextCleaner


def read_with_fitz(raw_bytes: bytes, selection: PageSelection | None = None) -> str:
    """Read plain text from a PDF via PyMuPDF. Returns "" on any failure --
    callers reach this only after the primary pdfplumber reader already
    failed or returned empty, so there's nothing further to fall back to."""
    selection = selection or PageSelection()
    cleaner = TextCleaner()
    try:
        doc = fitz.open(stream=raw_bytes, filetype="pdf")
        try:
            parts = [doc[index].get_text("text") for index in selection.indices(len(doc))]
        finally:
            doc.close()
    except Exception:
        return ""

    combined = "\n\n".join(part for part in parts if part.strip())
    return cleaner.clean_full_text(combined)
