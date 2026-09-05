"""
Font-remap text correction.

Some PDFs embed a full (non-subsetted) TrueType font whose *own* internal
cmap table (Unicode -> glyph) disagrees with the PDF's ToUnicode table (used
to decode copy/search text) -- the glyphs render correctly, but text
extraction reads the wrong characters, most visibly on Arabic content. Since
the font's own cmap table describes what the font itself considers each
glyph to mean, it's a more trustworthy source than the PDF's ToUnicode table
when the two disagree.

This reads each character's actual glyph ID (via PyMuPDF's low-level
get_texttrace(), not the ToUnicode-decoded guess), looks up that glyph's name
in the embedded font (fontTools), and reverse-looks-up that name in the
font's own cmap to recover the Unicode it actually represents. `python-bidi`
then reorders each reconstructed line into correct reading order (handles
mixed English/Arabic and digit runs correctly; a naive "reverse the RTL
characters" pass does not -- it flips date digits too).

Fonts without their own usable cmap table (e.g. subsetted fonts, which often
drop it entirely) have nothing to correct from -- callers should treat a
corrected_line_count of 0 as "not recoverable this way" and fall back to
whatever they use for non-digital documents (OCR, a vision model).

Costs dependencies: requires the `font-remap` optional extra (PyMuPDF,
fontTools, python-bidi). Import it as a submodule, never from the package
root, so a base install that never remaps fonts stays pdfplumber-only:

    from digital_pdf_reader.font_remap import font_corrected_document_text
"""

from __future__ import annotations

import io
import logging
import unicodedata
from collections import defaultdict
from dataclasses import dataclass

import fitz
from bidi.algorithm import get_display
from fontTools.ttLib import TTFont

from digital_pdf_reader.page_selection import PageSelection

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class _FontCorrectionMap:
    """Per-font glyph-ID -> Unicode lookup, built from the font's own cmap table."""

    glyph_order: list[str]
    reverse_cmap: dict[str, int]


def _is_arabicish(character: str) -> bool:
    return "\u0600" <= character <= "\u06ff" or "\ufb50" <= character <= "\ufeff"


def _build_font_maps(doc: fitz.Document, page: fitz.Page) -> dict[str, _FontCorrectionMap]:
    """Build a glyph-ID -> Unicode map per font used on *page*, skipping any
    font whose embedded program can't be parsed or has no cmap table of its
    own -- there is nothing to correct from in that case."""
    font_maps: dict[str, _FontCorrectionMap] = {}
    for font_xref, _ext, _font_type, basefont, _name, _enc, _ref in page.get_fonts(full=True):
        if basefont in font_maps:
            continue
        try:
            font_bytes = doc.extract_font(font_xref)[-1]
            if not font_bytes:
                continue
            ttf = TTFont(io.BytesIO(font_bytes), fontNumber=0, lazy=True)
            if "cmap" not in ttf:
                continue
            reverse_cmap: dict[str, int] = {}
            for unicode_cp, glyph_name in (ttf.getBestCmap() or {}).items():
                reverse_cmap.setdefault(glyph_name, unicode_cp)
            font_map = _FontCorrectionMap(
                glyph_order=ttf.getGlyphOrder(),
                reverse_cmap=reverse_cmap,
            )
        except Exception:
            log.debug("[font_remap] could not read embedded font %r", basefont, exc_info=True)
            continue
        font_maps[basefont] = font_map
        # texttrace may report the font name without its subset-tag prefix ("AAAAAB+...")
        font_maps.setdefault(basefont.split("+")[-1], font_map)
    return font_maps


def _reassemble_line(entries: list[tuple[int | None, int]]) -> tuple[str, bool]:
    """entries: (corrected_codepoint_or_none, original_codepoint), sorted by
    on-page x-position. Falls back to the PDF's original codepoint wherever
    no font-level correction is available. Returns (line text, was_corrected)."""
    characters = []
    was_corrected = False
    for corrected_cp, original_cp in entries:
        codepoint = corrected_cp if corrected_cp is not None else original_cp
        was_corrected = was_corrected or (corrected_cp is not None and corrected_cp != original_cp)
        characters.append(chr(codepoint))

    text = "".join(characters)
    if any(_is_arabicish(character) for character in text):
        text = get_display(unicodedata.normalize("NFKC", text))
    return text, was_corrected


def _corrected_page_text(
    page: fitz.Page,
    font_maps: dict[str, _FontCorrectionMap],
) -> tuple[str, int]:
    """Returns (page text, number of lines that needed font-level correction)."""
    entries_by_line: dict[int, list[tuple[float, int | None, int]]] = defaultdict(list)
    for span in page.get_texttrace():
        font_map = font_maps.get(span["font"])
        for codepoint, glyph_id, _origin, bbox in span["chars"]:
            corrected_cp = None
            if font_map is not None and glyph_id < len(font_map.glyph_order):
                glyph_name = font_map.glyph_order[glyph_id]
                corrected_cp = font_map.reverse_cmap.get(glyph_name)
            entries_by_line[round(bbox[1])].append((bbox[0], corrected_cp, codepoint))

    lines = []
    corrected_line_count = 0
    for top in sorted(entries_by_line):
        line_entries = sorted(entries_by_line[top], key=lambda entry: entry[0])
        text, was_corrected = _reassemble_line([(entry[1], entry[2]) for entry in line_entries])
        lines.append(text)
        corrected_line_count += int(was_corrected)
    return "\n".join(lines), corrected_line_count


def font_corrected_document_text(
    raw_bytes: bytes, selection: PageSelection | None = None
) -> tuple[str, int]:
    """
    Recover text using each embedded font's own cmap table instead of the
    PDF's (possibly wrong) ToUnicode table, over the pages *selection* names —
    the same selection the digital text reader used, so a recovered read
    covers the pages its caller asked for and no others.

    Returns (corrected_text, corrected_line_count). A corrected_line_count of
    0 means no font on these pages had a usable cmap to correct from (e.g.
    subsetted fonts) -- treat that as "not recoverable this way".
    """
    selection = selection or PageSelection()
    doc = fitz.open(stream=raw_bytes, filetype="pdf")
    try:
        pages_text = []
        total_corrected = 0
        for page_index in selection.indices(doc.page_count):
            page = doc[page_index]
            text, corrected_count = _corrected_page_text(page, _build_font_maps(doc, page))
            pages_text.append(text)
            total_corrected += corrected_count
        return "\n\n".join(pages_text), total_corrected
    finally:
        doc.close()
