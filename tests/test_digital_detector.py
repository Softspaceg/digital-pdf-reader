"""Unit tests for the unified DigitalDetector (pdfplumber page.chars +
printable/letter-ratio + text-area-ratio checks, first-page-only by
default)."""

from __future__ import annotations

from unittest.mock import MagicMock

from digital_pdf_reader.digital_detector import DigitalDetector, DigitalDetectorConfig
from digital_pdf_reader.pdfplumber_provider import PdfPlumberProvider
from digital_pdf_reader.text_cleaner import TextCleaner


def _detector(config: DigitalDetectorConfig | None = None) -> DigitalDetector:
    return DigitalDetector(PdfPlumberProvider(), TextCleaner(), config)


def _make_pdf(pages: list) -> MagicMock:
    pdf = MagicMock()
    pdf.pages = pages
    pdf.__enter__ = MagicMock(return_value=pdf)
    pdf.__exit__ = MagicMock(return_value=False)
    provider = MagicMock()
    provider.open.return_value = pdf
    return provider


def _make_page(
    text: str = "",
    char_count: int | None = None,
    width: float = 600.0,
    height: float = 800.0,
    word_area_ratio: float = 0.2,
) -> MagicMock:
    """Build a mock page whose word bounding boxes sum to exactly
    `word_area_ratio` of the given page area -- lets tests target a precise
    text-area-ratio without hand-computing bounding boxes."""
    page = MagicMock()
    if char_count is None:
        page.chars = [{"text": ch} for ch in text]
    else:
        page.chars = [{"text": "a"}] * char_count
    page.extract_text.return_value = text
    page.width = width
    page.height = height
    target_area = width * height * word_area_ratio
    page.extract_words.return_value = [{"width": target_area, "height": 1.0}] if target_area else []
    return page


def _blank_page() -> MagicMock:
    page = MagicMock()
    page.chars = []
    return page


def test_sample_contract_is_detected_as_digital(sample_pdf_bytes):
    assert _detector().is_digital(sample_pdf_bytes) is True


def test_garbage_bytes_are_not_digital():
    assert _detector().is_digital(b"not a pdf at all %%%%") is False


def test_empty_bytes_are_not_digital():
    assert _detector().is_digital(b"") is False


def test_page_with_no_chars_is_not_digital():
    provider = _make_pdf([_blank_page()])

    assert DigitalDetector(provider, TextCleaner()).is_digital(b"fake") is False


def test_page_with_few_chars_below_threshold_is_not_digital():
    # 5 chars, below default min_chars=50 -- a bare page number lands here.
    page = _make_page(text="a b c", char_count=5)
    provider = _make_pdf([page])

    assert DigitalDetector(provider, TextCleaner()).is_digital(b"fake") is False


def test_low_letter_ratio_page_is_not_digital():
    page = _make_page(text="1234567890 " * 10, char_count=60)
    provider = _make_pdf([page])

    assert DigitalDetector(provider, TextCleaner()).is_digital(b"fake") is False


def test_dense_digital_page_is_digital():
    text = "This is a real readable paragraph of English text extracted from a document."
    page = _make_page(text=text, word_area_ratio=0.2)
    provider = _make_pdf([page])

    assert DigitalDetector(provider, TextCleaner()).is_digital(b"fake") is True


def test_caption_on_mostly_image_page_is_not_digital():
    """A scanned poster/photo page whose only digital text is a caption long
    enough to clear the char-count and ratio checks on its own -- but the
    words cover a negligible fraction of the page, so it should NOT be
    treated as digital."""
    caption = "Figure 3: Site photo taken 12/01/2026 showing north elevation view."
    page = _make_page(text=caption, word_area_ratio=0.01)  # below default min_text_area_ratio=0.05
    provider = _make_pdf([page])

    assert DigitalDetector(provider, TextCleaner()).is_digital(b"fake") is False


def test_only_first_page_checked_by_default():
    digital_page = _make_page(
        text="This is a real readable paragraph of English text extracted from a document."
    )
    provider = _make_pdf([_blank_page(), digital_page])

    # Page 2 is digital but pages_to_check defaults to 1, so it's never seen.
    assert DigitalDetector(provider, TextCleaner()).is_digital(b"fake") is False
    digital_page.extract_text.assert_not_called()


def test_pages_to_check_can_sample_more_than_one_page():
    digital_page = _make_page(
        text="This is a real readable paragraph of English text extracted from a document."
    )
    provider = _make_pdf([_blank_page(), digital_page])

    config = DigitalDetectorConfig(pages_to_check=2)
    assert DigitalDetector(provider, TextCleaner(), config).is_digital(b"fake") is True
