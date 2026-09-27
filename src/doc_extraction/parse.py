"""Run Nemotron Parse 2.0 on rendered memo pages."""

import importlib.util
import json
import re
import sys
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from doc_extraction.paths import MODEL_DIR, MODEL_REVISION, OUTPUT_DIR, TASK_PROMPT
from doc_extraction.render import render_pdf

NEMOTRON_OUTPUT_DIR = OUTPUT_DIR / "nemotron"

# One layout block: start coordinates, text without another class tag, end coordinates, class.
_PAGE_NUMBER_BLOCK = re.compile(
    r"<x_[\d.]+><y_[\d.]+>(?:(?!<class_).)*?<x_[\d.]+><y_[\d.]+><class_Page-number>",
    re.DOTALL,
)


def memo_dir(output_dir: Path, pdf_path: Path) -> Path:
    """``<output_dir>/<variant>/<slug>``, where the variant is the PDF's folder name."""
    return output_dir / pdf_path.parent.name / pdf_path.stem


def parse_pdfs(
    pdf_paths: list[Path],
    model_dir: Path = MODEL_DIR,
    output_dir: Path = NEMOTRON_OUTPUT_DIR,
    batch_size: int = 4,
) -> list[Path]:
    """Load the local snapshot once and write markdown plus per-page JSON.

    Pages from every PDF share one queue, so a batch can span documents. A
    single background thread renders the next PDF while the GPU generates;
    pdfium is not thread-safe, so every render stays on that thread.
    """
    if not model_dir.is_dir():
        raise FileNotFoundError(
            f"Model directory {model_dir} is missing. Run `doc-extract download` first."
        )
    load_started = time.perf_counter()
    engine = _load_engine(model_dir)
    load_seconds = round(time.perf_counter() - load_started, 3)

    batches: list[dict] = []
    written: list[Path] = []
    batch: list[tuple[_Document, int, object]] = []

    def flush() -> None:
        if batch:
            batches.append(_run_batch(engine, batch))
            written.extend(doc.finish() for doc, _, _ in batch if doc.complete and not doc.finished)
            batch.clear()

    try:
        with ThreadPoolExecutor(max_workers=1) as renderer:
            queue = deque((path, renderer.submit(render_pdf, path)) for path in pdf_paths[:2])
            remaining = iter(pdf_paths[2:])
            while queue:
                pdf_path, rendered = queue.popleft()
                upcoming = next(remaining, None)
                if upcoming is not None:
                    queue.append((upcoming, renderer.submit(render_pdf, upcoming)))
                try:
                    images = rendered.result()
                except Exception as error:  # noqa: BLE001 - one unreadable PDF should not stop the run
                    print(f"warning: could not render {pdf_path}: {error}", flush=True)
                    continue
                doc = _Document(pdf_path, memo_dir(output_dir, pdf_path), len(images))
                if not images:
                    written.append(doc.finish())
                for index, image in enumerate(images, start=1):
                    batch.append((doc, index, image))
                    if len(batch) == batch_size:
                        flush()
            flush()
    finally:
        engine.close()

    _write_run(output_dir, pdf_paths, batch_size, load_seconds, batches)
    return written


class _Document:
    """Collects one PDF's pages and writes ``document.md`` once all have arrived."""

    def __init__(self, pdf_path: Path, directory: Path, page_count: int) -> None:
        self.pdf_path = pdf_path
        self.directory = directory
        self.page_count = page_count
        self.pages: dict[int, dict] = {}
        self.finished = False
        directory.mkdir(parents=True, exist_ok=True)

    @property
    def complete(self) -> bool:
        return len(self.pages) == self.page_count

    def add(self, index: int, page: dict) -> None:
        page["page"] = index
        self.pages[index] = page
        (self.directory / f"page-{index}.json").write_text(
            json.dumps(page, indent=2) + "\n",
            encoding="utf-8",
        )

    def finish(self) -> Path:
        parts = []
        for index in range(1, self.page_count + 1):
            page = self.pages[index]
            if "error" in page:
                parts.append(f"<!-- page {index} failed -->")
            else:
                parts.append(f"<!-- page {index} -->\n\n{page['markdown'].strip()}".rstrip())
        document_md = self.directory / "document.md"
        document_md.write_text("\n\n".join(parts).strip() + "\n", encoding="utf-8")
        summary = {
            "pdf": self.pdf_path.name,
            "pages": self.page_count,
            "seconds": round(sum(page["seconds"] for page in self.pages.values()), 3),
            "failed_pages": [i for i, page in sorted(self.pages.items()) if "error" in page],
            "truncated_pages": [i for i, page in sorted(self.pages.items()) if page.get("truncated")],
        }
        (self.directory / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        self.finished = True
        return document_md


def _run_batch(engine: "_ParseEngine", batch: list) -> dict:
    """Generate one batch; if the batch call itself fails, retry page by page."""
    images = [image for _, _, image in batch]
    for doc, index, image in batch:
        print(f"parsing {doc.pdf_path.name} page {index}/{doc.page_count} ({image.width}x{image.height})", flush=True)
    started = time.perf_counter()
    try:
        pages = engine.parse_images(images)
    except Exception as error:  # noqa: BLE001 - a failed batch should not lose every page
        print(f"batch of {len(images)} failed ({error}); retrying pages one at a time", flush=True)
        pages = []
        for image in images:
            try:
                pages.extend(engine.parse_images([image]))
            except Exception as page_error:  # noqa: BLE001
                pages.append({"error": f"{type(page_error).__name__}: {page_error}"})
    seconds = time.perf_counter() - started
    share = round(seconds / len(batch), 3)
    for (doc, index, _), page in zip(batch, pages):
        page.update(seconds=share, batch_seconds=round(seconds, 3), batch_size=len(batch))
        if page.get("truncated"):
            print(f"warning: {doc.pdf_path.name} page {index} hit max_new_tokens; output is cut off", flush=True)
        if "error" in page:
            print(f"warning: {doc.pdf_path.name} page {index} failed: {page['error']}", flush=True)
        doc.add(index, page)
    return {
        "pages": len(batch),
        "seconds": round(seconds, 3),
        "generated_tokens": sum(page.get("generated_tokens", 0) for page in pages),
    }


def _write_run(output_dir: Path, pdf_paths: list[Path], batch_size: int, load_seconds: float, batches: list[dict]) -> None:
    pages = sum(batch["pages"] for batch in batches)
    seconds = sum(batch["seconds"] for batch in batches)
    record = {
        "model_revision": MODEL_REVISION,
        "batch_size": batch_size,
        "load_seconds": load_seconds,
        "generate_seconds": round(seconds, 3),
        "pages": pages,
        "pages_per_second": round(pages / seconds, 3) if seconds else None,
        "generated_tokens": sum(batch["generated_tokens"] for batch in batches),
        "pdfs": [str(path) for path in pdf_paths],
        "batches": batches,
    }
    for variant in sorted({path.parent.name for path in pdf_paths}):
        (output_dir / variant).mkdir(parents=True, exist_ok=True)
        (output_dir / variant / "run.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


class _ParseEngine:
    def __init__(self, model, processor, generation_config, postprocessing, device: str) -> None:
        self.model = model
        self.processor = processor
        self.generation_config = generation_config
        self.postprocessing = postprocessing
        self.device = device

    def parse_images(self, images: list) -> list[dict]:
        """Generate for a batch of page images; postprocessing errors stay per page."""
        import torch

        inputs = self.processor(
            images=list(images),
            text=[TASK_PROMPT] * len(images),
            return_tensors="pt",
            add_special_tokens=False,
        )
        # The encoder casts to bfloat16 anyway; casting first halves the host-to-GPU copy.
        inputs["pixel_values"] = inputs["pixel_values"].to(torch.bfloat16)
        inputs = inputs.to(self.device)
        prompt_length = inputs["input_ids"].shape[1]
        with torch.inference_mode():
            outputs = self.model.generate(**inputs, generation_config=self.generation_config)

        pages = []
        for row, image in zip(outputs, images):
            new_tokens = _new_token_count(row[prompt_length:].tolist(), self.generation_config.pad_token_id)
            last_token = row[prompt_length + new_tokens - 1].item() if new_tokens else None
            truncated = _is_truncated(
                new_tokens,
                self.generation_config.max_new_tokens,
                last_token,
                self.generation_config.eos_token_id,
            )
            try:
                page = self._postprocess(row.unsqueeze(0), image)
            except Exception as error:  # noqa: BLE001 - record the page and keep going
                page = {"error": f"{type(error).__name__}: {error}"}
            page.update(generated_tokens=new_tokens, truncated=truncated)
            pages.append(page)
        return pages

    def _postprocess(self, output, image) -> dict:
        generated = _best_decode(self.processor, output)
        classes, boxes, texts, dropped = _extract_blocks(self.postprocessing, generated)
        boxes = [
            list(self.postprocessing.transform_bbox_to_original(box, image.width, image.height))
            for box in boxes
        ]
        rendered = [
            self.postprocessing.postprocess_text(
                text,
                cls=cls,
                table_format="markdown",
                text_format="markdown",
                blank_text_in_figures=False,
            )
            for text, cls in zip(texts, classes)
        ]
        elements = [
            {"class": cls, "bbox": box, "text": text}
            for cls, box, text in zip(classes, boxes, rendered)
        ]
        markdown = "\n\n".join(text.strip() for text in rendered if text and text.strip())
        return {
            "width": image.width,
            "height": image.height,
            "elements": elements,
            "markdown": markdown,
            "dropped_page_number": dropped,
        }

    def close(self) -> None:
        import torch

        del self.model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


def _load_engine(model_dir: Path) -> _ParseEngine:
    import torch
    from transformers import AutoModel, AutoProcessor, GenerationConfig

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required. Nemotron Parse runs on the DGX Spark GPU.")
    device = "cuda:0"
    model_path = str(model_dir)
    model = AutoModel.from_pretrained(
        model_path,
        trust_remote_code=True,
        dtype=torch.bfloat16,
        local_files_only=True,
    ).to(device).eval()
    processor = AutoProcessor.from_pretrained(
        model_path,
        trust_remote_code=True,
        local_files_only=True,
    )
    generation_config = GenerationConfig.from_pretrained(
        model_path,
        trust_remote_code=True,
        local_files_only=True,
    )
    if generation_config.max_new_tokens is None and generation_config.max_length is None:
        generation_config.max_new_tokens = 4096
    postprocessing = _load_postprocessing(model_dir)
    return _ParseEngine(model, processor, generation_config, postprocessing, device)


def _load_postprocessing(model_dir: Path):
    """Import the snapshot's postprocessing.py under a private module name.

    It imports ``latex2html`` from the same folder, so the folder is on
    ``sys.path`` only while the module executes.
    """
    spec = importlib.util.spec_from_file_location("_nemotron_postprocessing", model_dir / "postprocessing.py")
    module = importlib.util.module_from_spec(spec)
    location = str(model_dir)
    sys.path.insert(0, location)
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(location)
    return module


def _extract_blocks(postprocessing, generated: str):
    """Use the snapshot parser, dropping page-number blocks that it rejects.

    Returns ``(classes, boxes, texts, dropped_page_number)``.
    """
    try:
        return (*postprocessing.extract_classes_bboxes(generated), False)
    except AssertionError:
        cleaned = _PAGE_NUMBER_BLOCK.sub("", generated)
        if cleaned == generated:
            raise
        try:
            return (*postprocessing.extract_classes_bboxes(cleaned), True)
        except AssertionError as error:
            raise ValueError(
                f"postprocessing rejected the page after removing page numbers: {generated[:500]!r}"
            ) from error


def _new_token_count(tokens: list[int], pad_token_id: int | None) -> int:
    """Generated tokens before the right padding that finished rows get in a batch."""
    count = len(tokens)
    while count and tokens[count - 1] == pad_token_id:
        count -= 1
    return count


def _is_truncated(new_token_count: int, max_new_tokens: int | None, last_token_id: int | None, eos_id) -> bool:
    """True when generation used its whole budget without emitting end-of-sequence."""
    eos_ids = set(eos_id) if isinstance(eos_id, (list, tuple)) else {eos_id}
    if last_token_id in eos_ids:
        return False
    return max_new_tokens is not None and new_token_count >= max_new_tokens


def _best_decode(processor, outputs) -> str:
    """Prefer the decode that still contains layout tags the postprocessor reads."""
    skipped = processor.batch_decode(outputs, skip_special_tokens=True)[0]
    kept = processor.batch_decode(outputs, skip_special_tokens=False)[0]
    if skipped.count("<class_") >= kept.count("<class_") and "<class_" in skipped:
        return skipped
    if "<class_" in kept or "<x_" in kept:
        return kept
    return skipped
