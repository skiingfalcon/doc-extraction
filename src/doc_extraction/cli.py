"""Command line entry points for download, synthesis, parse, and compare."""

import argparse
from pathlib import Path

from doc_extraction.compare import compare
from doc_extraction.download import download_model
from doc_extraction.parse import parse_pdfs
from doc_extraction.paths import MEMO_DIR, MODEL_DIR
from doc_extraction.synthesize import synthesize


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="doc-extract")
    sub = parser.add_subparsers(dest="command", required=True)

    download = sub.add_parser("download", help="snapshot Nemotron Parse 2.0 onto local disk")
    download.add_argument("--dest", type=Path, default=MODEL_DIR)

    synthesize_cmd = sub.add_parser("synthesize", help="write fictional investment-memo PDFs")
    synthesize_cmd.add_argument("--dest", type=Path, default=MEMO_DIR)

    parse = sub.add_parser("parse", help="extract layout markdown with Nemotron Parse")
    parse.add_argument("path", type=Path, help="PDF file or directory of PDFs")
    parse.add_argument("--model", type=Path, default=MODEL_DIR)

    compare_cmd = sub.add_parser("compare", help="score Nemotron Parse and Docling")
    compare_cmd.add_argument("path", type=Path, help="PDF file or directory of PDFs")
    compare_cmd.add_argument("--model", type=Path, default=MODEL_DIR)

    args = parser.parse_args(argv)
    if args.command == "download":
        dest = download_model(args.dest)
        print(dest)
    elif args.command == "synthesize":
        for path in synthesize(args.dest):
            print(path)
    elif args.command == "parse":
        for path in parse_pdfs(_pdfs(args.path), model_dir=args.model):
            print(path)
    elif args.command == "compare":
        print(compare(_pdfs(args.path), model_dir=args.model))


def _pdfs(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise SystemExit(f"Path not found: {path}")
    found = sorted(path.glob("*.pdf"))
    if not found:
        raise SystemExit(f"No PDFs in {path}")
    return found


if __name__ == "__main__":
    main()
