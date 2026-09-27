"""CPU-only tests that the memo PDFs regenerate identically and the scanned ones are image-only."""

import pypdfium2 as pdfium
import pytest

from doc_extraction.paths import MAX_HEIGHT, MAX_WIDTH, MEMO_DIR
from doc_extraction.render import render_pdf
from doc_extraction.synthesize import synthesize


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    first = tmp_path_factory.mktemp("first")
    second = tmp_path_factory.mktemp("second")
    synthesize(first)
    synthesize(second)
    return first, second


def test_regeneration_is_byte_identical(generated):
    first, second = generated
    files = sorted(path.relative_to(first) for path in first.rglob("*") if path.is_file())
    assert files, "synthesize wrote nothing"
    for relative in files:
        assert (first / relative).read_bytes() == (second / relative).read_bytes(), relative


def test_committed_memos_match_the_generator(generated):
    first, _ = generated
    for path in first.rglob("*"):
        if path.is_file():
            committed = MEMO_DIR / path.relative_to(first)
            assert committed.read_bytes() == path.read_bytes(), f"re-run `doc-extract synthesize`: {committed}"


def test_scanned_pdfs_have_no_text_layer_and_same_page_count(generated):
    first, _ = generated
    for scanned_path in sorted((first / "scanned").glob("*.pdf")):
        scanned = pdfium.PdfDocument(str(scanned_path))
        digital = pdfium.PdfDocument(str(first / "digital" / scanned_path.name))
        try:
            assert len(scanned) == len(digital)
            for index in range(len(scanned)):
                assert scanned[index].get_textpage().get_text_range().strip() == ""
            assert digital[0].get_textpage().get_text_range().strip() != ""
        finally:
            scanned.close()
            digital.close()


def test_render_fits_the_model_window():
    for image in render_pdf(MEMO_DIR / "digital" / "lakefront.pdf"):
        assert image.width <= MAX_WIDTH and image.height <= MAX_HEIGHT
        assert image.width == MAX_WIDTH or image.height == MAX_HEIGHT
