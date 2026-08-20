"""CI drift-detect: _index.py matches the transforms directory."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_transforms_index_up_to_date():
    """Fails with the exact command needed to fix the drift."""
    proc = subprocess.run(
        [sys.executable, "scripts/regen_transforms_index.py", "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise AssertionError(
            "src/m3gast3gg/core/transforms/_index.py is out of sync.\n"
            f"stderr: {proc.stderr}\n"
            "Run: python scripts/regen_transforms_index.py --write"
        )
