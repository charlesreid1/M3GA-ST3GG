#!/usr/bin/env python3
"""Regenerate ``ALL_MODULES`` in ``src/m3gast3gg/core/transforms/_index.py``.

Walks ``src/m3gast3gg/core/transforms/<category>/*.py``, sorts by
(category, module name), and writes the tuple between the fenced markers::

    # <!-- BEGIN autogen: transforms-index -->
    ALL_MODULES = (
        "m3gast3gg.core.transforms.encoding.base64",
        ...
    )
    # <!-- END autogen: transforms-index -->

Skips files starting with an underscore (``_base_n.py``) and any ``__init__.py``.

Usage:
    python scripts/regen_transforms_index.py --write
    python scripts/regen_transforms_index.py --check
    python scripts/regen_transforms_index.py --stdout
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TRANSFORMS_DIR = REPO_ROOT / "src" / "m3gast3gg" / "core" / "transforms"
INDEX_FILE = TRANSFORMS_DIR / "_index.py"

BEGIN_FENCE = "# <!-- BEGIN autogen: transforms-index -->"
END_FENCE = "# <!-- END autogen: transforms-index -->"


def collect_modules() -> list[str]:
    """Return the sorted list of transform module dotted paths."""
    modules: list[str] = []
    if not TRANSFORMS_DIR.is_dir():
        raise FileNotFoundError(f"transforms directory missing: {TRANSFORMS_DIR}")
    for category_dir in sorted(TRANSFORMS_DIR.iterdir()):
        if not category_dir.is_dir() or category_dir.name.startswith("_"):
            continue
        for py in sorted(category_dir.glob("*.py")):
            if py.name.startswith("_") or py.name == "__init__.py":
                continue
            modules.append(
                f"m3gast3gg.core.transforms.{category_dir.name}.{py.stem}"
            )
    return modules


def render_block(modules: list[str]) -> str:
    inner = "\n".join(f'    "{m}",' for m in modules)
    return f"{BEGIN_FENCE}\nALL_MODULES = (\n{inner}\n)\n{END_FENCE}"


def replace_block(text: str, new_block: str) -> str:
    pattern = re.compile(
        re.escape(BEGIN_FENCE) + r".*?" + re.escape(END_FENCE),
        re.DOTALL,
    )
    if not pattern.search(text):
        raise RuntimeError(
            f"could not find fenced block in {INDEX_FILE}; "
            "expected BEGIN/END autogen markers"
        )
    return pattern.sub(new_block, text)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="write _index.py")
    mode.add_argument("--check", action="store_true", help="fail if drifted")
    mode.add_argument("--stdout", action="store_true", help="print to stdout")
    args = ap.parse_args()

    modules = collect_modules()
    new_block = render_block(modules)

    current = INDEX_FILE.read_text(encoding="utf-8")
    updated = replace_block(current, new_block)

    if args.stdout:
        print(updated, end="")
        return 0
    if args.write:
        if updated != current:
            INDEX_FILE.write_text(updated, encoding="utf-8")
            print(f"wrote {INDEX_FILE} ({len(modules)} modules)")
        else:
            print(f"{INDEX_FILE} already up to date")
        return 0
    if args.check:
        if updated != current:
            print(
                f"{INDEX_FILE} is out of sync with the transforms directory.\n"
                f"Run: python scripts/regen_transforms_index.py --write",
                file=sys.stderr,
            )
            return 1
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
