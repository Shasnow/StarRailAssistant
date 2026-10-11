"""Opt-in private replay inputs, kept outside the published test fixtures.

Set SRA_CURRENCY_WARS_REPLAY_DIR to a locally reviewed screenshot directory.
No screenshots are bundled. OCR replay also needs SRA_POPULATION_OCR_DEPS and
SRA_CURRENCY_WARS_OCR_DIR (config.yaml plus a models/ directory).
"""
from __future__ import annotations

import os
from pathlib import Path
import unittest


REPLAY_ROOT = Path(os.environ.get(
    "SRA_CURRENCY_WARS_REPLAY_DIR",
    str(Path(__file__).resolve().parent / "fixtures" / "currency_wars_private"),
))
OCR_ROOT = Path(os.environ.get("SRA_CURRENCY_WARS_OCR_DIR", str(REPLAY_ROOT / "rapidocr")))


def require_frames(*paths: Path) -> None:
    if not all(path.is_file() for path in paths):
        raise unittest.SkipTest("Optional private replay images are not configured")


def open_rgb(path: Path):
    from PIL import Image

    require_frames(path)
    with Image.open(path) as image:
        return image.convert("RGB").copy()
