"""
PageSelection -- which pages of a PDF a reader should read.

Every reader here answers the same question before it reads anything: given
a page count, which pages did the caller ask for? Expressed as a loose
(max_pages, pages) pair it was resolved in two places and travelled through
signatures in inconsistent order, where a positional call could silently swap
the two. One value with named fields makes that impossible and leaves the
rule with a single owner.

Depends on nothing -- usable from the pdfplumber reader, the fitz fallback
and the font-remap recovery alike.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class PageSelection:
    """Explicit *pages* win over a *max_pages* prefix; neither means every page."""

    max_pages: int | None = None
    pages: tuple[int, ...] | None = None

    @classmethod
    def of(cls, pages: Iterable[int]) -> PageSelection:
        """Exactly these 1-based pages."""
        return cls(pages=tuple(pages))

    @classmethod
    def first(cls, max_pages: int) -> PageSelection:
        """A leading prefix of at most *max_pages* pages."""
        return cls(max_pages=max_pages)

    def indices(self, page_count: int) -> list[int]:
        """0-based indices to read -- deduplicated, ordered, out-of-range dropped."""
        if self.pages:
            return sorted({page - 1 for page in self.pages if 1 <= page <= page_count})
        limit = page_count if self.max_pages is None else min(page_count, self.max_pages)
        return list(range(limit))
