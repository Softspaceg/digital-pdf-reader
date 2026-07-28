"""Unit tests for TextRatioDigitalDetector (dependency-free fallback)."""

from __future__ import annotations

from digital_pdf_reader.digital_detector import TextRatioDigitalDetector
from digital_pdf_reader.document_reader import DocumentReader


def test_empty_text_is_not_digital():
    assert TextRatioDigitalDetector().is_digital("") is False


def test_short_text_is_not_digital():
    assert TextRatioDigitalDetector().is_digital("a b c") is False


def test_low_letter_ratio_text_is_not_digital():
    assert TextRatioDigitalDetector().is_digital("1234567890 " * 10) is False


def test_normal_english_paragraph_is_digital():
    text = "This is a real paragraph of readable English text extracted from a digital document."
    assert TextRatioDigitalDetector().is_digital(text) is True


def test_sample_contract_text_is_detected_as_digital(
    sample_pdf_bytes, pdfplumber_provider, cleaner, reader_config
):
    content = DocumentReader(pdfplumber_provider, cleaner, reader_config).read(sample_pdf_bytes)

    assert TextRatioDigitalDetector().is_digital(content.full_text) is True
