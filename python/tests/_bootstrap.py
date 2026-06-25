"""Make runtime modules importable for unittest discovery from the repo root."""

from __future__ import annotations

import pathlib
import sys


PYTHON_DIR = pathlib.Path(__file__).resolve().parents[1]
python_dir = str(PYTHON_DIR)
if python_dir not in sys.path:
    sys.path.insert(0, python_dir)
