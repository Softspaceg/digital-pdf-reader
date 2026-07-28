"""Unit tests for the unified DigitalDetector (pdfplumber page.chars +
printable/letter-ratio check, first-page-only by default)."""

from __future__ import annotations

from unittest.mock import MagicMock

from digital_pdf_reader.digital_detector import DigitalDetector, DigitalDetectorConfig
from digital_pdf_reader.pdfplumber_provider import PdfPlumberProvider
from digital_pdf_reader.text_cleaner import TextCleaner


def _detector(config: DigitalDetectorConfig | None = None) -> DigitalDetector:
    return DigitalDetector(PdfPlumberProvider(), TextCleaner(), config)


def test_sample_contract_is_detected_as_digital(sample_pdf_bytes):
    assert _detector().is_digital(sample_pdf_bytes) is True


def test_garbage_bytes_are_not_digital():
    assert _detector().is_digital(b"not a pdf at all %%%%") is False


def test_empty_bytes_are_not_digital():
    assert _detector().is_digital(b"") is False


def test_page_with_no_chars_is_not_digital():
    page = MagicMock()
    page.chars = []
    pdf = MagicMock()
    pdf.pages = [page]
    pdf.__enter__ = MagicMock(return_value=pdf)
    pdf.__exit__ = MagicMock(return_value=False)
    provider = MagicMock()
    provider.open.return_value = pdf

    assert DigitalDetector(provider, TextCleaner()).is_digital(b"fake") is False


def test_page_with_few_chars_below_threshold_is_not_digital():
    page = MagicMock()
    page.chars = [{"text": "a"}] * 5  # 5 chars, below default min_chars=50
    page.extract_text.return_value = "a b c"
    pdf = MagicMock()
    pdf.pages = [page]
    pdf.__enter__ = MagicMock(return_value=pdf)
    pdf.__exit__ = MagicMock(return_value=False)
    provider = MagicMock()
    provider.open.return_value = pdf

    assert DigitalDetector(provider, TextCleaner()).is_digital(b"fake") is False


def test_low_letter_ratio_page_is_not_digital():
    page = MagicMock()
    page.chars = [{"text": "1"}] * 60
    page.extract_text.return_value = "1234567890 " * 10
    pdf = MagicMock()
    pdf.pages = [page]
    pdf.__enter__ = MagicMock(return_value=pdf)
    pdf.__exit__ = MagicMock(return_value=False)
    provider = MagicMock()
    provider.open.return_value = pdf

    assert DigitalDetector(provider, TextCleaner()).is_digital(b"fake") is False


def test_only_first_page_checked_by_default():
    blank_page = MagicMock()
    blank_page.chars = []
    digital_page = MagicMock()
    digital_page.chars = [{"text": "a"}] * 100
    digital_page.extract_text.return_value = (
        "This is a real readable paragraph of English text extracted from a document."
    )
    pdf = MagicMock()
    pdf.pages = [blank_page, digital_page]
    pdf.__enter__ = MagicMock(return_value=pdf)
    pdf.__exit__ = MagicMock(return_value=False)
    provider = MagicMock()
    provider.open.return_value = pdf

    # Page 2 is digital but pages_to_check defaults to 1, so it's never seen.
    assert DigitalDetector(provider, TextCleaner()).is_digital(b"fake") is False
    digital_page.extract_text.assert_not_called()


def test_pages_to_check_can_sample_more_than_one_page():
    blank_page = MagicMock()
    blank_page.chars = []
    digital_page = MagicMock()
    digital_page.chars = [{"text": "a"}] * 100
    digital_page.extract_text.return_value = (
        "This is a real readable paragraph of English text extracted from a document."
    )
    pdf = MagicMock()
    pdf.pages = [blank_page, digital_page]
    pdf.__enter__ = MagicMock(return_value=pdf)
    pdf.__exit__ = MagicMock(return_value=False)
    provider = MagicMock()
    provider.open.return_value = pdf

    config = DigitalDetectorConfig(pages_to_check=2)
    assert DigitalDetector(provider, TextCleaner(), config).is_digital(b"fake") is True
