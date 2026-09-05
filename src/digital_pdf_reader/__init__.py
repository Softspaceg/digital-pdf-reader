"""
digital_pdf_reader -- read a digital PDF into cleaned, structured text
(tables interleaved with layout-preserving text), and detect whether a PDF
is digital or scanned in the first place.

Base install depends only on pdfplumber -- including digital detection
(DigitalDetector), which needs no PyMuPDF/fitz dependency at all (see
digital_detector.py for why). Two modules cost extra dependencies and are
therefore imported as submodules rather than from this package root, so a
base install never pays for what it doesn't use:

    `fitz` extra -- an optional fallback for when DocumentReader/pdfplumber
    fails to extract text from a page already known digital:

        from digital_pdf_reader.fitz_text_reader import read_with_fitz

    `font-remap` extra -- recovers text from a PDF whose ToUnicode table
    disagrees with its embedded fonts' own cmap tables, which extracts as
    scrambled characters (most visibly on Arabic):

        from digital_pdf_reader.font_remap import font_corrected_document_text

PageSelection is the one page-selection contract every reader here shares --
DocumentReader, read_with_fitz and font_corrected_document_text all take it,
so a document read for one purpose and re-read for another covers the same
pages by construction.

FieldValueCleaner is exported but never called by anything else in this
package -- it's an opt-in policy (strip Arabic/markdown from a single field
value) for consumers whose own schema requires English-only output, not a
default text fix. See field_value_cleaner.py for why it must stay opt-in.
"""

from digital_pdf_reader.blocks import BlockKind, DocumentContent, PageBlock
from digital_pdf_reader.digital_detector import DigitalDetector, DigitalDetectorConfig
from digital_pdf_reader.document_reader import DocumentReader, DocumentReaderConfig
from digital_pdf_reader.field_value_cleaner import FieldValueCleaner
from digital_pdf_reader.page_selection import PageSelection
from digital_pdf_reader.pdfplumber_provider import PdfPlumberProvider
from digital_pdf_reader.text_cleaner import TextCleaner

__version__ = "0.5.0"

__all__ = [
    "BlockKind",
    "DigitalDetector",
    "DigitalDetectorConfig",
    "DocumentContent",
    "DocumentReader",
    "DocumentReaderConfig",
    "FieldValueCleaner",
    "PageBlock",
    "PageSelection",
    "PdfPlumberProvider",
    "TextCleaner",
    "__version__",
]
