"""Locations and model constants for the Spark extraction project."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_ID = "nvidia/NVIDIA-Nemotron-Parse-2.0"
MODEL_DIR = PROJECT_ROOT / "models" / "NVIDIA-Nemotron-Parse-2.0"
MEMO_DIR = PROJECT_ROOT / "data" / "memos"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

# Nemotron Parse 2.0 recommended input window (width, height).
MAX_WIDTH = 1664
MAX_HEIGHT = 2048
TASK_PROMPT = (
    "</s><s><predict_bbox><predict_classes><output_markdown><predict_no_text_in_pic>"
)
