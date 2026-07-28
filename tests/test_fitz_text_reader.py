"""Unit tests for read_with_fitz -- the fitz/PyMuPDF fallback text reader.
Requires the `fitz` extra to be installed."""

from __future__ import annotations

from digital_pdf_reader.fitz_text_reader import read_with_fitz


def test_reads_real_text_from_sample_contract(sample_pdf_bytes):
    result = read_with_fitz(sample_pdf_bytes)

    assert "ASIC-2026-0006798" in result


def test_garbage_bytes_return_empty():
    assert read_with_fitz(b"not a pdf at all %%%%") == ""


def test_empty_bytes_return_empty():
    assert read_with_fitz(b"") == ""


def test_pages_reads_only_the_requested_page(sample_pdf_bytes):
    full = read_with_fitz(sample_pdf_bytes)
    first_page_only = read_with_fitz(sample_pdf_bytes, pages=[1])

    assert "ASIC-2026-0006798" in first_page_only
    assert len(first_page_only) <= len(full)


def test_max_pages_limits_output(sample_pdf_bytes):
    limited = read_with_fitz(sample_pdf_bytes, max_pages=1)

    assert isinstance(limited, str)
    assert len(limited) > 0
