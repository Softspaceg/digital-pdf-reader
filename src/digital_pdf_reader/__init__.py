"""
digital_pdf_reader -- read a digital PDF into cleaned, structured text
(tables interleaved with layout-preserving text).

Base install depends only on pdfplumber. Two digital-detection strategies
are available; only TextRatioDigitalDetector is exported from here, since it
has no extra dependency. The more accurate GeometryDigitalDetector (and the
fitz text-reading fallback) require the `fitz` extra and must be imported
from their own modules explicitly -- see README for the trade-off:

    from digital_pdf_reader.fitz_digital_detector import GeometryDigitalDetector
    from digital_pdf_reader.fitz_text_reader import read_with_fitz
"""

from digital_pdf_reader.blocks import BlockKind, DocumentContent, PageBlock
from digital_pdf_reader.digital_detector import TextRatioDetectorConfig, TextRatioDigitalDetector
from digital_pdf_reader.document_reader import DocumentReader, DocumentReaderConfig
from digital_pdf_reader.pdfplumber_provider import PdfPlumberProvider
from digital_pdf_reader.text_cleaner import TextCleaner

__version__ = "0.1.0"

__all__ = [
    "BlockKind",
    "DocumentContent",
    "DocumentReader",
    "DocumentReaderConfig",
    "PageBlock",
    "PdfPlumberProvider",
    "TextCleaner",
    "TextRatioDetectorConfig",
    "TextRatioDigitalDetector",
    "__version__",
]
