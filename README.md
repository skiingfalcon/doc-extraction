# Document extraction on DGX Spark

This project turns fictional investment-memo PDFs into layout-aware markdown with [NVIDIA Nemotron Parse 2.0](https://huggingface.co/nvidia/NVIDIA-Nemotron-Parse-2.0), then scores that result against Docling.

DGX Spark is an aarch64 machine with a GB10 GPU. The Nemotron Parse NIM container does not run on GB10, so inference uses Transformers in bfloat16 against a snapshot stored on the local disk. Download the weights as your own user, not from a root container, so the model directory stays readable.

## Setup

```bash
uv sync
uv run doc-extract download
uv run doc-extract synthesize
uv run doc-extract parse data/memos
uv run doc-extract compare data/memos
```

`download` writes `models/NVIDIA-Nemotron-Parse-2.0`, including the postprocessing helpers, and skips the unused auxiliary prediction head. A Hugging Face token is optional because the repository is public. Xet downloads use `HF_XET_HIGH_PERFORMANCE=1`.

PyTorch comes from the CUDA 13 wheel index so it matches this machine's driver. The parser rasterizes each page with pypdfium2 and scales it to fit inside the model's 1664×2048 window.

## Comparison

`compare` scores two extractors against the JSON sidecar written next to each memo:

- `nemotron_parse` reads the markdown produced by `parse`, and runs that step first when the markdown is missing.
- `docling` exports markdown from Docling's document converter.

`outputs/comparison.md` lists runtime plus heading, table-cell, and footnote hits. Hits mean the ground-truth string appears in the extractor output after case, whitespace, and markdown emphasis markers are normalized.

The memos, issuers, and figures are fictional and are not an offer to sell securities.
