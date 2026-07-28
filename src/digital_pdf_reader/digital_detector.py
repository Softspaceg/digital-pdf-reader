"""
Digital-vs-scanned detection.

Checks page.chars first: pdfplumber already parses a page's content stream
into individual character objects as a byproduct of text extraction -- a
scanned page with no embedded text layer produces zero chars, which is a
more direct signal than any heuristic computed after the fact from a string.
The printable/letter-ratio check on top of that filters out pages whose only
"text" is a handful of garbage/placeholder characters.

A char-count/ratio check alone can't tell "this page IS its text" from "this
page is a scanned image/poster that also happens to carry a longer caption
or footer" -- a caption can clear the char-count threshold on its own while
covering a negligible fraction of the page. The text-area-ratio check closes
that gap: it requires the words pdfplumber finds (via page.extract_words(),
which gives each word's bounding box for free) to cover a real fraction of
the page's physical area, not just pass a character-ratio check.

Checking only the first page (the default) is enough to route a document
and avoids extracting the rest of the PDF just to answer a yes/no question.

No extra dependency: pdfplumber is already a hard dependency of this
package, so both checks above need no additional library and no additional
license consideration -- unlike a PyMuPDF-based geometry check, which would
require the `fitz` extra (AGPL-3.0/Artifex Commercial) for what pdfplumber
already answers directly.
"""

from __future__ import annotations

from dataclasses import dataclass

from digital_pdf_reader.pdfplumber_provider import PdfPlumberProvider
from digital_pdf_reader.text_cleaner import TextCleaner


@dataclass
class DigitalDetectorConfig:
    pages_to_check: int = 1
    min_chars: int = 50
    min_printable_ratio: float = 0.85
    min_letter_ratio: float = 0.30
    min_text_area_ratio: float = 0.05


class DigitalDetector:
    """Heuristic check for whether a PDF has a real embedded text layer
    (digital) or is scanned/image-only.

    Samples the first `pages_to_check` pages. A single page that passes the
    text-layer checks is enough to classify the whole document as digital.
    """

    def __init__(
        self,
        provider: PdfPlumberProvider | None = None,
        cleaner: TextCleaner | None = None,
        config: DigitalDetectorConfig | None = None,
    ) -> None:
        self._provider = provider or PdfPlumberProvider()
        self._cleaner = cleaner or TextCleaner()
        self._config = config or DigitalDetectorConfig()

    def is_digital(self, raw_bytes: bytes) -> bool:
        try:
            with self._provider.open(raw_bytes) as pdf:
                limit = min(len(pdf.pages), self._config.pages_to_check)
                return any(self._page_is_digital(pdf.pages[index]) for index in range(limit))
        except Exception:
            return False

    def _page_is_digital(self, page) -> bool:
        if not page.chars:
            return False

        text = self._cleaner.strip_cid_and_control(page.extract_text() or "")
        non_space = [ch for ch in text if not ch.isspace()]
        if len(non_space) < self._config.min_chars:
            return False

        printable_ratio = sum(1 for ch in non_space if ch.isprintable()) / len(non_space)
        letter_ratio = sum(1 for ch in non_space if ch.isalpha()) / len(non_space)
        if (
            printable_ratio < self._config.min_printable_ratio
            or letter_ratio < self._config.min_letter_ratio
        ):
            return False

        return self._text_area_ratio(page) >= self._config.min_text_area_ratio

    def _text_area_ratio(self, page) -> float:
        """Fraction of the page's physical area covered by words -- guards
        against a caption/footer/watermark that clears the char-count
        threshold on its own while the page is really a scanned image."""
        page_area = page.width * page.height
        if page_area == 0:
            return 0.0
        text_area = sum(word["width"] * word["height"] for word in page.extract_words())
        return text_area / page_area
