#!/usr/bin/env python3
"""Slack Transport Survivability Test Harness — FULLY AUTOMATED.

Usage:
    python tests/transport/test_slack.py --all          # every cell, all waves
    python tests/transport/test_slack.py --wave 1       # single wave
    python tests/transport/test_slack.py --cell <id>    # single cell
    python tests/transport/test_slack.py --all --dry-run
    python tests/transport/test_slack.py --gen-probes-only
    python tests/transport/test_slack.py --gen-ui-kit   # Section 8 manual kit

Outputs:
    TRANSPORT_RESULTS_SLACK.json                        # filled matrix
    transport_probes/slack/encoded/*                     # encoded artifacts
    transport_probes/slack/retrieved/*                   # downloaded artifacts
    transport_probes/slack/evidence/*.json               # per-cell evidence
"""

import argparse
import hashlib
import json
import os
import random
import re
import shutil
import string
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import f5_core.jsteg as jsteg
import text_core

# ---------------------------------------------------------------------------
# paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PROBE_DIR = REPO_ROOT / "transport_probes" / "slack"
CLEAN_DIR = PROBE_DIR / "clean"
ENCODED_DIR = PROBE_DIR / "encoded"
RETRIEVED_DIR = PROBE_DIR / "retrieved"
EVIDENCE_DIR = PROBE_DIR / "evidence"

SECRETS_PATH = Path(__file__).resolve().parent / "secrets_slack.json"
MATRIX_PATH = Path(__file__).resolve().parent / "matrix_slack.json"
RESULTS_PATH = REPO_ROOT / "TRANSPORT_RESULTS_SLACK.json"

PAYLOAD_PREFIX = "SLACK_PROBE"

# Ensure output dirs exist
for _d in (CLEAN_DIR, ENCODED_DIR, RETRIEVED_DIR, EVIDENCE_DIR):
    _d.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rand_id(k: int = 6) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=k))


def _make_payload(technique: str, timestamp: str, payload_bytes: int | None = None) -> str:
    """Deterministic-but-unique payload per cell.

    `payload_bytes` sets the total length in bytes (default 128). Cells
    whose technique has small carrier capacity (whitespace, hangul, etc.)
    override this via the matrix cell's `payload_bytes` field so the
    probe actually fits — and cells whose method balloons on the wire
    (emoji, skintone) must specify a small `payload_bytes` to stay under
    Slack's ~4000-char message store cap.

    If payload_bytes is smaller than the full descriptive inner template,
    return a short marker `{PREFIX}|{rand}` truncated/padded to
    payload_bytes. This preserves probe uniqueness at any size ≥ 12 bytes.
    """
    rand = _rand_id(8)
    inner = f"{PAYLOAD_PREFIX}|{technique}|{timestamp}|{rand}"
    if payload_bytes is not None and int(payload_bytes) < len(inner):
        # Short mode: fit within payload_bytes using just prefix + rand.
        short = f"{PAYLOAD_PREFIX[:3]}|{rand}"
        target = int(payload_bytes)
        if len(short) >= target:
            return short[:target]
        return short + ("P" * (target - len(short)))
    target = 128 if payload_bytes is None else int(payload_bytes)
    pad = "P" * max(0, target - len(inner))
    return inner + pad


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_path(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _file_fingerprint(path: Path | str) -> dict:
    p = Path(path)
    if not p.exists():
        return {"exists": False, "sha256": None, "size": 0}
    data = p.read_bytes()
    return {"exists": True, "sha256": _sha256(data), "size": len(data)}


def _run_stegg(*args: str, timeout: float = 30.0) -> subprocess.CompletedProcess:
    """Run the stegg CLI. Returns CompletedProcess. Raises on timeout/nonzero."""
    cmd = [sys.executable, str(REPO_ROOT / "cli.py"), "--quiet", "--json", *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(REPO_ROOT))


class SteggCLIError(Exception):
    """Raised when the stegg CLI reports an encode/decode failure.

    stegg CLI prints errors to stdout prefixed with '✗' and exits nonzero.
    Callers that swallow the exit code and treat stdout as data end up
    uploading error strings as if they were stego output. Don't do that."""
    def __init__(self, message: str, stdout: str = "", stderr: str = "", returncode: int = 0):
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


class ProbeConfigError(Exception):
    """Raised when a matrix cell is self-inconsistent — e.g. its declared
    payload can't fit in the (grown) cover for its technique. Propagates
    past run_cell's blanket catch (same pattern as SteggCLIError) so the
    whole run aborts and the operator fixes the cell before touching
    Slack."""


# ---------------------------------------------------------------------------
# text-cover sizing
# ---------------------------------------------------------------------------

_COVER_SEEDS = {
    # For cover-limited techniques, we grow a cover by repeating a
    # technique-appropriate seed until capacity fits. Deterministic:
    # same (method, payload_bytes) -> same cover across runs.
    "whitespace": "The quick brown fox jumps over the lazy dog.\n",
    "hangul":     "The quick brown fox jumps over the lazy dog. ",  # ASCII spaces are the carriers
    "confusable": "The quick brown fox jumps over the lazy dog. ",  # ASCII spaces again
    "capitalization": "The quick brown fox jumps over the lazy dog. ",  # word-initial letters
    "variation":  "the quick brown fox jumps over the lazy dog ",  # ASCII alnum
    "combining":  "the quick brown fox jumps over the lazy dog ",  # ASCII alpha
    "mathbold":   "the quick brown fox jumps over the lazy dog ",  # ASCII letters
    "cyrillic_homoglyph": "acex oxpy AB CE HK MO PT X. ",  # rich in Latin twin letters
    "cjk_homoglyph": "one, two. three; four: five! six? (seven) eight. ",  # ASCII punctuation
    # unbounded methods don't need growth — a short cover suffices
}

_DEFAULT_COVER = "The quick brown fox jumps over the lazy dog. " * 3


def _grow_cover_for_capacity(method: str, payload_bytes: int, seed_cover: str | None = None) -> str:
    """Return a cover long enough that `text_core.capacity(cover, method)`
    reports `payload_bytes_max >= payload_bytes`.

    Uses a technique-appropriate seed string (or the caller's override)
    and repeats it until capacity fits, with a safety cap. Deterministic —
    no RNG involved, so re-runs of the same cell produce the same cover."""
    seed = seed_cover if seed_cover is not None else _COVER_SEEDS.get(method, _DEFAULT_COVER)
    if not seed:
        raise ProbeConfigError(f"{method}: empty cover seed")
    # Probe capacity of the seed once to estimate repetitions.
    try:
        cap = text_core.capacity(seed, method)
    except Exception as e:
        raise ProbeConfigError(f"{method}: capacity() rejected seed: {e}") from e
    cb = cap.get("carrier_bits")
    if cb is None:
        # Unbounded technique — any non-empty cover works.
        return seed
    needed_bits = payload_bytes * 8 + 16  # 16-bit length prefix used by every cover-limited method
    if cb <= 0:
        # Seed contributes zero bits — retrying won't help.
        raise ProbeConfigError(
            f"{method}: seed contributes 0 carrier bits; supply a cover with the right carrier characters"
        )
    reps = max(1, (needed_bits + cb - 1) // cb + 1)  # +1 for safety margin
    cover = seed * reps
    # Verify. Cap at 100x the estimated reps to catch pathological cases.
    for _ in range(3):
        cap = text_core.capacity(cover, method)
        if cap.get("payload_bytes_max", 0) >= payload_bytes:
            return cover
        cover = cover * 2
    raise ProbeConfigError(
        f"{method}: could not grow cover to fit {payload_bytes} bytes "
        f"(final capacity: {cap.get('payload_bytes_max')})"
    )


def _resolve_text_cover_and_payload(cell: dict, technique: str, timestamp: str) -> tuple[str, str]:
    """Return (cover, payload) for a text-stego cell, honoring per-cell
    payload_bytes/cover_text/cover_seed, and running the capacity gate.

    Raises ProbeConfigError if the resolved cover can't fit the payload."""
    cfg = cell.get("encode_config", {})
    method = cfg["method"]
    payload_bytes = cfg.get("payload_bytes")
    payload = _make_payload(technique, timestamp, payload_bytes=payload_bytes)
    actual_bytes = len(payload.encode("utf-8"))

    cover_text = cfg.get("cover_text")
    cover_seed = cfg.get("cover_seed")
    if cover_text is not None:
        cover = cover_text
    else:
        cover = _grow_cover_for_capacity(method, actual_bytes, seed_cover=cover_seed)

    # Capacity gate — refuse locally, don't send garbage to Slack.
    try:
        cap = text_core.capacity(cover, method)
    except Exception as e:
        raise ProbeConfigError(f"{method}: capacity() failed: {e}") from e
    cb = cap.get("carrier_bits")
    max_bytes = cap.get("payload_bytes_max")
    if cb is not None and max_bytes is not None and actual_bytes > max_bytes:
        raise ProbeConfigError(
            f"cell {cell.get('id')}: {method} cover holds {max_bytes} B, "
            f"cell needs {actual_bytes} B (add cover_text/cover_seed or shrink payload_bytes)"
        )
    return cover, payload


def _run_stegg_text(*args: str, timeout: float = 15.0) -> str:
    """Run stegg and return stdout stripped. Raises SteggCLIError on failure.

    Failure = nonzero exit code, or stdout starting with the '✗' sentinel
    that stegg CLI uses for user-facing errors. Text output (no --json)."""
    cmd = [sys.executable, str(REPO_ROOT / "cli.py"), "--quiet", *args]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(REPO_ROOT))
    out = r.stdout.strip()
    if r.returncode != 0 or out.startswith("✗"):
        raise SteggCLIError(
            f"stegg CLI failed (rc={r.returncode}): {out[:200] or r.stderr[:200]}",
            stdout=out, stderr=r.stderr, returncode=r.returncode,
        )
    return out


# ---------------------------------------------------------------------------
# metadata / chunk verifiers
# ---------------------------------------------------------------------------

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _read_png_metadata(path: Path | str) -> dict:
    """Read a PNG's tEXt/zTXt/iTXt fields (via PIL image.info).

    Returns {"info": {key: value, ...}} on success or {"error": "..."}
    if the file isn't a readable PNG. This is what the exif-handler's
    verification step consumes — never infer STRIPPED from a hash mismatch
    alone; open the file and check the key's actual presence."""
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return {"error": "file missing or empty"}
    try:
        head = p.read_bytes()[:8]
        if head != _PNG_MAGIC:
            return {"error": f"not a PNG (magic={head.hex()})"}
        from PIL import Image
        with Image.open(p) as img:
            img.load()
            # Coerce non-string values (rare — e.g. gamma) into repr for JSON.
            return {"info": {k: (v if isinstance(v, (str, int, float, bool)) else repr(v))
                             for k, v in img.info.items()}}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def _classify_metadata_result(
    pre_fp: dict, post_fp: dict, pre_meta: dict, post_meta: dict,
    target_key: str | None, payload: str,
) -> str:
    """Verdict for the PNG-tEXt (image_exif) handler.

    Decision is based on the retrieved file's *actual* metadata slot for
    target_key, not on hash comparison. Hash equality is used only to
    distinguish "field survived, bytes intact" from "field survived, other
    bytes changed" (DEGRADED)."""
    if not post_fp["exists"]:
        return "API_ERROR"
    if "error" in post_meta:
        return "CARRIER_DESTROYED"
    if target_key is None:
        # Custom-field probe with no single target — fall back to hash.
        return "SURVIVES" if pre_fp["sha256"] == post_fp["sha256"] else "STRIPPED"

    post_info = post_meta.get("info", {})
    field_present = target_key in post_info and post_info[target_key] == payload
    hashes_match = pre_fp["sha256"] == post_fp["sha256"]

    if field_present and hashes_match:
        return "SURVIVES"
    if field_present and not hashes_match:
        return "DEGRADED"
    # Field is gone. Whether the surrounding carrier was also re-encoded
    # is a separate question — signal that with RECODED if the size shift
    # is large relative to just removing the tEXt chunk.
    if pre_fp["size"] > 0 and abs(post_fp["size"] - pre_fp["size"]) > pre_fp["size"] * 0.2:
        return "RECODED"
    return "STRIPPED"


_STANDARD_PNG_CHUNKS = {"IHDR", "IDAT", "IEND", "PLTE", "tRNS", "gAMA",
                        "cHRM", "sRGB", "iCCP", "bKGD", "pHYs", "sBIT",
                        "sPLT", "hIST", "tIME"}


def _classify_chunk_result(
    pre_fp: dict, post_fp: dict, chunks_post: dict,
    target_chunk_type: str,
) -> str:
    """Verdict for the image_chunk handler.

    Uses `stegg chunks` output on the retrieved PNG to distinguish a real
    STRIPPED (target chunk absent, carrier intact) from CARRIER_DESTROYED
    (unreadable) and DEGRADED (chunk survived but other bytes changed)."""
    if not post_fp["exists"]:
        return "API_ERROR"
    if "error" in chunks_post:
        return "CARRIER_DESTROYED"

    retrieved_types = {c.get("type") for c in chunks_post.get("chunks", [])}
    if "IHDR" not in retrieved_types or "IEND" not in retrieved_types:
        return "CARRIER_DESTROYED"

    target_present = target_chunk_type in retrieved_types
    hashes_match = pre_fp["sha256"] == post_fp["sha256"]

    if target_present and hashes_match:
        return "SURVIVES"
    if target_present and not hashes_match:
        return "DEGRADED"
    # target absent
    if pre_fp["size"] > 0 and abs(post_fp["size"] - pre_fp["size"]) > pre_fp["size"] * 0.2:
        return "RECODED"
    return "STRIPPED"


# ---------------------------------------------------------------------------
# classification
# ---------------------------------------------------------------------------

VERDICTS = [
    "SURVIVES",           # payload actually recoverable after transport
    "STRIPPED",           # metadata removed but carrier intact
    "RECODED",            # file re-encoded, carrier format changed
    "DEGRADED",           # bytes preserved but payload no longer decodes
    "TRUNCATED",          # Slack cut the message/file mid-content (retrieved is a strict prefix, or notably shorter than sent)
    "CARRIER_DESTROYED",  # file unreadable / format corrupted
    "API_ERROR",          # Slack API rejected or failed
    "SKIPPED",            # test not run (dry run, missing dep, etc.)
]

# Slack stores messages in `blocks` and renders them at ~4000 chars of
# colon-form-expanded text. Anything past that ceiling is dropped from
# BOTH `blocks` and the `text` preview. For non-emoji text the encoded
# length ~= wire length so a plain-text cap around 3500 chars is safe;
# for emoji/skintone the wire length balloons ~12–15x per emoji so those
# cells must specify small payload_bytes in the matrix.
SLACK_MSG_STORE_LIMIT_CHARS = 3500

# Rough per-character wire-form cost for emoji-family methods. Used to
# pre-check whether encoded text will exceed the storage ceiling. Length
# of `:red_circle:` is 12; `:+1::skin-tone-3:` per glyph averages ~15.
_EMOJI_WIRE_EXPANSION = {
    "emoji":    12,   # :red_circle: / :large_blue_circle:
    "skintone": 15,   # :+1::skin-tone-N:
}


def _estimate_wire_chars(encoded_text: str, method: str) -> int:
    """Estimate the colon-form-expanded length Slack will store for this text.

    For emoji-family methods, count non-ASCII runes and apply the
    per-method expansion factor; ASCII passes through 1:1. For all other
    methods (zero-width, whitespace, homoglyph, ...) the wire form is
    the same length as the input, so return raw length.
    """
    factor = _EMOJI_WIRE_EXPANSION.get(method)
    if not factor:
        return len(encoded_text)
    ascii_chars = sum(1 for c in encoded_text if ord(c) < 128)
    wide_chars = len(encoded_text) - ascii_chars
    return ascii_chars + wide_chars * factor

def _classify(pre_fp: dict, post_fp: dict, technique: str, retrieved_path: Path | None = None) -> tuple[str, dict]:
    """Compare pre/post fingerprints and return (verdict, details_dict)."""
    details: dict[str, Any] = {"pre": pre_fp, "post": post_fp}

    if not post_fp["exists"]:
        return "API_ERROR", details

    # Byte-identical = survives
    if pre_fp["sha256"] == post_fp["sha256"]:
        return "SURVIVES", details

    # Bytes differ — try to figure out what happened
    details["size_delta"] = post_fp["size"] - pre_fp["size"]

    # If size is zero or very small, carrier destroyed
    if post_fp["size"] < 4:
        return "CARRIER_DESTROYED", details

    # If size grew or shrank significantly, likely recoded
    if abs(details["size_delta"]) > pre_fp["size"] * 0.2:
        return "RECODED", details

    # Check if we can still detect stego content (for text techniques)
    if technique.startswith("text_"):
        return "DEGRADED", details

    # For image chunk techniques, if size changed but not destroyed, likely stripped
    if technique.startswith("chunk_") or technique.startswith("exif_") or technique.startswith("tEXt"):
        return "STRIPPED", details

    # Default: bytes changed, unknown severity
    return "RECODED", details


# ---------------------------------------------------------------------------
# Slack transport harness
# ---------------------------------------------------------------------------

class SlackTransportHarness:
    """Orchestrates the encode → send → retrieve → verify loop."""

    def __init__(self, secrets: dict, dry_run: bool = False):
        self.dry_run = dry_run
        if not dry_run:
            from slack_client import SlackTransportClient
            self.client = SlackTransportClient(
                bot_token=secrets["bot_token"],
                channel_id=secrets["channel_id"],
            )
        else:
            self.client = None
        self.results: list[dict] = []
        self.timestamp = _now_iso().replace(":", "-").replace(".", "-")[:19]

    # ------------------------------------------------------------------
    # main entry point
    # ------------------------------------------------------------------

    def run(self, cells: list[dict], wave_label: str = "") -> list[dict]:
        """Run a list of cells. Returns only the results produced by THIS call."""
        total = len(cells)
        this_run: list[dict] = []
        for i, cell in enumerate(cells, 1):
            print(f"\n{'─'*60}")
            print(f"[{i}/{total}] {cell['id']}  ({cell.get('description', '')})")
            print(f"  transport={cell['transport']}  technique={cell['technique']}  expect={cell.get('expect','?')}")
            result = self.run_cell(cell)
            self.results.append(result)
            this_run.append(result)
            self._print_verdict(result)
        return this_run

    def run_cell(self, cell: dict) -> dict:
        """Run a single cell and return its result dict."""
        result = {
            "id": cell["id"],
            "transport": cell["transport"],
            "technique": cell["technique"],
            "category": cell["category"],
            "wave": cell.get("wave"),
            "expect": cell.get("expect"),
            "description": cell.get("description", ""),
            "verdict": "SKIPPED",
            "started": _now_iso(),
            "evidence": {},
        }

        try:
            handler = getattr(self, f"_handle_{cell['category']}", None)
            if handler is None:
                handler = self._handle_generic
            handler(cell, result)
        except SteggCLIError:
            # ST3GG-side probe construction failed. This is a bug in the
            # probe config or the stegg library, not a transport verdict.
            # Fail loud — the whole run aborts, operator fixes the probe
            # spec before continuing. Do NOT paper over as API_ERROR.
            raise
        except ProbeConfigError:
            # Matrix cell is self-inconsistent (payload doesn't fit its
            # cover, unknown method, etc.). Same reasoning as SteggCLIError:
            # not a transport verdict, so fail loud rather than launder.
            raise
        except Exception as e:
            # Genuine Slack-transport failure (HTTP error, ok:false, etc.)
            result["verdict"] = "API_ERROR"
            result["error"] = f"{type(e).__name__}: {e}"

        result["finished"] = _now_iso()
        return result

    # ------------------------------------------------------------------
    # category handlers
    # ------------------------------------------------------------------

    def _handle_format_probe(self, cell: dict, result: dict) -> None:
        """Wave 1: upload clean format file, download, compare hashes."""
        fmt = cell["format"]
        clean_path = self._ensure_clean_probe(cell["id"], fmt)

        pre_fp = _file_fingerprint(clean_path)
        result["evidence"]["clean_path"] = str(clean_path)
        result["evidence"]["pre"] = pre_fp

        if self.dry_run:
            result["verdict"] = "SKIPPED"
            return

        # Upload
        upload_resp = self.client.upload_file(str(clean_path), title=clean_path.name)
        file_id = upload_resp["files"][0]["id"]
        result["evidence"]["send_response"] = {"file_id": file_id}

        # Download
        raw_bytes, meta = self.client.download_file(file_id)
        retrieved_path = RETRIEVED_DIR / f"{cell['id']}_{fmt.get('ext', 'bin')}"
        retrieved_path.write_bytes(raw_bytes)
        post_fp = _file_fingerprint(retrieved_path)
        result["evidence"]["retrieved_path"] = str(retrieved_path)
        result["evidence"]["post"] = post_fp
        result["evidence"]["slack_meta"] = {
            "mimetype": meta.get("mimetype", ""),
            "filetype": meta.get("filetype", ""),
            "size": meta.get("size", 0),
        }

        verdict, details = _classify(pre_fp, post_fp, "format_probe", retrieved_path)
        result["verdict"] = verdict
        result["evidence"]["classification"] = details

    def _handle_image_lsb(self, cell: dict, result: dict) -> None:
        """Wave 2: LSB encode → upload → download → verify."""
        cfg = cell.get("encode_config", {})
        channels = cfg.get("channels", "RGB")
        bits = cfg.get("bits", 1)
        strategy = cfg.get("strategy", "interleaved")
        seed = cfg.get("seed")
        clean_name = cfg.get("clean_input", "probe_150x150.png")
        clean_path = CLEAN_DIR / clean_name
        self._ensure_clean_png_present(clean_path)

        payload = _make_payload(cell["technique"], self.timestamp)
        encoded_path = ENCODED_DIR / f"{cell['id']}.png"

        # Encode
        encode_args = [
            "encode-cmd", "-i", str(clean_path),
            "-o", str(encoded_path),
            "-t", payload,
            "--channels", channels,
            "--bits", str(bits),
            "--strategy", strategy,
        ]
        if seed is not None:
            encode_args.extend(["--seed", str(seed)])

        r = _run_stegg(*encode_args)
        try:
            enc_result = json.loads(r.stdout) if r.stdout else {}
        except json.JSONDecodeError:
            enc_result = {"raw": r.stdout}
        result["evidence"]["encode"] = enc_result
        result["evidence"]["payload"] = payload

        pre_fp = _file_fingerprint(encoded_path)
        result["evidence"]["pre"] = pre_fp

        if self.dry_run:
            result["verdict"] = "SKIPPED"
            return

        # Upload
        upload_resp = self.client.upload_file(str(encoded_path), title=encoded_path.name)
        file_id = upload_resp["files"][0]["id"]
        result["evidence"]["send_response"] = {"file_id": file_id}

        # Download
        raw_bytes, meta = self.client.download_file(file_id)
        retrieved_path = RETRIEVED_DIR / f"{cell['id']}.png"
        retrieved_path.write_bytes(raw_bytes)
        post_fp = _file_fingerprint(retrieved_path)
        result["evidence"]["retrieved_path"] = str(retrieved_path)
        result["evidence"]["post"] = post_fp
        result["evidence"]["slack_meta"] = {
            "mimetype": meta.get("mimetype", ""),
            "filetype": meta.get("filetype", ""),
            "size": meta.get("size", 0),
        }

        # Verify: try decode on retrieved
        verdict, details = _classify(pre_fp, post_fp, cell["technique"], retrieved_path)
        if verdict != "SURVIVES":
            # Try to decode to see if payload survives despite byte changes
            decode_ok = self._try_lsb_decode(retrieved_path, channels, bits, strategy, seed, payload)
            details["payload_survives_decode"] = decode_ok
            if decode_ok:
                verdict = "DEGRADED"  # bytes changed but payload still extractable

        result["verdict"] = verdict
        result["evidence"]["classification"] = details

    def _handle_image_chunk(self, cell: dict, result: dict) -> None:
        """Wave 3: inject chunk → upload → download → check chunk presence."""
        cfg = cell.get("encode_config", {})
        chunk_type = cfg.get("chunk_type", "tEXt")
        keyword = cfg.get("keyword", "Comment")
        clean_path = CLEAN_DIR / cfg.get("clean_input", "probe_150x150.png")
        self._ensure_clean_png_present(clean_path)

        payload = _make_payload(cell["technique"], self.timestamp)
        encoded_path = ENCODED_DIR / f"{cell['id']}.png"

        chunk_args = [
            "inject", "chunk",
            "-i", str(clean_path),
            "-o", str(encoded_path),
            "--type", chunk_type,
            "--keyword", keyword,
            "-t", payload,
        ]
        if cfg.get("compressed"):
            chunk_args.append("--compressed")

        r = _run_stegg(*chunk_args)
        result["evidence"]["encode"] = {"stdout": r.stdout, "stderr": r.stderr}
        result["evidence"]["payload"] = payload

        pre_fp = _file_fingerprint(encoded_path)
        result["evidence"]["pre"] = pre_fp

        if self.dry_run:
            result["verdict"] = "SKIPPED"
            return

        upload_resp = self.client.upload_file(str(encoded_path), title=encoded_path.name)
        file_id = upload_resp["files"][0]["id"]
        result["evidence"]["send_response"] = {"file_id": file_id}

        raw_bytes, meta = self.client.download_file(file_id)
        retrieved_path = RETRIEVED_DIR / f"{cell['id']}.png"
        retrieved_path.write_bytes(raw_bytes)
        post_fp = _file_fingerprint(retrieved_path)
        result["evidence"]["retrieved_path"] = str(retrieved_path)
        result["evidence"]["post"] = post_fp
        result["evidence"]["slack_meta"] = {
            "mimetype": meta.get("mimetype", ""),
            "filetype": meta.get("filetype", ""),
            "size": meta.get("size", 0),
        }

        # Check chunk presence on retrieved. `stegg chunks` returning
        # nonzero or invalid JSON means the retrieved PNG isn't parseable;
        # surface that as a structured error so the classifier can decide
        # CARRIER_DESTROYED rather than inferring STRIPPED from a hash.
        chunks_data: dict = {}
        try:
            r2 = _run_stegg("chunks", str(retrieved_path))
            if r2.returncode != 0:
                chunks_data = {"error": f"rc={r2.returncode}: {r2.stderr[:200]}"}
            else:
                try:
                    chunks_data = json.loads(r2.stdout) if r2.stdout else {"error": "empty stdout"}
                except json.JSONDecodeError as je:
                    chunks_data = {"error": f"json decode: {je}"}
        except subprocess.TimeoutExpired:
            chunks_data = {"error": "stegg chunks timeout"}
        except Exception as e:
            chunks_data = {"error": f"{type(e).__name__}: {e}"}
        result["evidence"]["chunks_post"] = chunks_data

        details: dict[str, Any] = {"pre": pre_fp, "post": post_fp}
        details["size_delta"] = post_fp["size"] - pre_fp["size"]
        details["hashes_match"] = (pre_fp["sha256"] == post_fp["sha256"])
        retrieved_types = sorted({c.get("type") for c in chunks_data.get("chunks", []) if c.get("type")})
        details["retrieved_chunk_types"] = retrieved_types
        details["target_chunk_type"] = chunk_type
        details["target_chunk_present_post"] = chunk_type in retrieved_types

        verdict = _classify_chunk_result(pre_fp, post_fp, chunks_data, chunk_type)
        result["verdict"] = verdict
        result["evidence"]["classification"] = details

    def _handle_image_exif(self, cell: dict, result: dict) -> None:
        """Wave 3: inject PNG-tEXt metadata → upload → download → verify.

        The `inject exif` CLI writes PNG PngInfo, not JPEG EXIF — so this
        handler tests PNG-tEXt stripping (see cell ids `png_pseudo_exif_*`).
        Verification opens the retrieved PNG with PIL and inspects
        image.info for the specific field the encode step wrote."""
        cfg = cell.get("encode_config", {})
        clean_path = CLEAN_DIR / cfg.get("clean_input", "probe_150x150.png")
        self._ensure_clean_png_present(clean_path)

        payload = _make_payload(cell["technique"], self.timestamp)
        encoded_path = ENCODED_DIR / f"{cell['id']}.png"

        exif_args = [
            "inject", "exif",
            "-i", str(clean_path),
            "-o", str(encoded_path),
        ]
        field = cfg.get("field", "comment")
        exif_args.extend([f"--{field}", payload])
        if cfg.get("custom_fields"):
            exif_args.extend(["--custom-fields", json.dumps(cfg["custom_fields"])])

        r = _run_stegg(*exif_args)
        result["evidence"]["encode"] = {"stdout": r.stdout, "stderr": r.stderr}
        result["evidence"]["payload"] = payload

        # PIL PngInfo capitalizes the tEXt keyword. Track the exact key
        # written so verification checks the right slot.
        target_key = field.capitalize() if not cfg.get("custom_fields") else None
        result["evidence"]["target_key"] = target_key

        # Sanity check: injected key must be present in the encoded file.
        # If it isn't, the probe is broken and the STRIPPED/SURVIVES
        # distinction downstream is meaningless.
        pre_meta = _read_png_metadata(encoded_path)
        result["evidence"]["metadata_pre"] = pre_meta
        if target_key and (pre_meta.get("error") or target_key not in pre_meta.get("info", {})):
            raise SteggCLIError(
                f"probe bug: injected key {target_key!r} absent from encoded {encoded_path.name}"
            )

        pre_fp = _file_fingerprint(encoded_path)
        result["evidence"]["pre"] = pre_fp

        if self.dry_run:
            result["verdict"] = "SKIPPED"
            return

        upload_resp = self.client.upload_file(str(encoded_path), title=encoded_path.name)
        file_id = upload_resp["files"][0]["id"]
        result["evidence"]["send_response"] = {"file_id": file_id}

        raw_bytes, meta = self.client.download_file(file_id)
        retrieved_path = RETRIEVED_DIR / f"{cell['id']}.png"
        retrieved_path.write_bytes(raw_bytes)
        post_fp = _file_fingerprint(retrieved_path)
        result["evidence"]["retrieved_path"] = str(retrieved_path)
        result["evidence"]["post"] = post_fp
        result["evidence"]["slack_meta"] = {
            "mimetype": meta.get("mimetype", ""),
            "filetype": meta.get("filetype", ""),
            "size": meta.get("size", 0),
        }

        post_meta = _read_png_metadata(retrieved_path)
        result["evidence"]["metadata_post"] = post_meta

        details: dict[str, Any] = {"pre": pre_fp, "post": post_fp}
        details["size_delta"] = post_fp["size"] - pre_fp["size"]
        details["hashes_match"] = (pre_fp["sha256"] == post_fp["sha256"])

        verdict = _classify_metadata_result(
            pre_fp, post_fp, pre_meta, post_meta, target_key, payload,
        )
        details["target_key"] = target_key
        details["target_value_present_post"] = (
            target_key is not None
            and target_key in post_meta.get("info", {})
            and post_meta["info"][target_key] == payload
        )

        result["verdict"] = verdict
        result["evidence"]["classification"] = details

    def _handle_image_dct(self, cell: dict, result: dict) -> None:
        """Wave 4: DCT encode → upload → download → try decode."""
        cfg = cell.get("encode_config", {})
        clean_path = CLEAN_DIR / cfg.get("clean_input", "probe_150x150.png")
        self._ensure_clean_png_present(clean_path)

        # DCT has limited capacity (~31 bytes on 150x150) — use short payload
        payload = f"ST3GG|{cell['technique']}|{_rand_id(4)}"
        encoded_path = ENCODED_DIR / f"{cell['id']}.png"

        dct_args = [
            "dct", "encode",
            "-i", str(clean_path),
            "-o", str(encoded_path),
            "-t", payload,
        ]
        robustness = cfg.get("robustness", "medium")
        if robustness != "medium":
            dct_args.extend(["--robustness", robustness])
        if cfg.get("block_size"):
            dct_args.extend(["--block-size", str(cfg["block_size"])])

        r = _run_stegg(*dct_args)
        result["evidence"]["encode"] = {"stdout": r.stdout, "stderr": r.stderr}
        result["evidence"]["payload"] = payload

        pre_fp = _file_fingerprint(encoded_path)
        result["evidence"]["pre"] = pre_fp

        if self.dry_run:
            result["verdict"] = "SKIPPED"
            return

        upload_resp = self.client.upload_file(str(encoded_path), title=encoded_path.name)
        file_id = upload_resp["files"][0]["id"]
        result["evidence"]["send_response"] = {"file_id": file_id}

        raw_bytes, meta = self.client.download_file(file_id)
        retrieved_path = RETRIEVED_DIR / f"{cell['id']}.png"
        retrieved_path.write_bytes(raw_bytes)
        post_fp = _file_fingerprint(retrieved_path)
        result["evidence"]["post"] = post_fp

        # Try DCT decode
        decode_ok = False
        try:
            r2 = _run_stegg("dct", "decode", "-i", str(retrieved_path))
            dct_result = json.loads(r2.stdout) if r2.stdout else {}
            decode_ok = payload in r2.stdout
            result["evidence"]["decode"] = {"ok": decode_ok, "result": dct_result}
        except Exception as e:
            result["evidence"]["decode"] = {"ok": False, "error": str(e)}

        verdict, details = _classify(pre_fp, post_fp, cell["technique"], retrieved_path)
        if decode_ok:
            details["payload_survives_decode"] = True
        result["verdict"] = verdict
        result["evidence"]["classification"] = details

    def _handle_image_f5(self, cell: dict, result: dict) -> None:
        """Wave 4: F5 JPEG encode → upload → download → try decode."""
        cfg = cell.get("encode_config", {})
        clean_name = cfg.get("clean_input", "probe_150x150.jpg")
        clean_path = CLEAN_DIR / clean_name
        self._ensure_clean_jpg_present(clean_path)

        # F5 limited capacity on 150x150 JPEG — use short payload
        payload = f"ST3GG|{cell['technique']}|{_rand_id(4)}"
        password = cfg.get("password", "testpass")
        encoded_path = ENCODED_DIR / f"{cell['id']}.jpg"

        r = _run_stegg("dct", "f5", "encode",
                       "-i", str(clean_path),
                       "-o", str(encoded_path),
                       "-t", payload,
                       "-p", password)
        result["evidence"]["encode"] = {"stdout": r.stdout, "stderr": r.stderr}
        result["evidence"]["payload"] = payload

        pre_fp = _file_fingerprint(encoded_path)
        result["evidence"]["pre"] = pre_fp

        if self.dry_run:
            result["verdict"] = "SKIPPED"
            return

        upload_resp = self.client.upload_file(str(encoded_path), title=encoded_path.name)
        file_id = upload_resp["files"][0]["id"]
        result["evidence"]["send_response"] = {"file_id": file_id}

        raw_bytes, meta = self.client.download_file(file_id)
        retrieved_path = RETRIEVED_DIR / f"{cell['id']}.jpg"
        retrieved_path.write_bytes(raw_bytes)
        post_fp = _file_fingerprint(retrieved_path)
        result["evidence"]["post"] = post_fp

        # Try F5 decode
        decode_ok = False
        try:
            r2 = _run_stegg("dct", "f5", "decode",
                            "-i", str(retrieved_path),
                            "-p", password)
            decode_ok = payload in r2.stdout
            result["evidence"]["decode"] = {"ok": decode_ok, "stdout": r2.stdout}
        except Exception as e:
            result["evidence"]["decode"] = {"ok": False, "error": str(e)}

        verdict, details = _classify(pre_fp, post_fp, cell["technique"], retrieved_path)
        # Decode is authoritative for F5: a byte-identical round-trip
        # whose payload doesn't decode is DEGRADED, not SURVIVES — the
        # carrier's still valid but the stego is gone.
        details["payload_survives_decode"] = decode_ok
        if decode_ok:
            verdict = "SURVIVES"
        elif verdict == "SURVIVES":
            verdict = "DEGRADED"
        result["verdict"] = verdict
        result["evidence"]["classification"] = details

    def _handle_image_jsteg(self, cell: dict, result: dict) -> None:
        """Wave 4: JSteg JPEG encode → upload → download → try decode."""
        cfg = cell.get("encode_config", {})
        clean_name = cfg.get("clean_input", "probe_150x150.jpg")
        clean_path = CLEAN_DIR / clean_name
        self._ensure_clean_jpg_present(clean_path)

        # JSteg limited capacity on small JPEG — use short payload
        payload = f"ST3GG|{cell['technique']}|{_rand_id(4)}".encode()
        encoded_path = ENCODED_DIR / f"{cell['id']}.jpg"

        jpeg_bytes = clean_path.read_bytes()
        try:
            encoded_bytes = jsteg.jsteg_encode(jpeg_bytes, payload)
        except Exception as e:
            # In-process encode failed — this is a probe-config or library
            # bug, not a Slack transport failure. Raise the same exception
            # type CLI-side failures use so run_cell re-raises past its
            # blanket catch instead of laundering as API_ERROR.
            raise SteggCLIError(f"jsteg_encode failed: {type(e).__name__}: {e}") from e
        encoded_path.write_bytes(encoded_bytes)
        result["evidence"]["payload"] = payload.decode()
        result["evidence"]["encode"] = {"method": "jsteg_encode", "output_bytes": len(encoded_bytes)}

        pre_fp = _file_fingerprint(encoded_path)
        result["evidence"]["pre"] = pre_fp

        if self.dry_run:
            result["verdict"] = "SKIPPED"
            return

        upload_resp = self.client.upload_file(str(encoded_path), title=encoded_path.name)
        file_id = upload_resp["files"][0]["id"]
        result["evidence"]["send_response"] = {"file_id": file_id}

        raw_bytes, meta = self.client.download_file(file_id)
        retrieved_path = RETRIEVED_DIR / f"{cell['id']}.jpg"
        retrieved_path.write_bytes(raw_bytes)
        post_fp = _file_fingerprint(retrieved_path)
        result["evidence"]["post"] = post_fp

        # Try JSteg decode
        decode_ok = False
        try:
            extracted = jsteg.jsteg_decode(raw_bytes)
            decode_ok = payload in extracted if extracted else False
            result["evidence"]["decode"] = {"ok": decode_ok}
        except Exception as e:
            result["evidence"]["decode"] = {"ok": False, "error": str(e)}

        verdict, details = _classify(pre_fp, post_fp, cell["technique"], retrieved_path)
        # Decode is authoritative — same reasoning as F5 above.
        details["payload_survives_decode"] = decode_ok
        if decode_ok:
            verdict = "SURVIVES"
        elif verdict == "SURVIVES":
            verdict = "DEGRADED"
        result["verdict"] = verdict
        result["evidence"]["classification"] = details

    def _handle_image_trailing(self, cell: dict, result: dict) -> None:
        """Wave 4: append trailing bytes → upload → download → check."""
        cfg = cell.get("encode_config", {})
        clean_name = cfg.get("clean_input", "probe_150x150.png")
        clean_path = CLEAN_DIR / clean_name
        self._ensure_clean_png_present(clean_path)

        payload = _make_payload(cell["technique"], self.timestamp)
        encoded_path = ENCODED_DIR / f"{cell['id']}.png"

        # Append payload bytes after file
        original = clean_path.read_bytes()
        encoded_path.write_bytes(original + payload.encode())
        result["evidence"]["payload"] = payload

        pre_fp = _file_fingerprint(encoded_path)
        result["evidence"]["pre"] = pre_fp

        if self.dry_run:
            result["verdict"] = "SKIPPED"
            return

        upload_resp = self.client.upload_file(str(encoded_path), title=encoded_path.name)
        file_id = upload_resp["files"][0]["id"]
        result["evidence"]["send_response"] = {"file_id": file_id}

        raw_bytes, meta = self.client.download_file(file_id)
        retrieved_path = RETRIEVED_DIR / f"{cell['id']}.png"
        retrieved_path.write_bytes(raw_bytes)
        post_fp = _file_fingerprint(retrieved_path)
        result["evidence"]["post"] = post_fp

        # Check if trailer survived
        trailer_survives = payload.encode() in raw_bytes
        result["evidence"]["trailer_survives"] = trailer_survives

        verdict, details = _classify(pre_fp, post_fp, cell["technique"], retrieved_path)
        details["trailer_survives"] = trailer_survives
        trailer_bytes = len(payload.encode())
        size_delta = post_fp["size"] - pre_fp["size"]
        if verdict != "SURVIVES" and trailer_survives:
            verdict = "DEGRADED"
        elif not trailer_survives and size_delta == -trailer_bytes:
            # Trailer gone; carrier shrank by exactly the trailer length.
            # That's Slack removing the appended bytes and passing the
            # underlying carrier through untouched — textbook STRIPPED,
            # not RECODED. (A JPEG re-encode would show |delta| >> trailer.)
            verdict = "STRIPPED"
        result["verdict"] = verdict
        result["evidence"]["classification"] = details

    def _handle_image_specter(self, cell: dict, result: dict) -> None:
        """Wave 6: SPECTER encode → upload → download → try decode."""
        cfg = cell.get("encode_config", {})
        clean_path = CLEAN_DIR / cfg.get("clean_input", "probe_150x150.png")
        self._ensure_clean_png_present(clean_path)

        payload = _make_payload(cell["technique"], self.timestamp)
        encoded_path = ENCODED_DIR / f"{cell['id']}.png"

        r = _run_stegg("specter", "encode",
                       "-i", str(clean_path),
                       "-o", str(encoded_path),
                       "-t", payload,
                       "-p", "testpass")
        result["evidence"]["encode"] = {"stdout": r.stdout, "stderr": r.stderr}
        result["evidence"]["payload"] = payload

        pre_fp = _file_fingerprint(encoded_path)
        result["evidence"]["pre"] = pre_fp

        if self.dry_run:
            result["verdict"] = "SKIPPED"
            return

        upload_resp = self.client.upload_file(str(encoded_path), title=encoded_path.name)
        file_id = upload_resp["files"][0]["id"]
        result["evidence"]["send_response"] = {"file_id": file_id}

        raw_bytes, meta = self.client.download_file(file_id)
        retrieved_path = RETRIEVED_DIR / f"{cell['id']}.png"
        retrieved_path.write_bytes(raw_bytes)
        post_fp = _file_fingerprint(retrieved_path)
        result["evidence"]["post"] = post_fp

        decode_ok = False
        try:
            r2 = _run_stegg("specter", "decode", "-i", str(retrieved_path))
            decode_ok = payload in r2.stdout
            result["evidence"]["decode"] = {"ok": decode_ok}
        except Exception as e:
            result["evidence"]["decode"] = {"ok": False, "error": str(e)}

        verdict, details = _classify(pre_fp, post_fp, cell["technique"], retrieved_path)
        if decode_ok:
            details["payload_survives_decode"] = True
        result["verdict"] = verdict
        result["evidence"]["classification"] = details

    def _handle_image_matryoshka(self, cell: dict, result: dict) -> None:
        """Wave 6: Matryoshka embed → upload → download → try extract."""
        cfg = cell.get("encode_config", {})
        clean_path = CLEAN_DIR / cfg.get("clean_input", "probe_150x150.png")
        self._ensure_clean_png_present(clean_path)

        payload = _make_payload(cell["technique"], self.timestamp)
        payload_path = ENCODED_DIR / f"{cell['id']}_payload.bin"
        payload_path.write_text(payload)
        encoded_path = ENCODED_DIR / f"{cell['id']}.png"

        # matryoshka embed uses -p (payload file) and -c (carrier images)
        r = _run_stegg("matryoshka", "embed",
                       "-p", str(payload_path),
                       "-c", str(clean_path),
                       "-o", str(encoded_path))
        result["evidence"]["encode"] = {"stdout": r.stdout, "stderr": r.stderr}
        result["evidence"]["payload"] = payload

        pre_fp = _file_fingerprint(encoded_path)
        result["evidence"]["pre"] = pre_fp

        if self.dry_run:
            result["verdict"] = "SKIPPED"
            return

        upload_resp = self.client.upload_file(str(encoded_path), title=encoded_path.name)
        file_id = upload_resp["files"][0]["id"]
        result["evidence"]["send_response"] = {"file_id": file_id}

        raw_bytes, meta = self.client.download_file(file_id)
        retrieved_path = RETRIEVED_DIR / f"{cell['id']}.png"
        retrieved_path.write_bytes(raw_bytes)
        post_fp = _file_fingerprint(retrieved_path)
        result["evidence"]["post"] = post_fp

        decode_ok = False
        try:
            # matryoshka extract takes image as positional arg
            r2 = _run_stegg("matryoshka", "extract", str(retrieved_path))
            decode_ok = payload in r2.stdout
            result["evidence"]["decode"] = {"ok": decode_ok, "stdout": r2.stdout[:500]}
        except Exception as e:
            result["evidence"]["decode"] = {"ok": False, "error": str(e)}

        verdict, details = _classify(pre_fp, post_fp, cell["technique"], retrieved_path)
        if decode_ok:
            details["payload_survives_decode"] = True
        result["verdict"] = verdict
        result["evidence"]["classification"] = details

    def _handle_text_stego(self, cell: dict, result: dict) -> None:
        """Wave 2/3/5: text stego → post message → retrieve → verify.

        Verdict semantics for text stego:
          SURVIVES  = payload extracted successfully from retrieved text
          DEGRADED  = bytes preserved but decoder can't recover the payload
          RECODED   = bytes changed (Slack normalized something)
        """
        cfg = cell.get("encode_config", {})
        method = cfg["method"]

        # Cover/payload resolution + capacity gate lives outside the
        # handler so text_stego and text_snippet share the same policy.
        # Raises ProbeConfigError before we touch Slack if the cell is
        # mis-sized.
        cover, payload = _resolve_text_cover_and_payload(cell, cell["technique"], self.timestamp)
        cover_path = CLEAN_DIR / f"cover_{cell['id']}.txt"
        cover_path.write_text(cover)
        result["evidence"]["cover_len_chars"] = len(cover)

        # Encode. If this raises SteggCLIError, run_cell lets it propagate
        # and the whole run aborts — encode failure is a probe-config bug,
        # not a Slack transport verdict.
        encoded_text = _run_stegg_text(
            "text", "encode",
            "-m", method,
            "-c", str(cover_path),
            "-s", payload,
        )
        result["evidence"]["payload"] = payload
        result["evidence"]["encoded_text"] = encoded_text
        result["evidence"]["encoded_len_chars"] = len(encoded_text)
        pre_fp = {"sha256": _sha256(encoded_text.encode()), "size": len(encoded_text.encode()), "exists": True}
        result["evidence"]["pre"] = pre_fp

        if self.dry_run:
            result["verdict"] = "SKIPPED"
            return

        # Refuse to send text whose wire-form-expanded length will exceed
        # Slack's ~4000-char message store ceiling. Cells whose method
        # expands per-codepoint on the wire (emoji, skintone) must specify
        # a small enough payload_bytes to keep the estimated wire length
        # under SLACK_MSG_STORE_LIMIT_CHARS.
        wire_len = _estimate_wire_chars(encoded_text, method)
        result["evidence"]["estimated_wire_chars"] = wire_len
        if wire_len > SLACK_MSG_STORE_LIMIT_CHARS:
            raise ProbeConfigError(
                f"cell {cell.get('id')}: encoded_text is {len(encoded_text)} chars "
                f"but expands to ~{wire_len} chars on the wire (method={method}) "
                f"— exceeds Slack's ~{SLACK_MSG_STORE_LIMIT_CHARS} char storage limit. "
                f"Reduce payload_bytes for this cell."
            )

        # Round-trip through Slack
        msg = self.client.post_message(encoded_text)
        ts = msg["ts"]
        result["evidence"]["send_response"] = {"ts": ts}

        retrieved_text = self.client.get_message_text(ts)
        result["evidence"]["retrieved_text"] = retrieved_text
        post_fp = {"sha256": _sha256(retrieved_text.encode()), "size": len(retrieved_text.encode()), "exists": True}
        result["evidence"]["post"] = post_fp

        self.client.delete_message(ts)

        retrieved_path = RETRIEVED_DIR / f"{cell['id']}.txt"
        retrieved_path.write_text(retrieved_text)

        details: dict[str, Any] = {"pre": pre_fp, "post": post_fp}
        details["text_match"] = (encoded_text == retrieved_text)
        details["len_delta"] = len(retrieved_text) - len(encoded_text)

        # For text stego, "SURVIVES" means the payload actually decodes
        # from the retrieved text — NOT that the bytes happen to match.
        # A byte-identical round-trip whose payload no longer decodes is
        # DEGRADED. A decode failure on the retrieved text is a transport
        # verdict (Slack ate something meaningful), not a harness error,
        # so we catch it here and don't re-raise.
        try:
            decoded = _run_stegg_text(
                "text", "decode",
                "-m", method,
                "-i", str(retrieved_path),
            )
            payload_survives = payload in decoded
            details["payload_survives_decode"] = payload_survives
            result["evidence"]["decode"] = {"ok": payload_survives, "output": decoded[:200]}
        except SteggCLIError as e:
            payload_survives = False
            details["payload_survives_decode"] = False
            result["evidence"]["decode"] = {"ok": False, "error": str(e)}

        # Truncation detection: if we retrieved a strict prefix of what we
        # sent (or the retrieved is >= ~5% shorter and starts with the
        # encoded prefix), Slack cut the message mid-content. That's a
        # transport verdict distinct from RECODED (which implies canonicalization).
        # Order matters: check TRUNCATED before falling through to RECODED.
        is_prefix = encoded_text.startswith(retrieved_text) and len(retrieved_text) < len(encoded_text)
        significantly_shorter = len(retrieved_text) < len(encoded_text) * 0.95
        details["truncation_suspected"] = is_prefix or significantly_shorter

        if payload_survives:
            verdict = "SURVIVES"
        elif details["text_match"]:
            verdict = "DEGRADED"
        elif is_prefix or significantly_shorter:
            verdict = "TRUNCATED"
        else:
            verdict = "RECODED"

        result["verdict"] = verdict
        result["evidence"]["classification"] = details

    def _handle_text_transform(self, cell: dict, result: dict) -> None:
        """Wave 5: text transform → post → retrieve → check survival."""
        cfg = cell.get("encode_config", {})
        transform = cfg["transform"]  # "zalgo" or "leet"
        intensity = cfg.get("intensity")

        # Generate input text
        input_text = f"ST3GG transport test: {cell['technique']} {_rand_id(8)} " * 3

        # Apply transform
        if transform == "zalgo":
            args = ["inject", "zalgo", input_text]
            if intensity:
                args.insert(2, "--intensity")
                args.insert(3, str(intensity))
            encoded_text = _run_stegg_text(*args)
        elif transform == "leet":
            args = ["inject", "leet", input_text]
            if intensity:
                args.insert(2, "--intensity")
                args.insert(3, str(intensity))
            encoded_text = _run_stegg_text(*args)
        else:
            encoded_text = input_text

        result["evidence"]["input_text"] = input_text
        result["evidence"]["encoded_text"] = encoded_text
        pre_fp = {"sha256": _sha256(encoded_text.encode()), "size": len(encoded_text.encode()), "exists": True}
        result["evidence"]["pre"] = pre_fp

        if self.dry_run:
            result["verdict"] = "SKIPPED"
            return

        msg = self.client.post_message(encoded_text)
        ts = msg["ts"]
        result["evidence"]["send_response"] = {"ts": ts}

        retrieved_text = self.client.get_message_text(ts)
        result["evidence"]["retrieved_text"] = retrieved_text
        post_fp = {"sha256": _sha256(retrieved_text.encode()), "size": len(retrieved_text.encode()), "exists": True}
        result["evidence"]["post"] = post_fp

        self.client.delete_message(ts)

        retrieved_path = RETRIEVED_DIR / f"{cell['id']}.txt"
        retrieved_path.write_text(retrieved_text)

        verdict, details = _classify(pre_fp, post_fp, cell["technique"], retrieved_path)
        details["text_match"] = (encoded_text == retrieved_text)
        details["len_delta"] = len(retrieved_text) - len(encoded_text)
        result["verdict"] = verdict
        result["evidence"]["classification"] = details

    def _handle_text_snippet(self, cell: dict, result: dict) -> None:
        """Wave 5: text stego → upload as snippet → download → verify.

        Same verdict semantics as _handle_text_stego — SURVIVES requires
        the payload to actually decode from the retrieved snippet bytes."""
        cfg = cell.get("encode_config", {})
        method = cfg["method"]

        # Cover/payload resolution + capacity gate lives outside the
        # handler so text_stego and text_snippet share the same policy.
        # Raises ProbeConfigError before we touch Slack if the cell is
        # mis-sized.
        cover, payload = _resolve_text_cover_and_payload(cell, cell["technique"], self.timestamp)
        cover_path = CLEAN_DIR / f"cover_{cell['id']}.txt"
        cover_path.write_text(cover)
        result["evidence"]["cover_len_chars"] = len(cover)

        # If encode fails, run_cell lets SteggCLIError propagate — fail loud.
        encoded_text = _run_stegg_text(
            "text", "encode",
            "-m", method,
            "-c", str(cover_path),
            "-s", payload,
        )
        result["evidence"]["payload"] = payload
        result["evidence"]["encoded_text"] = encoded_text

        snippet_path = ENCODED_DIR / f"{cell['id']}.txt"
        snippet_path.write_text(encoded_text)
        pre_fp = _file_fingerprint(snippet_path)
        result["evidence"]["pre"] = pre_fp

        if self.dry_run:
            result["verdict"] = "SKIPPED"
            return

        upload_resp = self.client.upload_snippet(str(snippet_path), title=snippet_path.name, snippet_type="text")
        file_id = upload_resp["files"][0]["id"]
        result["evidence"]["send_response"] = {"file_id": file_id}

        raw_bytes, meta = self.client.download_file(file_id)
        retrieved_path = RETRIEVED_DIR / f"{cell['id']}.txt"
        retrieved_path.write_bytes(raw_bytes)
        post_fp = _file_fingerprint(retrieved_path)
        result["evidence"]["post"] = post_fp

        # Empty retrieval on a non-empty upload is a hard API failure, not
        # a classification. Bail before running the decoder on zero bytes.
        if pre_fp["size"] > 0 and post_fp["size"] == 0:
            result["verdict"] = "API_ERROR"
            result["evidence"]["classification"] = {
                "pre": pre_fp, "post": post_fp,
                "error": "snippet download returned 0 bytes for non-empty upload",
                "file_id": file_id,
                "file_meta": {k: meta.get(k) for k in ("id", "size", "url_private_download", "mimetype", "filetype") if k in meta},
            }
            return

        details: dict[str, Any] = {"pre": pre_fp, "post": post_fp}
        details["text_match"] = (encoded_text.encode() == raw_bytes)
        details["size_delta"] = post_fp["size"] - pre_fp["size"]

        # SURVIVES requires payload_survives_decode. Decode failure on
        # retrieved content is a transport verdict, not a probe bug.
        try:
            decoded = _run_stegg_text(
                "text", "decode",
                "-m", method,
                "-i", str(retrieved_path),
            )
            payload_survives = payload in decoded
            details["payload_survives_decode"] = payload_survives
            result["evidence"]["decode"] = {"ok": payload_survives, "output": decoded[:200]}
        except SteggCLIError as e:
            payload_survives = False
            details["payload_survives_decode"] = False
            result["evidence"]["decode"] = {"ok": False, "error": str(e)}

        if payload_survives:
            verdict = "SURVIVES"
        elif details["text_match"]:
            verdict = "DEGRADED"
        else:
            verdict = "RECODED"

        result["verdict"] = verdict
        result["evidence"]["classification"] = details

    def _handle_generic(self, cell: dict, result: dict) -> None:
        """Catch-all for cell types without a dedicated handler."""
        result["verdict"] = "SKIPPED"
        result["error"] = f"No handler for category: {cell['category']}"

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _ensure_clean_png_present(self, path: Path) -> None:
        if not path.exists():
            from PIL import Image
            img = Image.new("RGB", (150, 150))
            random.seed(42)
            pixels = img.load()
            for x in range(150):
                for y in range(150):
                    pixels[x, y] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            path.parent.mkdir(parents=True, exist_ok=True)
            img.save(str(path))

    def _ensure_clean_jpg_present(self, path: Path) -> None:
        if not path.exists():
            from PIL import Image
            img = Image.new("RGB", (150, 150))
            random.seed(42)
            pixels = img.load()
            for x in range(150):
                for y in range(150):
                    pixels[x, y] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            path.parent.mkdir(parents=True, exist_ok=True)
            img.save(str(path), quality=85)

    def _ensure_clean_probe(self, cell_id: str, fmt: dict) -> Path:
        """Generate a clean format probe file if it doesn't exist."""
        ext = fmt.get("ext", "bin")
        mode = fmt.get("mode", "RGB")
        img_type = fmt.get("type", "png")
        path = CLEAN_DIR / f"{cell_id}.{ext}"

        if path.exists():
            return path

        from PIL import Image, ImageDraw

        if img_type == "png":
            if mode in ("RGB", "RGBA", "L", "P"):
                img = Image.new(mode, (150, 150))
                random.seed(42)
                if mode in ("RGB", "RGBA"):
                    pixels = img.load()
                    for x in range(150):
                        for y in range(150):
                            v = tuple(random.randint(0, 255) for _ in range(len(mode)))
                            pixels[x, y] = v
                elif mode == "L":
                    pixels = img.load()
                    for x in range(150):
                        for y in range(150):
                            pixels[x, y] = random.randint(0, 255)
                elif mode == "P":
                    # Palette mode — put some colors in
                    random.seed(42)
                    img = Image.new("RGB", (150, 150)).convert("P")
                img.save(str(path))
            else:
                img = Image.new("RGB", (150, 150))
                img.save(str(path))

        elif img_type == "jpeg":
            img = Image.new("RGB", (150, 150))
            random.seed(42)
            pixels = img.load()
            for x in range(150):
                for y in range(150):
                    pixels[x, y] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            quality = fmt.get("quality", 85)
            img.save(str(path), quality=quality)

        elif img_type == "gif":
            img = Image.new("RGB", (150, 150))
            random.seed(42)
            pixels = img.load()
            for x in range(150):
                for y in range(150):
                    pixels[x, y] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            img.save(str(path), format="GIF")

        elif img_type == "webp":
            img = Image.new("RGB", (150, 150))
            random.seed(42)
            pixels = img.load()
            for x in range(150):
                for y in range(150):
                    pixels[x, y] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            img.save(str(path), format="WebP")

        elif img_type == "bmp":
            img = Image.new("RGB", (150, 150))
            random.seed(42)
            pixels = img.load()
            for x in range(150):
                for y in range(150):
                    pixels[x, y] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            img.save(str(path), format="BMP")

        elif img_type == "tiff":
            from PIL import TiffImagePlugin
            img = Image.new("RGB", (150, 150))
            random.seed(42)
            pixels = img.load()
            for x in range(150):
                for y in range(150):
                    pixels[x, y] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            img.save(str(path), format="TIFF")

        elif img_type == "svg":
            svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="150" height="150"><rect width="150" height="150" fill="#808080"/><text x="10" y="80" font-size="12">ST3GG probe {_rand_id(8)}</text></svg>'
            path.write_text(svg)

        elif img_type == "text":
            lines = []
            if fmt.get("bom"):
                lines.append("﻿")
            ending = "\r\n" if fmt.get("line_ending") == "crlf" else "\n"
            for i in range(10):
                line = f"ST3GG format probe line {i} — {_rand_id(8)}"
                if fmt.get("null_bytes") and i == 5:
                    line += "\x00NULL_HERE\x00"
                lines.append(line)
            text = ending.join(lines) + ending
            path.write_text(text, encoding="utf-8")

        else:
            # Generic binary — just random bytes
            path.write_bytes(os.urandom(1024))

        print(f"  Generated clean probe: {path}")
        return path

    def _try_lsb_decode(self, retrieved_path: Path, channels: str, bits: int,
                        strategy: str, seed: int | None, payload: str) -> bool:
        """Try to decode LSB from a retrieved file. Returns True if payload found."""
        try:
            decode_args = [
                "decode-cmd", "-i", str(retrieved_path),
                "--channels", channels, "--bits", str(bits), "--strategy", strategy,
            ]
            if seed is not None:
                decode_args.extend(["--seed", str(seed)])
            r = _run_stegg(*decode_args)
            return payload in r.stdout
        except Exception:
            return False

    def _print_verdict(self, result: dict) -> None:
        v = result["verdict"]
        expected = result.get("expect", "?")
        marker = ""
        if v == expected:
            marker = " ✓"
        elif expected and expected != "UNKNOWN" and v != expected and v != "SKIPPED":
            marker = " ✗ UNEXPECTED"
        icon = {"SURVIVES": "🟢", "STRIPPED": "🟡", "RECODED": "🟠",
                "DEGRADED": "🔴", "CARRIER_DESTROYED": "💀",
                "API_ERROR": "❌", "SKIPPED": "⏭️"}.get(v, "❓")
        print(f"  {icon} {v}  (expected: {expected}){marker}")


# ---------------------------------------------------------------------------
# matrix loading
# ---------------------------------------------------------------------------

def load_matrix(path: Path) -> dict:
    """Load matrix JSON. Returns {waves: {N: {label, cells: [...]}, ...}}."""
    with open(path) as f:
        data = json.load(f)

    # Support both flat list and nested wave format
    if isinstance(data, list):
        # Flat list — wrap in a single wave
        return {"1": {"label": "All cells", "cells": data}}

    # Nested format: {"waves": {"1": {...}, "2": {...}}}
    waves = data.get("waves", data)
    for wkey, wave in waves.items():
        for cell in wave.get("cells", []):
            cell["wave"] = int(wkey)
    return waves


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Slack Transport Survivability Test Harness")
    parser.add_argument("--all", action="store_true", help="Run all waves")
    parser.add_argument("--wave", type=int, nargs="+", help="Run specific wave(s)")
    parser.add_argument("--cell", type=str, nargs="+", help="Run specific cell ID(s)")
    parser.add_argument("--dry-run", action="store_true", help="Validate matrix, skip Slack API calls")
    parser.add_argument("--gen-probes-only", action="store_true", help="Generate clean probes and exit")
    parser.add_argument("--gen-ui-kit", action="store_true", help="Generate manual UI clipboard comparison kit")
    parser.add_argument("--secrets", type=str, default=str(SECRETS_PATH), help="Path to secrets JSON")
    parser.add_argument("--matrix", type=str, default=str(MATRIX_PATH), help="Path to matrix JSON")
    parser.add_argument("--results", type=str, default=str(RESULTS_PATH), help="Path to output results JSON")
    args = parser.parse_args()

    # Load matrix
    if not Path(args.matrix).exists():
        print(f"ERROR: Matrix file not found: {args.matrix}")
        print("Run with --gen-matrix to generate a default matrix, or create one manually.")
        sys.exit(1)

    waves = load_matrix(Path(args.matrix))
    all_waves = sorted(waves.keys(), key=lambda w: int(w))

    # Determine which cells to run
    cells_to_run: list[dict] = []

    if args.cell:
        all_cells = [c for w in all_waves for c in waves[w].get("cells", [])]
        by_id = {c["id"]: c for c in all_cells}
        for cid in args.cell:
            if cid in by_id:
                cells_to_run.append(by_id[cid])
            else:
                print(f"WARNING: cell '{cid}' not found in matrix — skipping")
    elif args.wave:
        for w in args.wave:
            wk = str(w)
            if wk in waves:
                wave_cells = waves[wk].get("cells", [])
                cells_to_run.extend(wave_cells)
                print(f"Wave {w}: {len(wave_cells)} cells")
            else:
                print(f"WARNING: wave {w} not found in matrix — skipping")
    elif args.all or args.gen_probes_only or args.gen_ui_kit:
        # --all, --gen-probes-only, and --gen-ui-kit all need the full matrix
        for w in all_waves:
            wave_cells = waves[w].get("cells", [])
            cells_to_run.extend(wave_cells)
            print(f"Wave {w}: {len(wave_cells)} cells")
    else:
        print("Specify --all, --wave N, --cell <id>, --gen-probes-only, or --gen-ui-kit")
        sys.exit(1)

    print(f"\nTotal cells to run: {len(cells_to_run)}")

    if args.gen_probes_only:
        harness = SlackTransportHarness({}, dry_run=True)
        for cell in cells_to_run:
            if cell.get("category") == "format_probe":
                fmt = cell.get("format", {})
                harness._ensure_clean_probe(cell["id"], fmt)
        print("Clean probes generated. Exiting.")
        return

    if args.gen_ui_kit:
        _generate_ui_kit(cells_to_run)
        return

    # Load secrets (unless dry run)
    secrets = {}
    if not args.dry_run:
        secrets_path = Path(args.secrets)
        if not secrets_path.exists():
            print(f"ERROR: Secrets file not found: {args.secrets}")
            print("Create it at tests/transport/secrets_slack.json with bot_token and channel_id.")
            sys.exit(1)
        with open(secrets_path) as f:
            secrets = json.load(f)

    harness = SlackTransportHarness(secrets, dry_run=args.dry_run)

    # Group cells by wave for display
    wave_groups: dict[str, list[dict]] = {}
    for c in cells_to_run:
        w = str(c.get("wave", "?"))
        wave_groups.setdefault(w, []).append(c)

    all_results = []
    for wk in sorted(wave_groups.keys(), key=lambda w: int(w)):
        wcells = wave_groups[wk]
        label = waves.get(wk, {}).get("label", f"Wave {wk}")
        print(f"\n{'='*60}")
        print(f"WAVE {wk}: {label}")
        print(f"{'='*60}")
        results = harness.run(wcells, wave_label=label)
        all_results.extend(results)

    # Write results
    results_doc = {
        "generated": _now_iso(),
        "transport": "slack",
        "total_cells": len(all_results),
        "verdicts": _count_verdicts(all_results),
        "results": all_results,
    }

    results_path = Path(args.results)
    print(f"\n{'='*60}")
    if args.dry_run:
        # Dry-runs produce only SKIPPED verdicts — writing them would
        # clobber real prior results with meaningless data.
        print(f"DRY-RUN: skipping write to {results_path}")
    else:
        results_path.write_text(json.dumps(results_doc, indent=2, default=str))
        print(f"RESULTS WRITTEN: {results_path}")

    # Summary
    vc = _count_verdicts(all_results)
    print(f"\nVERDICT SUMMARY:")
    for v in VERDICTS:
        if vc.get(v, 0) > 0:
            print(f"  {v}: {vc[v]}")

    # Unexpected results
    unexpected = [r for r in all_results if r.get("expect") and r.get("expect") != "UNKNOWN"
                  and r["verdict"] != r["expect"] and r["verdict"] != "SKIPPED"]
    if unexpected:
        print(f"\n⚠️  UNEXPECTED RESULTS ({len(unexpected)}):")
        for r in unexpected:
            print(f"  {r['id']}: got {r['verdict']}, expected {r['expect']}")


def _count_verdicts(results: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in results:
        v = r.get("verdict", "UNKNOWN")
        counts[v] = counts.get(v, 0) + 1
    return counts


def _generate_ui_kit(cells: list[dict]) -> None:
    """Generate the manual UI clipboard comparison kit (Section 8)."""
    ui_dir = PROBE_DIR / "ui_kit"
    paste_dir = ui_dir / "paste_these"
    retrieve_dir = ui_dir / "retrieve_here"
    for d in (ui_dir, paste_dir, retrieve_dir):
        d.mkdir(parents=True, exist_ok=True)

    # Only text_stego cells are relevant for UI
    text_cells = [c for c in cells if c.get("category") in ("text_stego", "text_transform")]

    # Pick 5-6 representative ones
    representative = text_cells[:6]

    readme = ui_dir / "README.txt"
    lines = [
        "SLACK UI CLIPBOARD COMPARISON KIT",
        "===================================",
        "",
        "This kit tests whether the Slack web UI clipboard path preserves",
        "stego text the same way the API path does.",
        "",
        "INSTRUCTIONS:",
        "",
        "For each file in paste_these/:",
        "  1. Open the file in a text editor",
        "  2. Select ALL text (Cmd+A)",
        "  3. Copy (Cmd+C)",
        "  4. Paste into the Slack #stegg-transport-tests channel web UI",
        "  5. Send the message",
        "  6. Select the sent message text in Slack",
        "  7. Copy (Cmd+C)",
        "  8. Paste into the corresponding file in retrieve_here/",
        "     (filename is printed inside each paste_these file)",
        "",
        "Then run:",
        "  python tests/transport/test_slack.py --verify-ui-kit",
        "",
        f"Generated: {_now_iso()}",
        f"Number of test files: {len(representative)}",
    ]
    readme.write_text("\n".join(lines))

    for i, cell in enumerate(representative, 1):
        num = f"{i:02d}"
        payload = _make_payload(cell["technique"], _now_iso().replace(":", "-"))

        # Generate stego text
        cfg = cell.get("encode_config", {})
        if cell["category"] == "text_stego":
            method = cfg["method"]
            cover = cfg.get("cover_text", "The quick brown fox jumps over the lazy dog. " * 3)
            cover_path = paste_dir / f"{num}_cover.txt"
            cover_path.write_text(cover)
            try:
                encoded = _run_stegg_text(
                    "text", "encode", "-m", method,
                    "-c", str(cover_path), "-s", payload,
                )
            except Exception:
                encoded = f"ERROR encoding: {cell['id']}"
        elif cell["category"] == "text_transform":
            transform = cfg.get("transform", "zalgo")
            input_text = f"ST3GG UI test: {cell['technique']} "
            if transform == "zalgo":
                encoded = _run_stegg_text("inject", "zalgo", input_text)
            else:
                encoded = _run_stegg_text("inject", "leet", input_text)
        else:
            encoded = f"UNSUPPORTED: {cell['id']}"

        paste_file = paste_dir / f"{num}_{cell['id']}.txt"
        paste_file.write_text(
            f"# UI KIT TEST {num}\n"
            f"# Technique: {cell['technique']}\n"
            f"# Cell ID: {cell['id']}\n"
            f"# Retrieve to: retrieve_here/{num}_{cell['id']}_retrieved.txt\n"
            f"# --- COPY EVERYTHING BELOW THIS LINE ---\n"
            f"{encoded}"
        )

    print(f"UI kit generated: {ui_dir}")
    print(f"  {len(representative)} text files in paste_these/")
    print(f"  README: {readme}")


if __name__ == "__main__":
    main()
