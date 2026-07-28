"""
Digital-vs-scanned detection.

Checks page.chars first: pdfplumber already parses a page's content stream
into individual character objects as a byproduct of text extraction -- a
scanned page with no embedded text layer produces zero chars, which is a
more direct signal than any heuristic computed after the fact from a string.
The printable/letter-ratio check on top of that filters out pages whose only
"text" is a handful of garbage/placeholder characters.

Checking only the first page (the default) is enough to route a document
and avoids extracting the rest of the PDF just to answer a yes/no question.

No extra dependency: pdfplumber is already a hard dependency of this
package, so this needs no additional library and no additional license
consideration -- unlike a PyMuPDF-based geometry check, which would require
the `fitz` extra (AGPL-3.0/Artifex Commercial) for what page.chars already
answers directly.
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
        return (
            printable_ratio >= self._config.min_printable_ratio
            and letter_ratio >= self._config.min_letter_ratio
        )
