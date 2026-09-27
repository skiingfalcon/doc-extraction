"""Rasterize PDF pages for Nemotron Parse and for the scanned memo variant."""

from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image

from doc_extraction.paths import MAX_HEIGHT, MAX_WIDTH


def render_pdf(pdf_path: Path) -> list[Image.Image]:
    """Return one RGB image per page, scaled to fit inside 1664×2048."""
    document = pdfium.PdfDocument(str(pdf_path))
    try:
        return [_render_page(document[index]) for index in range(len(document))]
    finally:
        document.close()


def render_pdf_at_dpi(pdf_path: Path, dpi: int) -> list[Image.Image]:
    """Return one RGB image per page at a fixed resolution."""
    document = pdfium.PdfDocument(str(pdf_path))
    try:
        return [
            document[index].render(scale=dpi / 72).to_pil().convert("RGB")
            for index in range(len(document))
        ]
    finally:
        document.close()


def _render_page(page: pdfium.PdfPage) -> Image.Image:
    width_pt, height_pt = page.get_size()
    scale = min(MAX_WIDTH / width_pt, MAX_HEIGHT / height_pt)
    bitmap = page.render(scale=scale)
    image = bitmap.to_pil().convert("RGB")
    if image.width > MAX_WIDTH or image.height > MAX_HEIGHT:
        image.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.Resampling.LANCZOS)
    return image
