"""
digital_pdf_reader -- read a digital PDF into cleaned, structured text
(tables interleaved with layout-preserving text), and detect whether a PDF
is digital or scanned in the first place.

Base install depends only on pdfplumber -- including digital detection
(DigitalDetector), which needs no PyMuPDF/fitz dependency at all (see
digital_detector.py for why). The only thing gated behind the `fitz` extra
is fitz_text_reader.read_with_fitz, an optional fallback for when
DocumentReader/pdfplumber fails to extract text from a page already known
digital:

    from digital_pdf_reader.fitz_text_reader import read_with_fitz

FieldValueCleaner is exported but never called by anything else in this
package -- it's an opt-in policy (strip Arabic/markdown from a single field
value) for consumers whose own schema requires English-only output, not a
default text fix. See field_value_cleaner.py for why it must stay opt-in.
"""

from digital_pdf_reader.blocks import BlockKind, DocumentContent, PageBlock
from digital_pdf_reader.digital_detector import DigitalDetector, DigitalDetectorConfig
from digital_pdf_reader.document_reader import DocumentReader, DocumentReaderConfig
from digital_pdf_reader.field_value_cleaner import FieldValueCleaner
from digital_pdf_reader.pdfplumber_provider import PdfPlumberProvider
from digital_pdf_reader.text_cleaner import TextCleaner

__version__ = "0.4.0"

__all__ = [
    "BlockKind",
    "DigitalDetector",
    "DigitalDetectorConfig",
    "DocumentContent",
    "DocumentReader",
    "DocumentReaderConfig",
    "FieldValueCleaner",
    "PageBlock",
    "PdfPlumberProvider",
    "TextCleaner",
    "__version__",
]
