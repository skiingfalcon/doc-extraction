"""Download Nemotron Parse 2.0 onto the Spark's local disk."""

import os
from pathlib import Path

from doc_extraction.paths import MODEL_DIR, MODEL_ID, MODEL_REVISION

# Training-only auxiliary heads; neither Transformers nor vLLM inference loads them.
_SKIP = ["auxiliary_prediction_heads.safetensors.extra"]


def download_model(dest: Path = MODEL_DIR, revision: str = MODEL_REVISION) -> Path:
    """Snapshot the public Parse 2.0 repo at a pinned revision as the host user.

    ``local_dir`` keeps a plain folder of weights and the postprocessing
    modules, so later inference can load them with ``local_files_only``.
    """
    os.environ.setdefault("HF_XET_HIGH_PERFORMANCE", "1")
    from huggingface_hub import snapshot_download

    dest.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=MODEL_ID,
        revision=revision,
        local_dir=str(dest),
        ignore_patterns=_SKIP,
    )
    return dest
