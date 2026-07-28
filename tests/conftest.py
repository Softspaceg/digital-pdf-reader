from pathlib import Path

import pytest

from digital_pdf_reader.document_reader import DocumentReaderConfig
from digital_pdf_reader.pdfplumber_provider import PdfPlumberProvider
from digital_pdf_reader.text_cleaner import TextCleaner

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    return (FIXTURES_DIR / "sample_contract.pdf").read_bytes()


@pytest.fixture
def cleaner() -> TextCleaner:
    return TextCleaner()


@pytest.fixture
def pdfplumber_provider() -> PdfPlumberProvider:
    return PdfPlumberProvider()


@pytest.fixture
def reader_config() -> DocumentReaderConfig:
    return DocumentReaderConfig()
