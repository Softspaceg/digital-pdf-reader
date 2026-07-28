# digital-pdf-reader

Single source of truth for reading a digital PDF (one with a real embedded
text layer, as opposed to a scan) into cleaned, structured text. Shared
across `ocr-pipeline` and `asico-pm`, which independently built near-identical
readers for this — table/text interleaving in reading order, a form-layout
fallback, doubled-character repair, and Arabic visual-order repair — so a fix
to any of that logic happens once and takes effect in both.

## Modules

- `digital_pdf_reader.blocks` — `BlockKind`, `PageBlock`, `DocumentContent`
  (with `.full_text` and `.raw_tables` convenience properties).
- `digital_pdf_reader.pdfplumber_provider` — `PdfPlumberProvider`, a thin
  wrapper around `pdfplumber.open`.
- `digital_pdf_reader.text_cleaner` — `TextCleaner`: doubled-character repair
  (`"CCoonnttrraacctt"` → `"Contract"`), Arabic visual-order repair, and
  cid/control-character stripping.
- `digital_pdf_reader.document_reader` — `DocumentReader.read(raw_bytes,
  max_pages=None, pages=None, detect_tables=True) -> DocumentContent`. Reads
  page by page, interleaving detected tables with the surrounding text in
  top-to-bottom order; falls back to plain layout-preserving text for a page
  when a detected "table" is actually a dense form region (a cell over
  `form_layout_cell_threshold` characters). Tables that repeat the same
  header row across consecutive one-record tables are merged into a single
  grid. Pass `pages=[1]` and `detect_tables=False` for a fast single-page,
  no-table-search read.
- `digital_pdf_reader.digital_detector` — `DigitalDetector`: digital-vs-scanned
  detection. Checks the first page only by default (`pages_to_check=1`):
  pdfplumber already parses a page's content stream into character objects
  (`page.chars`) as a byproduct of text extraction, so a scanned page with no
  embedded text layer produces zero chars — a more direct signal than any
  ratio computed after the fact from a string. That's combined with two
  further checks over the page's text: a printable/letter-ratio check (to
  filter out pages whose only "chars" are a handful of garbage/placeholder
  glyphs), and a text-area-ratio check via `page.extract_words()` bounding
  boxes (to filter out a scanned poster/photo page whose only digital text
  is a caption or footer long enough to clear the char-count check on its
  own, but covers a negligible fraction of the page).
- `digital_pdf_reader.fitz_text_reader` — `read_with_fitz`: a PyMuPDF-backed
  plain-text fallback for when `DocumentReader` returns empty on a page
  already known digital. **Requires the `fitz` extra.**

## Why no PyMuPDF for digital detection

An earlier version of this package shipped a PyMuPDF/fitz-based "geometry"
detector (checking whether text covers a real fraction of a page's physical
area) alongside a pdfplumber-only text-ratio detector, reasoning that the
area check was needed for accuracy but required PyMuPDF's AGPL-3.0/Artifex
Commercial license. That turned out to be a false trade-off: pdfplumber's
own `page.extract_words()` already returns each word's bounding box for
free, as a byproduct of the extraction work this package does anyway — so
the same area-ratio check can be computed without any extra dependency.
Char-count alone screens out a short stamp/watermark, but not a longer
caption/footer on a scanned poster or photo page that clears `min_chars` on
its own; the area-ratio check catches that case specifically (see
`test_caption_on_mostly_image_page_is_not_digital` in the test suite).
`DigitalDetector` is dependency-free and is the only detector this package
ships.

`fitz_text_reader` is unrelated to detection — it's a fallback for the
separate concern of *extracting* text once a page is already known digital,
for the rare case pdfplumber's extraction itself fails. It is not imported
by `digital_pdf_reader/__init__.py`, so a plain `pip install
digital-pdf-reader` never touches PyMuPDF — only a consumer that installs
the `fitz` extra and explicitly imports from that module pulls it in.

## What's deliberately *not* here

Stripping Arabic characters or markdown markup from a single field/cell
value (as opposed to a whole document's text) is a downstream, schema-
specific business rule — e.g. an app whose structured output should only
ever contain English values — not a property of "reading a digital PDF."
Consumers that need that should layer it on top of this package's output in
their own codebase.

## Using this from another project

Not published to PyPI — install straight from this repo, pinned to a tag:

```
# requirements.txt
git+https://github.com/Softspaceg/digital-pdf-reader.git@v0.3.0
# add the fitz extra only if you want read_with_fitz's fallback text reader:
digital-pdf-reader[fitz] @ git+https://github.com/Softspaceg/digital-pdf-reader.git@v0.3.0
```

```toml
# pyproject.toml
dependencies = [
    "digital-pdf-reader @ git+https://github.com/Softspaceg/digital-pdf-reader.git@v0.3.0",
]
```

```python
from digital_pdf_reader import (
    DigitalDetector,
    DocumentReader,
    DocumentReaderConfig,
    PdfPlumberProvider,
    TextCleaner,
)

is_digital = DigitalDetector().is_digital(raw_bytes)
reader = DocumentReader(PdfPlumberProvider(), TextCleaner(), DocumentReaderConfig())
content = reader.read(raw_bytes)
print(content.full_text)
```

Docker images need `git` installed in the build stage for pip to clone this
(the repo is public, so no credentials are needed either locally or in CI).

## Releasing a new version

1. Bump `version` in `pyproject.toml` (and `src/digital_pdf_reader/__init__.py`).
2. Commit, then tag: `git tag -a vX.Y.Z -m "..."` and `git push origin main --tags`.
3. Bump the `@vX.Y.Z` pin in every consuming project's `requirements.txt` /
   `pyproject.toml` and reinstall.

## Development

```bash
pip install -e ".[dev,fitz]"
pytest
```
