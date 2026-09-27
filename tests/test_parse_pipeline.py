"""Drive parse_pdfs end to end on CPU with a fake engine in place of the model."""

import json

import pytest

from doc_extraction import parse
from doc_extraction.paths import MEMO_DIR

PDFS = sorted((MEMO_DIR / "digital").glob("*.pdf"))


class FakeEngine:
    def __init__(self, fail_batches_larger_than=None, failing_calls=()):
        self.batch_sizes = []
        self.fail_batches_larger_than = fail_batches_larger_than
        self.failing_calls = set(failing_calls)
        self.closed = False

    def parse_images(self, images):
        self.batch_sizes.append(len(images))
        if self.fail_batches_larger_than and len(images) > self.fail_batches_larger_than:
            raise RuntimeError("out of memory")
        if len(self.batch_sizes) in self.failing_calls:
            raise RuntimeError("bad page")
        return [
            {"markdown": f"# Page {image.width}x{image.height}", "generated_tokens": 10, "truncated": False}
            for image in images
        ]

    def close(self):
        self.closed = True


@pytest.fixture
def run(tmp_path, monkeypatch):
    model_dir = tmp_path / "model"
    model_dir.mkdir()

    def _run(engine, batch_size):
        monkeypatch.setattr(parse, "_load_engine", lambda _dir: engine)
        written = parse.parse_pdfs(PDFS, model_dir=model_dir, output_dir=tmp_path / "out", batch_size=batch_size)
        return written, tmp_path / "out"

    return _run


def test_batches_span_documents_and_every_document_is_written(run):
    engine = FakeEngine()
    written, out = run(engine, batch_size=4)
    # Three 2-page memos in batches of four: 4 + 2.
    assert engine.batch_sizes == [4, 2]
    assert engine.closed
    assert sorted(path.parent.name for path in written) == sorted(path.stem for path in PDFS)
    for pdf in PDFS:
        directory = out / "digital" / pdf.stem
        document = (directory / "document.md").read_text(encoding="utf-8")
        assert "<!-- page 1 -->" in document and "<!-- page 2 -->" in document
        assert "## Page" not in document
        summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
        assert summary["pages"] == 2 and summary["failed_pages"] == []
    run_record = json.loads((out / "digital" / "run.json").read_text(encoding="utf-8"))
    assert run_record["pages"] == 6 and run_record["batch_size"] == 4


def test_failed_batch_is_retried_page_by_page(run):
    engine = FakeEngine(fail_batches_larger_than=1)
    written, _out = run(engine, batch_size=4)
    assert engine.batch_sizes == [4, 1, 1, 1, 1, 2, 1, 1]
    assert len(written) == 3


def test_a_page_that_keeps_failing_is_recorded_and_the_run_continues(run):
    # Batch size 1: call 3 fails, and so does its one-page retry (call 4).
    engine = FakeEngine(failing_calls={3, 4})
    written, out = run(engine, batch_size=1)
    assert len(written) == 3
    failed = []
    for pdf in PDFS:
        summary = json.loads((out / "digital" / pdf.stem / "summary.json").read_text(encoding="utf-8"))
        failed += [(pdf.stem, page) for page in summary["failed_pages"]]
    assert len(failed) == 1
    stem, page = failed[0]
    page_json = json.loads((out / "digital" / stem / f"page-{page}.json").read_text(encoding="utf-8"))
    assert "error" in page_json
    assert f"<!-- page {page} failed -->" in (out / "digital" / stem / "document.md").read_text(encoding="utf-8")
