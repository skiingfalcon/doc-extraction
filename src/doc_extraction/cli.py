"""Command line entry points for download, synthesis, parse, and evaluate."""

import argparse
from pathlib import Path

from doc_extraction.paths import MEMO_DIR, MODEL_DIR


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="doc-extract")
    sub = parser.add_subparsers(dest="command", required=True)

    download = sub.add_parser("download", help="snapshot Nemotron Parse 2.0 onto local disk")
    download.add_argument("--dest", type=Path, default=MODEL_DIR)

    synthesize_cmd = sub.add_parser("synthesize", help="write fictional digital and scanned memo PDFs")
    synthesize_cmd.add_argument("--dest", type=Path, default=MEMO_DIR)
    synthesize_cmd.add_argument("--no-scanned", action="store_true", help="skip the image-only variant")

    parse = sub.add_parser("parse", help="extract layout markdown with Nemotron Parse")
    parse.add_argument("path", type=Path, help="PDF file or directory of PDFs (searched recursively)")
    parse.add_argument("--model", type=Path, default=MODEL_DIR)
    parse.add_argument("--batch-size", type=int, default=4)

    evaluate_cmd = sub.add_parser("evaluate", help="score one extractor and write its own report")
    evaluate_cmd.add_argument("path", type=Path, help="PDF file or directory of PDFs (searched recursively)")
    evaluate_cmd.add_argument("--extractor", choices=["nemotron", "docling", "all"], default="all")
    evaluate_cmd.add_argument("--docling-force-ocr", action="store_true", help="OCR every page with Docling")
    evaluate_cmd.add_argument("--model", type=Path, default=MODEL_DIR)
    evaluate_cmd.add_argument("--batch-size", type=int, default=4)

    args = parser.parse_args(argv)
    # Imports are deferred so `evaluate --extractor docling` never loads torch.
    if args.command == "download":
        from doc_extraction.download import download_model

        print(download_model(args.dest))
    elif args.command == "synthesize":
        from doc_extraction.synthesize import synthesize

        for path in synthesize(args.dest, scanned=not args.no_scanned):
            print(path)
    elif args.command == "parse":
        from doc_extraction.parse import parse_pdfs

        for path in parse_pdfs(_pdfs(args.path), model_dir=args.model, batch_size=args.batch_size):
            print(path)
    elif args.command == "evaluate":
        from doc_extraction.evaluate import EXTRACTORS, evaluate

        extractors = EXTRACTORS if args.extractor == "all" else [args.extractor]
        for extractor in extractors:
            print(evaluate(
                extractor,
                _pdfs(args.path),
                model_dir=args.model,
                batch_size=args.batch_size,
                docling_force_ocr=args.docling_force_ocr,
            ))


def _pdfs(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise SystemExit(f"Path not found: {path}")
    found = sorted(path.rglob("*.pdf"))
    if not found:
        raise SystemExit(f"No PDFs in {path}")
    return found


if __name__ == "__main__":
    main()
