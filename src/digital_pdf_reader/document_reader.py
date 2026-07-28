"""
DocumentReader -- reads a digital PDF page by page, interleaving tables with
their surrounding text in reading order.

Falls back to plain layout-preserving text for a page when a detected
"table" looks like a dense form region instead of real tabular data.
Consecutive tables that repeat the same header row (e.g. one document
giving every record its own one-row table) are merged into a single grid,
since emitted separately they read as unrelated entities.
"""

from __future__ import annotations

from dataclasses import dataclass

from digital_pdf_reader.blocks import BlockKind, DocumentContent, PageBlock
from digital_pdf_reader.pdfplumber_provider import PdfPlumberProvider
from digital_pdf_reader.text_cleaner import TextCleaner


@dataclass
class DocumentReaderConfig:
    # A cell longer than this means the "table" pdfplumber found is really a
    # dense form region (every field crammed into one cell), not real tabular
    # data -- rendering it as a markdown grid would collapse it to one
    # unreadable line, so the page falls back to plain layout text instead.
    form_layout_cell_threshold: int = 120


@dataclass
class _TableCandidate:
    top: float
    bottom: float
    rows: list[list[str]]


def _cell(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def _table_to_markdown(rows: list[list[str]]) -> str:
    if not rows or not rows[0]:
        return ""
    header, body = rows[0], rows[1:]
    lines = [
        "| " + " | ".join(_cell(c) for c in header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    lines.extend("| " + " | ".join(_cell(c) for c in row) + " |" for row in body)
    return "\n".join(lines) + "\n"


def _has_content(rows: list[list[str]]) -> bool:
    """True if any cell holds text -- pdfplumber reports page furniture
    (footer rules, empty frames) as tables; an all-empty one adds nothing."""
    return any(_cell(cell) for row in rows for cell in row)


def _resolve_page_indices(
    page_count: int, max_pages: int | None, pages: list[int] | None
) -> list[int]:
    """Resolve which 0-based page indices to read.

    If *pages* (1-based) is given, reads exactly those pages -- deduped,
    sorted, out-of-range indices dropped. Otherwise reads the first
    *max_pages* pages, or every page when *max_pages* is None.
    """
    if pages:
        return sorted({page - 1 for page in pages if 1 <= page <= page_count})
    limit = page_count if max_pages is None else min(page_count, max_pages)
    return list(range(limit))


class DocumentReader:
    def __init__(
        self,
        provider: PdfPlumberProvider,
        cleaner: TextCleaner,
        config: DocumentReaderConfig | None = None,
    ) -> None:
        self._provider = provider
        self._cleaner = cleaner
        self._config = config or DocumentReaderConfig()

    def read(
        self,
        raw_bytes: bytes,
        max_pages: int | None = None,
        pages: list[int] | None = None,
        detect_tables: bool = True,
    ) -> DocumentContent:
        """Read a digital PDF into cleaned, structured content.

        By default reads every page with table detection on. Pass *max_pages*/
        *pages* to limit which pages are read, and *detect_tables=False* to
        skip table search entirely -- a fast plain-text-only pass, e.g. for
        callers that only need the first page.
        """
        blocks: list[PageBlock] = []
        with self._provider.open(raw_bytes) as pdf:
            indices = _resolve_page_indices(len(pdf.pages), max_pages, pages)
            for index in indices:
                blocks.extend(self._read_page(pdf.pages[index], detect_tables))
        return DocumentContent(blocks=[self._clean_block(block) for block in blocks])

    def _clean_block(self, block: PageBlock) -> PageBlock:
        cleaned_rows = self._cleaner.clean_table(block.table_rows) if block.table_rows else None
        return PageBlock(
            kind=block.kind,
            text=self._cleaner.clean_full_text(block.text),
            table_rows=cleaned_rows,
        )

    def _read_page(self, page, detect_tables: bool) -> list[PageBlock]:
        if not detect_tables:
            return [self._plain_text_block(page)]
        candidates = self._find_tables(page)
        if not candidates or any(self._is_form_layout(c.rows) for c in candidates):
            return [self._plain_text_block(page)]
        return self._interleave(page, candidates)

    def _find_tables(self, page) -> list[_TableCandidate]:
        candidates = []
        page_height = page.height
        for table in page.find_tables():
            try:
                top, bottom = self._clamp_bbox(table.bbox, page_height)
                if bottom <= top:
                    continue
                rows = table.extract()
                if rows and _has_content(rows):
                    candidates.append(_TableCandidate(top=top, bottom=bottom, rows=rows))
            except Exception:
                continue
        return candidates

    def _clamp_bbox(
        self, bbox: tuple[float, float, float, float], page_height: float
    ) -> tuple[float, float]:
        # pdfplumber can return out-of-range coords for a table's bbox
        _, top, _, bottom = bbox
        return max(0.0, min(top, page_height)), max(0.0, min(bottom, page_height))

    def _is_form_layout(self, rows: list[list[str]]) -> bool:
        threshold = self._config.form_layout_cell_threshold
        return any(cell and len(str(cell)) > threshold for row in rows for cell in row)

    def _plain_text_block(self, page) -> PageBlock:
        return PageBlock(kind=BlockKind.TEXT, text=self._extract_text(page) + "\n")

    def _extract_text(self, page, bbox: tuple[float, float, float, float] | None = None) -> str:
        """Extract text from a page, or from one cropped region of it, preserving
        column layout. Without layout=True, columns collapse into one another
        and values detach from their labels."""
        try:
            region = page if bbox is None else page.within_bbox(bbox)
            text = region.extract_text(layout=True, x_tolerance=3, y_tolerance=3)
            if not text or len(text.strip()) < 10:
                text = region.extract_text()
        except Exception:
            return ""
        return text or ""

    def _crop_text(self, page, top: float, bottom: float) -> str:
        if bottom <= top:
            return ""
        return self._extract_text(page, (0, top, page.width, bottom))

    def _interleave(self, page, candidates: list[_TableCandidate]) -> list[PageBlock]:
        candidates = self._merge_repeated_tables(sorted(candidates, key=lambda c: c.top))
        blocks: list[PageBlock] = []
        current_top = 0.0

        for candidate in candidates:
            if candidate.top > current_top:
                above = self._crop_text(page, current_top, min(candidate.top - 2, page.height))
                if above.strip():
                    blocks.append(PageBlock(kind=BlockKind.TEXT, text=above))
            blocks.append(
                PageBlock(
                    kind=BlockKind.TABLE,
                    text=_table_to_markdown(candidate.rows),
                    table_rows=candidate.rows,
                )
            )
            current_top = candidate.bottom

        if current_top < page.height:
            below = self._crop_text(page, current_top + 2, page.height)
            if below.strip():
                blocks.append(PageBlock(kind=BlockKind.TEXT, text=below))

        return blocks

    def _merge_repeated_tables(self, candidates: list[_TableCandidate]) -> list[_TableCandidate]:
        """Merge consecutive tables that repeat the same header into one grid.

        Some documents give every record its own bordered table -- seven
        principals become seven one-row tables with an identical header.
        Emitted separately they read as seven unrelated entities; merged
        they restore the one N-row table the document is actually showing.
        """
        merged: list[_TableCandidate] = []
        for candidate in candidates:
            shared_rows = self._shared_header_rows(merged[-1].rows, candidate.rows) if merged else 0
            if not shared_rows:
                merged.append(
                    _TableCandidate(
                        top=candidate.top, bottom=candidate.bottom, rows=list(candidate.rows)
                    )
                )
                continue
            previous = merged[-1]
            previous.rows.extend(candidate.rows[shared_rows:])
            previous.bottom = candidate.bottom
        return merged

    def _shared_header_rows(self, earlier: list[list[str]], later: list[list[str]]) -> int:
        """Count the identical leading rows two tables share, or 0 if they
        can't be merged. Requires the shared rows to carry text -- otherwise
        two unrelated tables that both happen to open with a blank row would
        look mergeable."""
        if not earlier or not later or len(earlier[0]) != len(later[0]):
            return 0
        shared_rows = 0
        for earlier_row, later_row in zip(earlier, later):
            if [_cell(cell) for cell in earlier_row] != [_cell(cell) for cell in later_row]:
                break
            shared_rows += 1
        if not shared_rows or not _has_content(earlier[:shared_rows]):
            return 0
        return shared_rows
