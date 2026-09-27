"""Score Nemotron Parse and Docling against memo sidecars."""

import json
import time
from pathlib import Path

from doc_extraction.baselines import extract_docling, make_docling_converter
from doc_extraction.paths import MODEL_DIR, OUTPUT_DIR
from doc_extraction.parse import parse_pdfs


def compare(
    pdf_paths: list[Path],
    model_dir: Path = MODEL_DIR,
    output_dir: Path = OUTPUT_DIR,
) -> Path:
    """Write ``comparison.json`` and ``comparison.md`` for the given memos."""
    output_dir.mkdir(parents=True, exist_ok=True)
    missing = [path for path in pdf_paths if not _nemotron_markdown(output_dir, path).is_file()]
    if missing:
        parse_pdfs(missing, model_dir=model_dir, output_dir=output_dir)

    converter_holder: dict = {}
    reports = [_score_memo(pdf_path, output_dir, converter_holder) for pdf_path in pdf_paths]
    payload = {"memos": reports}
    json_path = output_dir / "comparison.json"
    md_path = output_dir / "comparison.md"
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(_render_report(reports), encoding="utf-8")
    return md_path


def _score_memo(pdf_path: Path, output_dir: Path, converter_holder: dict) -> dict:
    truth = json.loads(pdf_path.with_suffix(".truth.json").read_text(encoding="utf-8"))
    nemotron_md = _nemotron_markdown(output_dir, pdf_path).read_text(encoding="utf-8")
    timing_path = output_dir / pdf_path.stem / "timing.json"
    nemotron_seconds = json.loads(timing_path.read_text(encoding="utf-8"))["seconds"]
    extractors = {
        "nemotron_parse": _hit_record(nemotron_md, truth, seconds=nemotron_seconds),
    }

    def _docling() -> str:
        if "converter" not in converter_holder:
            converter_holder["converter"] = make_docling_converter()
        return extract_docling(pdf_path, converter_holder["converter"])

    extractors["docling"] = _timed_extract(_docling, truth)
    return {"pdf": pdf_path.name, "extractors": extractors}


def _timed_extract(fn, truth: dict) -> dict:
    started = time.perf_counter()
    markdown = fn()
    elapsed = round(time.perf_counter() - started, 3)
    return _hit_record(markdown, truth, seconds=elapsed)


def _hit_record(markdown: str, truth: dict, seconds: float) -> dict:
    return {
        "seconds": seconds,
        "headings": _containment(markdown, truth["headings"]),
        "table_cells": _containment(markdown, truth["table_cells"]),
        "footnotes": _containment(markdown, truth["footnotes"]),
    }


def _containment(markdown: str, expected: list[str]) -> dict:
    haystack = _normalize(markdown)
    hits = [item for item in expected if _normalize(item) in haystack]
    misses = [item for item in expected if item not in hits]
    return {"found": len(hits), "expected": len(expected), "misses": misses}


def _normalize(text: str) -> str:
    """Casefold, drop markdown emphasis, and collapse whitespace."""
    plain = text.replace("*", "").replace("_", "")
    return " ".join(plain.casefold().split())


def _nemotron_markdown(output_dir: Path, pdf_path: Path) -> Path:
    return output_dir / pdf_path.stem / "document.md"


def _render_report(reports: list[dict]) -> str:
    lines = [
        "# Extraction comparison",
        "",
        "Hits are string containment after case, whitespace, and markdown emphasis are normalized.",
        "",
        "| Memo | Extractor | Seconds | Headings | Table cells | Footnotes |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for report in reports:
        for name, result in report["extractors"].items():
            lines.append(
                "| {pdf} | {name} | {seconds} | {headings} | {cells} | {footnotes} |".format(
                    pdf=report["pdf"],
                    name=name,
                    seconds=result["seconds"],
                    headings=_ratio(result["headings"]),
                    cells=_ratio(result["table_cells"]),
                    footnotes=_ratio(result["footnotes"]),
                )
            )
    lines.append("")
    return "\n".join(lines)


def _ratio(score: dict) -> str:
    return f"{score['found']}/{score['expected']}"
