import io

import pdfplumber
from pdfplumber.pdf import PDF


class PdfPlumberProvider:
    """Wraps pdfplumber. Knows nothing about documents, fields, or business
    rules -- one job: open a PDF from raw bytes and hand back its pages."""

    def open(self, raw_bytes: bytes) -> PDF:
        return pdfplumber.open(io.BytesIO(raw_bytes))
