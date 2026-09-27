"""Run one extractor over the memos and write its own report against the ground truth."""

import json
import time
from pathlib import Path

from doc_extraction.metrics import score
from doc_extraction.paths import MODEL_DIR, OUTPUT_DIR

EXTRACTORS = ("nemotron", "docling")
_TITLES = {
    "nemotron": "Nemotron Parse 2.0",
    "docling": "Docling",
    "docling-force-ocr": "Docling (full-page OCR forced)",
}


def evaluate(
    extractor: str,
    pdf_paths: list[Path],
    model_dir: Path = MODEL_DIR,
    output_dir: Path = OUTPUT_DIR,
    batch_size: int = 4,
    docling_force_ocr: bool = False,
) -> Path:
    """Extract (or reuse) markdown for each PDF, score it, and write ``report.md``/``report.json``."""
    if extractor == "nemotron":
        name = "nemotron"
        runs, meta = _nemotron_outputs(pdf_paths, model_dir, output_dir / name, batch_size)
    elif extractor == "docling":
        name = "docling-force-ocr" if docling_force_ocr else "docling"
        runs, meta = _docling_outputs(pdf_paths, output_dir / name, docling_force_ocr)
    else:
        raise ValueError(f"Unknown extractor {extractor!r}; expected one of {EXTRACTORS}")

    memos = [_score_memo(run) for run in runs]
    root = output_dir / name
    root.mkdir(parents=True, exist_ok=True)
    payload = {"extractor": name, "meta": meta, "memos": memos}
    (root / "report.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    report = root / "report.md"
    report.write_text(_render_report(name, meta, memos), encoding="utf-8")
    return report


def _nemotron_outputs(pdf_paths: list[Path], model_dir: Path, root: Path, batch_size: int):
    from doc_extraction.parse import memo_dir, parse_pdfs

    missing = [path for path in pdf_paths if not (memo_dir(root, path) / "document.md").is_file()]
    if missing:
        parse_pdfs(missing, model_dir=model_dir, output_dir=root, batch_size=batch_size)

    runs = []
    for pdf_path in pdf_paths:
        directory = memo_dir(root, pdf_path)
        summary_path = directory / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.is_file() else {}
        runs.append({
            "pdf": pdf_path,
            "markdown": (directory / "document.md").read_text(encoding="utf-8"),
            "seconds": summary.get("seconds"),
            "notes": _page_notes(summary),
        })
    meta = {}
    for variant in sorted({path.parent.name for path in pdf_paths}):
        run_path = root / variant / "run.json"
        if run_path.is_file():
            run = json.loads(run_path.read_text(encoding="utf-8"))
            meta[variant] = {
                key: run.get(key)
                for key in ("model_revision", "batch_size", "load_seconds", "pages_per_second", "generated_tokens")
            }
    return runs, meta


def _page_notes(summary: dict) -> list[str]:
    notes = []
    if summary.get("failed_pages"):
        notes.append(f"failed pages: {summary['failed_pages']}")
    if summary.get("truncated_pages"):
        notes.append(f"truncated pages: {summary['truncated_pages']}")
    return notes


def _docling_outputs(pdf_paths: list[Path], root: Path, force_ocr: bool):
    started = time.perf_counter()
    converter = make_docling_converter(force_ocr=force_ocr)
    load_seconds = round(time.perf_counter() - started, 3)

    runs = []
    for pdf_path in pdf_paths:
        started = time.perf_counter()
        document = converter.convert(str(pdf_path)).document
        seconds = round(time.perf_counter() - started, 3)
        markdown = document.export_to_markdown()
        directory = root / pdf_path.parent.name / pdf_path.stem
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "document.md").write_text(markdown, encoding="utf-8")
        (directory / "document.json").write_text(
            json.dumps(document.export_to_dict(), indent=2) + "\n", encoding="utf-8"
        )
        runs.append({"pdf": pdf_path, "markdown": markdown, "seconds": seconds, "notes": []})
    meta = {
        "all": {
            "force_ocr": force_ocr,
            "load_seconds": load_seconds,
            "note": "The first document's seconds include Docling's lazy model loading.",
        }
    }
    return runs, meta


def make_docling_converter(force_ocr: bool = False):
    """Docling's default PDF converter, optionally OCRing every page in full."""
    from docling.document_converter import DocumentConverter

    if not force_ocr:
        return DocumentConverter()
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import (
        OcrAutoOptions,
        OcrMode,
        PdfPipelineOptions,
    )
    from docling.document_converter import PdfFormatOption

    options = PdfPipelineOptions(do_ocr=True, ocr_options=OcrAutoOptions(mode=OcrMode.FULL_PAGE))
    return DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)})


def _score_memo(run: dict) -> dict:
    pdf_path = run["pdf"]
    truth = json.loads(pdf_path.with_suffix(".truth.json").read_text(encoding="utf-8"))
    reference = pdf_path.with_name(f"{pdf_path.stem}.reference.md").read_text(encoding="utf-8")
    return {
        "pdf": pdf_path.name,
        "variant": pdf_path.parent.name,
        "seconds": run["seconds"],
        "notes": run["notes"],
        "scores": score(run["markdown"], truth, reference),
    }


def _render_report(name: str, meta: dict, memos: list[dict]) -> str:
    lines = [
        f"# {_TITLES.get(name, name)}: extraction report",
        "",
        (
            "Each memo is scored against its `.truth.json` and `.reference.md`. "
            "The README explains what each metric catches and misses."
        ),
        "",
        "## Run",
        "",
    ]
    for scope, values in meta.items():
        details = ", ".join(f"{key}: {value}" for key, value in values.items())
        lines.append(f"- **{scope}**: {details}")
    if not meta:
        lines.append("- no run metadata recorded")

    for variant in sorted({memo["variant"] for memo in memos}):
        lines += [
            "",
            f"## {variant}",
            "",
            (
                "| Memo | Headings (as heading / right level) | Table header | Rows | Cells in tables "
                "| Text similarity | Bullets | Chart labels | Chart values | Furniture kept | Seconds |"
            ),
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |",
        ]
        variant_memos = [memo for memo in memos if memo["variant"] == variant]
        for memo in variant_memos:
            s = memo["scores"]
            headings = s["headings"]
            tables = s["tables"]
            kept = sum(s["page_furniture"].values())
            lines.append(
                f"| {memo['pdf']} "
                f"| {headings['as_heading']}/{headings['expected']} · {headings['right_level']}/{headings['expected']} "
                f"| {_ratio(tables['headers'])} | {_ratio(tables['rows'])} | {_ratio(tables['cells_in_tables'])} "
                f"| {s['text_similarity']:.3f} | {_ratio(s['bullets'])} "
                f"| {_ratio(s['chart']['labels'])} | {_ratio(s['chart']['values'])} "
                f"| {kept}/{len(s['page_furniture'])} | {memo['seconds'] if memo['seconds'] is not None else '–'} |"
            )
        for memo in variant_memos:
            details = _misses(memo)
            if details:
                lines += ["", f"<details><summary>{memo['pdf']}: misses and notes</summary>", ""]
                lines += [f"- {item}" for item in details]
                lines += ["", "</details>"]
    lines.append("")
    return "\n".join(lines)


def _misses(memo: dict) -> list[str]:
    s = memo["scores"]
    items = list(memo["notes"])
    items += [f"heading missing: {text}" for text in s["headings"]["misses"]]
    items += [f"heading level: {text}" for text in s["headings"]["wrong_level"]]
    items += [f"table row missing: {row}" for row in s["tables"]["rows"]["misses"]]
    items += [f"bullet missing: {text}" for text in s["bullets"]["misses"]]
    items += [f"chart label missing: {text}" for text in s["chart"]["labels"]["misses"]]
    items += [f"chart value missing: {text}" for text in s["chart"]["values"]["misses"]]
    items += [f"furniture dropped: {text}" for text, kept in s["page_furniture"].items() if not kept]
    return items


def _ratio(result: dict) -> str:
    return f"{result['found']}/{result['expected']}"
