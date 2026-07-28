"""Unit tests for DocumentReader -- table/text interleaving, form-layout
fallback, repeated-table merging, page selection, and detect_tables=False.

Uses mocked pdfplumber page/table objects for the per-page logic (mirrors
real pdfplumber's API shape without needing a real file), plus the real
sample_contract.pdf fixture for end-to-end integration checks.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from digital_pdf_reader.blocks import BlockKind
from digital_pdf_reader.document_reader import (
    DocumentReader,
    DocumentReaderConfig,
    _cell,
    _has_content,
    _resolve_page_indices,
    _table_to_markdown,
    _TableCandidate,
)
from digital_pdf_reader.pdfplumber_provider import PdfPlumberProvider
from digital_pdf_reader.text_cleaner import TextCleaner


def _make_page(
    tables=None,
    layout_text="Layout extracted text for the document.",
    plain_text="Plain extracted text.",
    height=842.0,
    width=595.0,
) -> MagicMock:
    page = MagicMock()
    page.height = height
    page.width = width
    page.find_tables.return_value = tables or []
    page.extract_text.side_effect = [layout_text, plain_text] * 5
    return page


def _make_table_mock(bbox=(50, 100, 400, 300), data=None, raise_on_extract=False) -> MagicMock:
    table = MagicMock()
    table.bbox = bbox
    if raise_on_extract:
        table.extract.side_effect = RuntimeError("extraction failed")
    else:
        table.extract.return_value = data or [["Name", "Amount"], ["Alice", "100"]]
    return table


def _reader() -> DocumentReader:
    return DocumentReader(PdfPlumberProvider(), TextCleaner(), DocumentReaderConfig())


class TestCell:
    def test_none_returns_empty(self):
        assert _cell(None) == ""

    def test_normal_string_unchanged(self):
        assert _cell("Contract") == "Contract"

    def test_internal_multi_whitespace_collapsed(self):
        assert _cell("hello   world") == "hello world"

    def test_integer_converted_to_string(self):
        assert _cell(42) == "42"


class TestTableToMarkdown:
    def test_empty_list_returns_empty(self):
        assert _table_to_markdown([]) == ""

    def test_header_only_produces_header_and_separator(self):
        result = _table_to_markdown([["Name", "Amount"]])
        lines = result.strip().splitlines()
        assert "Name" in lines[0]
        assert "---" in lines[1]
        assert len(lines) == 2

    def test_multiple_data_rows(self):
        data = [["A", "B"], ["1", "2"], ["3", "4"]]
        result = _table_to_markdown(data)
        assert len(result.strip().splitlines()) == 4

    def test_none_cells_become_empty(self):
        result = _table_to_markdown([["Name", None], [None, "100"]])
        assert "None" not in result


class TestHasContent:
    def test_empty_rows_has_no_content(self):
        assert _has_content([["", None], [" ", ""]]) is False

    def test_any_cell_with_text_has_content(self):
        assert _has_content([["", ""], ["value", ""]]) is True


class TestResolvePageIndices:
    def test_no_pages_no_cap_reads_everything(self):
        assert _resolve_page_indices(page_count=4, max_pages=None, pages=None) == [0, 1, 2, 3]

    def test_no_pages_falls_back_to_front_n_cap(self):
        assert _resolve_page_indices(page_count=10, max_pages=3, pages=None) == [0, 1, 2]

    def test_no_pages_capped_by_page_count(self):
        assert _resolve_page_indices(page_count=2, max_pages=6, pages=None) == [0, 1]

    def test_explicit_pages_converted_to_0_based(self):
        assert _resolve_page_indices(page_count=10, max_pages=6, pages=[2, 4]) == [1, 3]

    def test_out_of_range_pages_dropped(self):
        assert _resolve_page_indices(page_count=3, max_pages=6, pages=[1, 6, 0]) == [0]

    def test_duplicates_and_order_normalized(self):
        assert _resolve_page_indices(page_count=10, max_pages=6, pages=[5, 1, 1]) == [0, 4]

    def test_empty_pages_list_falls_back_to_cap(self):
        assert _resolve_page_indices(page_count=10, max_pages=2, pages=[]) == [0, 1]


class TestIsFormLayout:
    def test_short_cells_not_form_layout(self):
        reader = _reader()
        assert reader._is_form_layout([["Name", "Amount"], ["Alice", "100"]]) is False

    def test_long_cell_triggers_form_layout(self):
        reader = _reader()
        long_text = "A" * 121
        assert reader._is_form_layout([["Header"], [long_text]]) is True

    def test_exactly_at_threshold_not_triggered(self):
        reader = _reader()
        assert reader._is_form_layout([["H"], ["A" * 120]]) is False


class TestReadPageFormLayoutFallback:
    def test_form_layout_falls_back_to_plain_text(self):
        long_cell = "B" * 200
        table = MagicMock()
        table.bbox = (0, 50, 595, 400)
        table.extract.return_value = [["Header"], [long_cell]]
        page = _make_page(
            tables=[table],
            layout_text="Clean readable layout text for the document page.",
        )
        reader = _reader()

        blocks = reader._read_page(page, detect_tables=True)

        assert len(blocks) == 1
        assert blocks[0].kind is BlockKind.TEXT
        assert long_cell not in blocks[0].text
        assert "Clean readable layout text" in blocks[0].text

    def test_normal_table_produces_table_and_text_blocks(self):
        table = _make_table_mock(
            bbox=(50, 100, 400, 300), data=[["Name", "Amount"], ["Alice", "100"]]
        )
        page = _make_page(tables=[table], height=842.0, width=595.0)
        page.within_bbox.return_value = MagicMock(extract_text=MagicMock(return_value=None))
        reader = _reader()

        blocks = reader._read_page(page, detect_tables=True)

        table_blocks = [b for b in blocks if b.kind is BlockKind.TABLE]
        assert len(table_blocks) == 1
        assert "Alice" in table_blocks[0].text
        assert table_blocks[0].table_rows == [["Name", "Amount"], ["Alice", "100"]]

    def test_no_tables_returns_plain_text_block(self):
        page = _make_page(layout_text="This is the full page content here.")
        reader = _reader()

        blocks = reader._read_page(page, detect_tables=True)

        assert len(blocks) == 1
        assert blocks[0].kind is BlockKind.TEXT
        assert "This is the full page content here." in blocks[0].text

    def test_detect_tables_false_skips_table_search_entirely(self):
        page = _make_page(layout_text="Fast first-page text only.")
        reader = _reader()

        blocks = reader._read_page(page, detect_tables=False)

        page.find_tables.assert_not_called()
        assert len(blocks) == 1
        assert blocks[0].kind is BlockKind.TEXT
        assert "Fast first-page text only." in blocks[0].text

    def test_table_extraction_exception_skips_that_table(self):
        bad_table = _make_table_mock(raise_on_extract=True)
        page = _make_page(tables=[bad_table], layout_text="Page content without table.")
        reader = _reader()

        blocks = reader._read_page(page, detect_tables=True)

        assert len(blocks) == 1
        assert "Page content without table." in blocks[0].text

    def test_table_bbox_outside_page_is_clamped_and_skipped(self):
        table = _make_table_mock(
            bbox=(0, 1280.38, 595, 2869.6),  # entirely outside an 842-tall page
            data=[["Name", "Amount"], ["Alice", "100"]],
        )
        page = _make_page(tables=[table], height=842.0, width=595.0)
        reader = _reader()

        blocks = reader._read_page(page, detect_tables=True)

        assert len(blocks) == 1
        assert "Alice" not in blocks[0].text

    def test_empty_table_is_skipped_as_page_furniture(self):
        # An all-empty table (footer rule, blank frame) shouldn't surface as
        # a TABLE block -- it adds nothing and would push real text down the
        # non-layout-preserving interleave path for no reason.
        table = _make_table_mock(data=[["", None], [None, ""]])
        page = _make_page(tables=[table], layout_text="Only real content on this page.")
        reader = _reader()

        blocks = reader._read_page(page, detect_tables=True)

        assert len(blocks) == 1
        assert blocks[0].kind is BlockKind.TEXT


class TestMergeRepeatedTables:
    def test_tables_with_identical_header_are_merged(self):
        reader = _reader()
        header = ["Name", "Role"]
        first = _TableCandidate(top=100.0, bottom=150.0, rows=[header, ["Alice", "Buyer"]])
        second = _TableCandidate(top=200.0, bottom=250.0, rows=[header, ["Bob", "Seller"]])

        merged = reader._merge_repeated_tables([first, second])

        assert len(merged) == 1
        assert merged[0].rows == [header, ["Alice", "Buyer"], ["Bob", "Seller"]]
        assert merged[0].bottom == 250.0

    def test_tables_with_different_headers_are_not_merged(self):
        reader = _reader()
        first_rows = [["Name", "Role"], ["Alice", "Buyer"]]
        second_rows = [["Amount", "Date"], ["500", "2026-01-01"]]
        first = _TableCandidate(top=100.0, bottom=150.0, rows=first_rows)
        second = _TableCandidate(top=200.0, bottom=250.0, rows=second_rows)

        merged = reader._merge_repeated_tables([first, second])

        assert len(merged) == 2

    def test_three_repeated_single_row_tables_merge_into_one(self):
        reader = _reader()
        header = ["Principal", "Share"]
        candidates = [
            _TableCandidate(
                top=100.0 + i * 50, bottom=140.0 + i * 50, rows=[header, [f"P{i}", "10%"]]
            )
            for i in range(3)
        ]

        merged = reader._merge_repeated_tables(candidates)

        assert len(merged) == 1
        assert len(merged[0].rows) == 4  # header + 3 records
        assert merged[0].bottom == candidates[-1].bottom

    def test_blank_shared_header_does_not_merge(self):
        # Two unrelated tables that both happen to open with a blank row
        # shouldn't look mergeable just because that row matches.
        reader = _reader()
        blank_header = ["", ""]
        first = _TableCandidate(top=100.0, bottom=150.0, rows=[blank_header, ["Alice", "100"]])
        second = _TableCandidate(top=200.0, bottom=250.0, rows=[blank_header, ["Bob", "200"]])

        merged = reader._merge_repeated_tables([first, second])

        assert len(merged) == 2

    def test_single_table_passes_through_unchanged(self):
        reader = _reader()
        only = _TableCandidate(top=100.0, bottom=150.0, rows=[["A", "B"], ["1", "2"]])

        merged = reader._merge_repeated_tables([only])

        assert merged == [only]


class TestDocumentReaderIntegration:
    def test_read_finds_tables_and_full_text(
        self, sample_pdf_bytes, pdfplumber_provider, cleaner, reader_config
    ):
        reader = DocumentReader(pdfplumber_provider, cleaner, reader_config)

        content = reader.read(sample_pdf_bytes)

        assert len(content.raw_tables) >= 5
        assert "ASIC-2026-0006798" in content.full_text

    def test_detect_tables_false_reads_only_first_page_plain_text(
        self, sample_pdf_bytes, pdfplumber_provider, cleaner, reader_config
    ):
        reader = DocumentReader(pdfplumber_provider, cleaner, reader_config)

        content = reader.read(sample_pdf_bytes, pages=[1], detect_tables=False)

        assert len(content.blocks) == 1
        assert content.blocks[0].kind is BlockKind.TEXT
        assert content.raw_tables == []
        assert "ASIC-2026-0006798" in content.full_text

    def test_max_pages_limits_pages_read(
        self, sample_pdf_bytes, pdfplumber_provider, cleaner, reader_config
    ):
        reader = DocumentReader(pdfplumber_provider, cleaner, reader_config)

        full = reader.read(sample_pdf_bytes)
        limited = reader.read(sample_pdf_bytes, max_pages=1)

        assert len(limited.blocks) <= len(full.blocks)
