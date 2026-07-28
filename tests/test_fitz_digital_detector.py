"""Unit tests for GeometryDigitalDetector (fitz/PyMuPDF-backed, recommended
detector). Requires the `fitz` extra to be installed."""

from __future__ import annotations

from digital_pdf_reader.fitz_digital_detector import GeometryDigitalDetector


def test_sample_contract_is_detected_as_digital(sample_pdf_bytes):
    assert GeometryDigitalDetector().is_digital(sample_pdf_bytes) is True


def test_garbage_bytes_are_not_digital():
    assert GeometryDigitalDetector().is_digital(b"not a pdf at all %%%%") is False


def test_empty_bytes_are_not_digital():
    assert GeometryDigitalDetector().is_digital(b"") is False
