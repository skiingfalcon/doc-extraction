"""Turn a digital memo PDF into an image-only "scanned" PDF with no text layer."""

import io
import random
from pathlib import Path

import numpy as np
from PIL import Image

from doc_extraction.render import render_pdf_at_dpi

SCAN_DPI = 200
_MAX_ROTATION_DEGREES = 0.8
_NOISE_SIGMA = 6.0
_JPEG_QUALITY = 55


def degrade_pdf(source: Path, dest: Path, seed: str) -> Path:
    """Rasterize ``source``, degrade every page deterministically, and save ``dest``."""
    rng = random.Random(seed)
    pages = [degrade_page(image, rng) for image in render_pdf_at_dpi(source, SCAN_DPI)]
    dest.parent.mkdir(parents=True, exist_ok=True)
    first, *rest = pages
    first.save(
        dest,
        "PDF",
        save_all=True,
        append_images=rest,
        resolution=SCAN_DPI,
        # Fixed metadata keeps regenerated PDFs byte-identical.
        title=source.stem,
        creationDate=None,
        modDate=None,
    )
    return dest


def degrade_page(image: Image.Image, rng: random.Random) -> Image.Image:
    """Grayscale, a slight skew, sensor noise, and a lossy JPEG round trip."""
    gray = image.convert("L")
    angle = rng.uniform(-_MAX_ROTATION_DEGREES, _MAX_ROTATION_DEGREES)
    skewed = gray.rotate(angle, resample=Image.Resampling.BICUBIC, expand=False, fillcolor=255)
    noise = np.random.default_rng(rng.getrandbits(32)).normal(0.0, _NOISE_SIGMA, (skewed.height, skewed.width))
    noisy = Image.fromarray(np.clip(np.asarray(skewed, dtype=np.float32) + noise, 0, 255).astype(np.uint8))
    buffer = io.BytesIO()
    noisy.save(buffer, "JPEG", quality=_JPEG_QUALITY)
    buffer.seek(0)
    return Image.open(buffer).convert("L")
