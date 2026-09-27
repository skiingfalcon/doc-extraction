"""Run Nemotron Parse 2.0 on rendered memo pages."""

import importlib
import json
import re
import sys
import time
from pathlib import Path

from doc_extraction.paths import MODEL_DIR, OUTPUT_DIR, TASK_PROMPT
from doc_extraction.render import render_pdf


def parse_pdfs(pdf_paths: list[Path], model_dir: Path = MODEL_DIR, output_dir: Path = OUTPUT_DIR) -> list[Path]:
    """Load the local snapshot once and write markdown plus per-page JSON."""
    if not model_dir.is_dir():
        raise FileNotFoundError(
            f"Model directory {model_dir} is missing. Run `doc-extract download` first."
        )
    engine = _load_engine(model_dir)
    written: list[Path] = []
    try:
        for pdf_path in pdf_paths:
            written.append(_parse_one(engine, pdf_path, output_dir))
    finally:
        engine.close()
    return written


def _parse_one(engine: "_ParseEngine", pdf_path: Path, output_dir: Path) -> Path:
    memo_dir = output_dir / pdf_path.stem
    memo_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    pages_md: list[str] = []
    images = render_pdf(pdf_path)
    for index, image in enumerate(images, start=1):
        print(f"parsing {pdf_path.name} page {index}/{len(images)} ({image.width}x{image.height})", flush=True)
        page = engine.parse_image(image)
        page["page"] = index
        (memo_dir / f"page-{index}.json").write_text(
            json.dumps(page, indent=2) + "\n",
            encoding="utf-8",
        )
        pages_md.append(f"## Page {index}\n\n{page['markdown'].strip()}".rstrip())
    elapsed = time.perf_counter() - started
    document_md = memo_dir / "document.md"
    document_md.write_text("\n\n".join(pages_md).strip() + "\n", encoding="utf-8")
    (memo_dir / "timing.json").write_text(
        json.dumps({"seconds": round(elapsed, 3)}) + "\n",
        encoding="utf-8",
    )
    return document_md


class _ParseEngine:
    def __init__(self, model, processor, generation_config, postprocessing, device: str) -> None:
        self.model = model
        self.processor = processor
        self.generation_config = generation_config
        self.postprocessing = postprocessing
        self.device = device

    def parse_image(self, image) -> dict:
        import torch

        inputs = self.processor(
            images=[image],
            text=TASK_PROMPT,
            return_tensors="pt",
            add_special_tokens=False,
        ).to(self.device)
        with torch.inference_mode():
            outputs = self.model.generate(**inputs, generation_config=self.generation_config)
        generated = _best_decode(self.processor, outputs)
        classes, boxes, texts = _extract_blocks(self.postprocessing, generated)
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
        return {"width": image.width, "height": image.height, "elements": elements, "markdown": markdown}

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
    location = str(model_dir)
    if location not in sys.path:
        sys.path.insert(0, location)
    sys.modules.pop("postprocessing", None)
    sys.modules.pop("latex2html", None)
    return importlib.import_module("postprocessing")


def _extract_blocks(postprocessing, generated: str):
    """Use the snapshot parser, dropping page-number blocks that it rejects."""
    try:
        return postprocessing.extract_classes_bboxes(generated)
    except AssertionError:
        cleaned = re.sub(
            r"<x_\d+(?:\.\d+)?><y_\d+(?:\.\d+)?>.*?<class_Page-number>",
            "",
            generated,
            flags=re.DOTALL,
        )
        return postprocessing.extract_classes_bboxes(cleaned)


def _best_decode(processor, outputs) -> str:
    """Prefer the decode that still contains layout tags the postprocessor reads."""
    skipped = processor.batch_decode(outputs, skip_special_tokens=True)[0]
    kept = processor.batch_decode(outputs, skip_special_tokens=False)[0]
    if skipped.count("<class_") >= kept.count("<class_") and "<class_" in skipped:
        return skipped
    if "<class_" in kept or "<x_" in kept:
        return kept
    return skipped
