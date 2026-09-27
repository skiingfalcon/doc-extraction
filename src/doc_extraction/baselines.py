"""Docling adapter that returns markdown."""

from pathlib import Path


def extract_docling(pdf_path: Path, converter=None) -> str:
    """Convert a PDF with Docling's layout and table models."""
    from docling.document_converter import DocumentConverter

    if converter is None:
        converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    return result.document.export_to_markdown()


def make_docling_converter():
    from docling.document_converter import DocumentConverter

    return DocumentConverter()
