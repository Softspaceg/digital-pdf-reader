"""
Digital-vs-scanned detection derived from already-extracted text.

Dependency-free fallback: cheaper than fitz_digital_detector.GeometryDigitalDetector
and has no PyMuPDF dependency, but no physical-layout signal either -- an
isolated stamp, watermark, or footer with real digital text on an otherwise-
scanned page can pass this check when it shouldn't. Prefer
GeometryDigitalDetector unless PyMuPDF's AGPL-3.0/Artifex Commercial license
is unacceptable for your project.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TextRatioDetectorConfig:
    min_chars: int = 50
    min_printable_ratio: float = 0.85
    min_letter_ratio: float = 0.30


class TextRatioDigitalDetector:
    """Heuristic check for whether extracted text looks like a real text
    layer (digital) or negligible/garbled leftovers (scanned)."""

    def __init__(self, config: TextRatioDetectorConfig | None = None) -> None:
        self._config = config or TextRatioDetectorConfig()

    def is_digital(self, text: str) -> bool:
        # Non-whitespace only: layout-preserving extraction pads output with
        # runs of spaces to preserve column alignment -- often over half the
        # string -- which would otherwise dilute the letter ratio below any
        # reasonable threshold regardless of how much real text there is.
        non_space = [ch for ch in text if not ch.isspace()]
        if len(non_space) < self._config.min_chars:
            return False

        printable_ratio = sum(1 for ch in non_space if ch.isprintable()) / len(non_space)
        letter_ratio = sum(1 for ch in non_space if ch.isalpha()) / len(non_space)
        return (
            printable_ratio >= self._config.min_printable_ratio
            and letter_ratio >= self._config.min_letter_ratio
        )
