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
- `digital_pdf_reader.digital_detector` — `TextRatioDigitalDetector`: digital-
  vs-scanned detection from already-extracted text (printable/letter-
  character ratios). Dependency-free, but has no physical-layout signal.
- `digital_pdf_reader.fitz_digital_detector` — `GeometryDigitalDetector`:
  digital-vs-scanned detection via PyMuPDF block geometry (requires text to
  cover a real fraction of the page's physical area, not just pass a
  character-ratio check). **Requires the `fitz` extra.**
- `digital_pdf_reader.fitz_text_reader` — `read_with_fitz`: a PyMuPDF-backed
  plain-text fallback for when `DocumentReader` returns empty on a page
  already known digital. **Requires the `fitz` extra.**

## Which digital detector should I use?

`GeometryDigitalDetector` is the **recommended, more accurate** detector — the
physical-area check it does is a structural guard against a real false-
positive case that `TextRatioDigitalDetector` cannot express: an isolated
stamp, watermark, or footer with real digital text on an otherwise-scanned
page can pass a pure character-ratio check even though the page is a scan.
It also lets a caller decide up front, before running `DocumentReader`'s
heavier table-detecting extraction, that a page is scanned and skip that
work entirely.

The only reason to prefer `TextRatioDigitalDetector` instead is that
`GeometryDigitalDetector` requires PyMuPDF, which is **dual-licensed
AGPL-3.0 / Artifex Commercial** — resolve that license for your project
before depending on it commercially. If it's unacceptable,
`TextRatioDigitalDetector` is a documented, lower-fidelity fallback, not an
equally-good alternative.

Neither `fitz_digital_detector` nor `fitz_text_reader` is imported by
`digital_pdf_reader/__init__.py`, so a plain `pip install digital-pdf-reader`
never touches PyMuPDF — only a consumer that installs the `fitz` extra and
explicitly imports from those two modules pulls it in.

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
git+https://github.com/Softspaceg/digital-pdf-reader.git@v0.1.0
# add the fitz extra if you want GeometryDigitalDetector / read_with_fitz:
digital-pdf-reader[fitz] @ git+https://github.com/Softspaceg/digital-pdf-reader.git@v0.1.0
```

```toml
# pyproject.toml
dependencies = [
    "digital-pdf-reader[fitz] @ git+https://github.com/Softspaceg/digital-pdf-reader.git@v0.1.0",
]
```

```python
from digital_pdf_reader import DocumentReader, DocumentReaderConfig, PdfPlumberProvider, TextCleaner
from digital_pdf_reader.fitz_digital_detector import GeometryDigitalDetector

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
