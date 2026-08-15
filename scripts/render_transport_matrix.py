#!/usr/bin/env python3
"""Regenerate the transport-survival matrix table in TRANSPORT_MATRIX.md.

The matrix used to be hand-authored prose next to `survival.json`; anything the
model read from prose was two edits away from the record layer. This script
makes `survival.json` authoritative — the fenced block in the doc is derived,
not authored.

For every survival record it drops one cell into a technique × transport table.
Umbrella records (e.g. `sv-text-http-raw` with `technical_body.applies_to`) get
expanded — one cell per applies_to id. Cells with no record show `❓`; cells
where technique and transport carrier families are incompatible show `➖`.

Fence:

    <!-- BEGIN autogen: transport matrix -->
    ...
    <!-- END autogen: transport matrix -->

Usage:
    python scripts/render_transport_matrix.py --write
    python scripts/render_transport_matrix.py --check
    python scripts/render_transport_matrix.py --stdout
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from st3ggmcp import records  # noqa: E402

BEGIN_FENCE = "<!-- BEGIN autogen: transport matrix -->"
END_FENCE = "<!-- END autogen: transport matrix -->"

TARGET = REPO_ROOT / "st3ggmcp" / "TRANSPORT_MATRIX.md"
RECORDS_DIR = REPO_ROOT / "knowledge" / "records"

# Column order — Slack triple first (the most-tested), then image-heavy
# transports, then universal file channels, then terminal/clipboard.
TRANSPORT_ORDER = [
    "transport-slack-upload",
    "transport-slack-paste",
    "transport-slack-snippet",
    "transport-discord-upload",
    "transport-discord-paste",
    "transport-telegram-photo",
    "transport-telegram-file",
    "transport-whatsapp-photo",
    "transport-whatsapp-document",
    "transport-signal-attachment",
    "transport-imessage-photo",
    "transport-imessage-attachment",
    "transport-email-attachment",
    "transport-gmail-inline",
    "transport-github-upload",
    "transport-http-raw",
    "transport-terminal-stdout",
    "transport-pbcopy",
]

# Short column labels (the transport `name` field is too wordy for a table).
COLUMN_LABEL = {
    "transport-slack-upload":     "Slack (upload)",
    "transport-slack-paste":      "Slack (paste)",
    "transport-slack-snippet":    "Slack (snip)",
    "transport-discord-upload":   "Discord (up)",
    "transport-discord-paste":    "Discord (paste)",
    "transport-telegram-photo":   "TG (photo)",
    "transport-telegram-file":    "TG (file)",
    "transport-whatsapp-photo":   "WA (photo)",
    "transport-whatsapp-document":"WA (doc)",
    "transport-signal-attachment":"Signal",
    "transport-imessage-photo":   "iMsg (photo)",
    "transport-imessage-attachment":"iMsg (attach)",
    "transport-email-attachment": "Email",
    "transport-gmail-inline":     "Gmail inline",
    "transport-github-upload":    "GitHub",
    "transport-http-raw":         "HTTP raw",
    "transport-terminal-stdout":  "Terminal",
    "transport-pbcopy":           "pbcopy",
}

# Row order — image first, then text, then emoji. Within a family, roughly
# bit / coefficient / container / character / semantic.
FAMILY_ORDER = {"image": 0, "text": 1, "emoji": 2, "audio": 3, "network": 4, "document": 5}
LAYER_ORDER = {"bit": 0, "coefficient": 1, "container": 2, "character": 3, "semantic": 4}


def _short_status(raw: str) -> str:
    """Compact form of `technical_body.status` for a table cell."""
    if not raw:
        return "❓"
    s = raw.strip()
    # `✅ survives` -> `✅`, `❌ stripped` -> `❌`, `⚠ tuned only` -> `⚠ tuned`
    parts = s.split(None, 1)
    if not parts:
        return "❓"
    sym = parts[0]
    if sym in ("✅", "❌", "❓", "➖"):
        # Include the qualifier only when it changes the read (`✅ likely`, `❌ recoded`).
        rest = parts[1] if len(parts) > 1 else ""
        if rest.startswith(("survives", "stripped", "unknown", "n/a")):
            return sym
        return f"{sym} {rest}" if rest else sym
    if sym == "⚠":
        rest = parts[1] if len(parts) > 1 else ""
        return f"⚠ {rest}" if rest else "⚠"
    return s


def _compatible(technique: dict, transport: dict) -> bool:
    """False iff the (technique, transport) combination is nonsensical."""
    tfam = (transport.get("carrier_family") or "").strip()
    if tfam in ("", "universal"):
        return True
    kfam = (technique.get("carrier_family") or "").strip()
    if kfam in ("", "universal"):
        return True
    if tfam == "text":
        # Text transports carry text and emoji techniques; image/audio don't ride text.
        return kfam in ("text", "emoji")
    if tfam == "image":
        return kfam == "image"
    # audio/network transports: only their own family.
    return kfam == tfam


def _build_cell_index(store: records.RecordStore) -> dict[tuple[str, str], dict]:
    """(technique_id, transport_id) -> survival record.

    Expands umbrella records (`applies_to` in technical_body) so a single
    survival record can fill many cells.
    """
    idx: dict[tuple[str, str], dict] = {}
    for rec in store.in_category("survival"):
        body = rec.get("technical_body") or {}
        tport = body.get("transport_id")
        if not tport:
            continue
        techs = [body.get("technique_id")]
        for extra in body.get("applies_to") or []:
            if extra not in techs:
                techs.append(extra)
        for tid in techs:
            if not tid:
                continue
            idx.setdefault((tid, tport), rec)
    return idx


def _row_techniques(store: records.RecordStore, cell_index: dict) -> list[dict]:
    """Every technique that appears in at least one survival cell."""
    referenced: set[str] = {tid for (tid, _) in cell_index.keys()}
    techs = [store.get(tid) for tid in referenced]
    techs = [t for t in techs if t is not None and t.get("category") == "technique"]

    def _sort_key(t: dict) -> tuple:
        return (
            FAMILY_ORDER.get(t.get("carrier_family") or "", 99),
            LAYER_ORDER.get(t.get("layer") or "", 99),
            t.get("id", ""),
        )

    return sorted(techs, key=_sort_key)


def _render_table(store: records.RecordStore) -> list[str]:
    cell_index = _build_cell_index(store)
    techniques = _row_techniques(store, cell_index)
    transports = [store.get(tid) for tid in TRANSPORT_ORDER]
    transports = [t for t in transports if t is not None]

    header_cells = ["Technique"] + [COLUMN_LABEL.get(t["id"], t.get("name", t["id"])) for t in transports]
    lines = ["| " + " | ".join(header_cells) + " |"]
    lines.append("| " + " | ".join(["---"] * len(header_cells)) + " |")

    used_records: dict[str, dict] = {}

    for tech in techniques:
        row = [f"`{tech['id']}`"]
        for tport in transports:
            rec = cell_index.get((tech["id"], tport["id"]))
            if rec is None:
                cell = "➖" if not _compatible(tech, tport) else "❓"
            else:
                body = rec.get("technical_body") or {}
                cell = _short_status(body.get("status", ""))
                used_records[rec["id"]] = rec
            row.append(cell)
        lines.append("| " + " | ".join(row) + " |")

    lines.append("")
    lines.append("Legend: `✅` survives · `❌` stripped/destroyed · `⚠` conditional (see caveat) · `❓` untested · `➖` nonsensical combination.")

    if used_records:
        lines.append("")
        lines.append("### Cell provenance")
        lines.append("")
        lines.append(
            "Every non-`❓`/non-`➖` cell above maps to a survival record — look up with "
            "`stegg_verify_survival(technique, transport)`, or find the record id below."
        )
        lines.append("")
        for rid in sorted(used_records):
            rec = used_records[rid]
            body = rec.get("technical_body") or {}
            tested = body.get("tested_at") or "—"
            lines.append(f"- `{rid}` — {rec.get('name', rid)} · tested {tested}")

    return lines


def render() -> str:
    store = records.RecordStore.load(RECORDS_DIR)
    body = _render_table(store)
    lines = [BEGIN_FENCE, "<!-- Generated by scripts/render_transport_matrix.py — do not edit by hand. -->", ""]
    lines.extend(body)
    lines.append("")
    lines.append(END_FENCE)
    return "\n".join(lines)


_FENCED_RE = re.compile(
    re.escape(BEGIN_FENCE) + r".*?" + re.escape(END_FENCE),
    re.DOTALL,
)


def apply(path: Path) -> tuple[str, str]:
    old = path.read_text(encoding="utf-8")
    if BEGIN_FENCE not in old or END_FENCE not in old:
        raise SystemExit(
            f"{path}: missing autogen fences ({BEGIN_FENCE!r} / {END_FENCE!r}). "
            "Add them once by hand around the matrix section."
        )
    new_block = render()
    new = _FENCED_RE.sub(lambda _m: new_block, old, count=1)
    return old, new


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="Rewrite TRANSPORT_MATRIX.md in place.")
    mode.add_argument("--check", action="store_true", help="Exit non-zero if the file would change.")
    mode.add_argument("--stdout", action="store_true", help="Print the block to stdout.")
    args = parser.parse_args(argv)

    if args.stdout:
        print(render())
        return 0

    old, new = apply(TARGET)
    if old == new:
        return 0
    if args.check:
        diff = difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=f"{TARGET} (committed)",
            tofile=f"{TARGET} (regenerated)",
        )
        sys.stdout.writelines(diff)
        print(
            f"\nTRANSPORT_MATRIX.md is out of sync with survival.json. "
            "Run: python scripts/render_transport_matrix.py --write",
            file=sys.stderr,
        )
        return 1
    TARGET.write_text(new, encoding="utf-8")
    print(f"wrote {TARGET}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
