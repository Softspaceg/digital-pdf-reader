"""
Digital-vs-scanned detection via PyMuPDF block geometry.

Recommended, more accurate detector: requires meaningful text to also cover a
real fraction of the page's physical area, which text-ratio-only detection
(digital_detector.TextRatioDigitalDetector) can't express -- that guards
against a false positive where an isolated stamp, watermark, or footer with
real digital text sits on an otherwise-scanned page. It also lets a caller
decide up front, before running the heavier pdfplumber table-detecting
extraction, that a page is scanned and skip that work entirely.

Costs a dependency: requires the `fitz` optional extra (PyMuPDF,
AGPL-3.0/Artifex Commercial dual-licensed) -- resolve that license before
shipping commercially. Prefer this detector unless that license is
unacceptable for your project, in which case use TextRatioDigitalDetector as
a documented, lower-fidelity fallback.
"""

from __future__ import annotations

from dataclasses import dataclass

import fitz  # PyMuPDF

from digital_pdf_reader.text_cleaner import TextCleaner


@dataclass
class GeometryDetectorConfig:
    sample_pages: int = 3
    min_chars: int = 50
    min_blocks: int = 2
    min_text_ratio: float = 0.05
    min_printable_ratio: float = 0.85
    min_letter_ratio: float = 0.30


class GeometryDigitalDetector:
    """Heuristic check for a real text layer using PyMuPDF block geometry.

    Samples the first `sample_pages` pages. A single page that passes the
    text-layer checks is enough to classify the whole document as digital.
    """

    def __init__(
        self,
        config: GeometryDetectorConfig | None = None,
        cleaner: TextCleaner | None = None,
    ) -> None:
        self._config = config or GeometryDetectorConfig()
        self._cleaner = cleaner or TextCleaner()

    def is_digital(self, raw_bytes: bytes) -> bool:
        try:
            doc = fitz.open(stream=raw_bytes, filetype="pdf")
            try:
                limit = min(len(doc), self._config.sample_pages)
                return any(self._page_has_digital_text(doc[index]) for index in range(limit))
            finally:
                doc.close()
        except Exception:
            return False

    def _page_has_digital_text(self, page: fitz.Page) -> bool:
        blocks = page.get_text("blocks")  # [(x0,y0,x1,y1,text,block_no,block_type), ...]
        page_area = page.rect.width * page.rect.height
        if page_area == 0:
            return False

        meaningful_block_count = 0
        char_count = 0
        text_area = 0.0

        for block in blocks:
            if block[6] != 0:  # skip image blocks
                continue
            cleaned = self._cleaner.strip_cid_and_control(block[4])
            if not cleaned:
                continue

            printable_ratio = sum(1 for ch in cleaned if ch.isprintable()) / len(cleaned)
            letter_ratio = sum(1 for ch in cleaned if ch.isalpha()) / len(cleaned)
            if not (
                printable_ratio >= self._config.min_printable_ratio
                and letter_ratio >= self._config.min_letter_ratio
            ):
                continue

            block_area = (block[2] - block[0]) * (block[3] - block[1])
            if block_area / page_area < 0.01:  # block must cover >= 1% of page
                continue

            meaningful_block_count += 1
            char_count += len(cleaned)
            text_area += block_area

        text_ratio = text_area / page_area
        return (
            char_count >= self._config.min_chars
            and meaningful_block_count >= self._config.min_blocks
            and text_ratio >= self._config.min_text_ratio
        )
