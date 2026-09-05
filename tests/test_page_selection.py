"""Unit tests for PageSelection -- the one page-selection rule DocumentReader,
read_with_fitz and font_corrected_document_text all share, so a document read
for one purpose and re-read for another covers the same pages by construction."""

from __future__ import annotations

from digital_pdf_reader.page_selection import PageSelection


class TestIndices:
    def test_nothing_set_reads_the_whole_document(self):
        assert PageSelection().indices(4) == [0, 1, 2, 3]

    def test_max_pages_reads_a_leading_prefix(self):
        assert PageSelection(max_pages=2).indices(5) == [0, 1]

    def test_max_pages_beyond_the_document_reads_what_exists(self):
        assert PageSelection(max_pages=10).indices(2) == [0, 1]

    def test_explicit_pages_convert_from_one_based(self):
        assert PageSelection.of([1, 3]).indices(5) == [0, 2]

    def test_explicit_pages_win_over_max_pages(self):
        assert PageSelection(max_pages=2, pages=(5,)).indices(5) == [4]

    def test_out_of_range_pages_are_dropped(self):
        assert PageSelection.of([2, 9, 0]).indices(3) == [1]

    def test_duplicates_and_order_are_normalized(self):
        assert PageSelection.of([3, 1, 3]).indices(3) == [0, 2]

    def test_an_empty_page_list_falls_back_to_the_prefix_rule(self):
        assert PageSelection.of([]).indices(3) == [0, 1, 2]


class TestConstructors:
    def test_of_names_exact_pages(self):
        assert PageSelection.of([2, 4]) == PageSelection(pages=(2, 4))

    def test_first_names_a_prefix(self):
        assert PageSelection.first(3) == PageSelection(max_pages=3)
