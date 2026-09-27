"""Run evaluate() end to end with a stub Docling converter, so no models are downloaded."""

import json
import types
from pathlib import Path

from doc_extraction import evaluate as evaluate_module
from doc_extraction.paths import MEMO_DIR

PDFS = sorted(MEMO_DIR.rglob("*.pdf"))


class StubDocument:
    def __init__(self, markdown):
        self.markdown = markdown

    def export_to_markdown(self):
        return self.markdown

    def export_to_dict(self):
        return {"markdown": self.markdown}


class StubConverter:
    """Returns each memo's reference markdown with its first table row removed."""

    def convert(self, source):
        reference = Path(source).with_suffix(".reference.md").read_text(encoding="utf-8")
        lines = reference.splitlines()
        first_row = next(i for i, line in enumerate(lines) if line.startswith("| ") and "---" in lines[i - 1])
        del lines[first_row]
        return types.SimpleNamespace(document=StubDocument("\n".join(lines)))


def test_docling_report_is_written_per_variant(tmp_path, monkeypatch):
    monkeypatch.setattr(evaluate_module, "make_docling_converter", lambda force_ocr=False: StubConverter())
    report = evaluate_module.evaluate("docling", PDFS, output_dir=tmp_path)

    assert report == tmp_path / "docling" / "report.md"
    text = report.read_text(encoding="utf-8")
    assert "## digital" in text and "## scanned" in text
    assert "table row missing:" in text
    assert "nemotron" not in text.casefold()

    payload = json.loads((tmp_path / "docling" / "report.json").read_text(encoding="utf-8"))
    assert len(payload["memos"]) == len(PDFS)
    for memo in payload["memos"]:
        rows = memo["scores"]["tables"]["rows"]
        assert rows["found"] == rows["expected"] - 1
        assert (tmp_path / "docling" / memo["variant"] / memo["pdf"].removesuffix(".pdf") / "document.md").is_file()
