"""CI guard: skill/reference docs stay in sync with TOOL_SCHEMAS.

If this test fails, the MCP tool registry drifted from the docs the model
reads. Regenerate with:

    python scripts/render_skill_tool_index.py --write
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "render_skill_tool_index.py"


def test_skill_tool_index_in_sync():
    assert SCRIPT.exists(), f"generator script missing: {SCRIPT}"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(
            "skill/reference tool index is out of sync with TOOL_SCHEMAS.\n"
            "Run: python scripts/render_skill_tool_index.py --write\n\n"
            f"--- diff ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}"
        )
