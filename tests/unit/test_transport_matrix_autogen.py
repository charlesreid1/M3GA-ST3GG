"""CI guard: TRANSPORT_MATRIX.md stays in sync with survival.json.

If this test fails, an edit to `knowledge/records/survival.json` or
`transports.json` was made without regenerating the matrix. Regenerate with:

    python scripts/render_transport_matrix.py --write
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "render_transport_matrix.py"


def test_transport_matrix_in_sync():
    assert SCRIPT.exists(), f"generator script missing: {SCRIPT}"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(
            "TRANSPORT_MATRIX.md is out of sync with survival.json.\n"
            "Run: python scripts/render_transport_matrix.py --write\n\n"
            f"--- diff ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}"
        )
