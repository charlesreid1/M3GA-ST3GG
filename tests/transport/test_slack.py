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


def _make_payload(technique: str, timestamp: str) -> str:
    """Deterministic-but-unique payload per cell."""
    rand = _rand_id(8)
    inner = f"{PAYLOAD_PREFIX}|{technique}|{timestamp}|{rand}"
    # pad to min 128 bytes to exercise real stego paths
    pad = "P" * max(0, 128 - len(inner))
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


def _run_stegg_text(*args: str, timeout: float = 15.0) -> str:
    """Run stegg and return stdout stripped. Doesn't use --json (text output)."""
    cmd = [sys.executable, str(REPO_ROOT / "cli.py"), "--quiet", *args]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(REPO_ROOT))
    return r.stdout.strip()


# ---------------------------------------------------------------------------
# classification
# ---------------------------------------------------------------------------

VERDICTS = [
    "SURVIVES",           # byte-identical, payload intact
    "STRIPPED",           # metadata removed but carrier intact
    "RECODED",            # file re-encoded, carrier format changed
    "DEGRADED",           # partial damage
    "CARRIER_DESTROYED",  # file unreadable / format corrupted
    "API_ERROR",          # Slack API rejected or failed
    "SKIPPED",            # test not run (dry run, missing dep, etc.)
]

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
        """Run a list of cells. Returns results list."""
        total = len(cells)
        for i, cell in enumerate(cells, 1):
            print(f"\n{'─'*60}")
            print(f"[{i}/{total}] {cell['id']}  ({cell.get('description', '')})")
            print(f"  transport={cell['transport']}  technique={cell['technique']}  expect={cell.get('expect','?')}")
            result = self.run_cell(cell)
            self.results.append(result)
            self._print_verdict(result)
        return self.results

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
        except Exception as e:
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

        # Check chunk presence on retrieved
        try:
            r2 = _run_stegg("chunks", str(retrieved_path))
            chunks_data = json.loads(r2.stdout) if r2.stdout else {}
        except Exception:
            chunks_data = {"error": str(r2.stderr)}
        result["evidence"]["chunks_post"] = chunks_data

        verdict, details = _classify(pre_fp, post_fp, cell["technique"], retrieved_path)
        # Override: if hashes differ, it's definitely STRIPPED
        if verdict != "SURVIVES":
            verdict = "STRIPPED"
        result["verdict"] = verdict
        result["evidence"]["classification"] = details

    def _handle_image_exif(self, cell: dict, result: dict) -> None:
        """Wave 3: inject EXIF → upload → download → check metadata."""
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

        verdict, details = _classify(pre_fp, post_fp, cell["technique"], retrieved_path)
        if verdict != "SURVIVES":
            verdict = "STRIPPED"
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
        if decode_ok:
            details["payload_survives_decode"] = True
            if verdict == "RECODED":
                verdict = "DEGRADED"  # re-encoded but payload survives
        result["verdict"] = verdict
        result["evidence"]["classification"] = details

    def _handle_image_jsteg(self, cell: dict, result: dict) -> None:
        """Wave 4: JSteg JPEG encode → upload → download → try decode."""
        cfg = cell.get("encode_config", {})
        clean_name = cfg.get("clean_input", "probe_150x150.jpg")
        clean_path = CLEAN_DIR / clean_name
        self._ensure_clean_jpg_present(clean_path)

        import f5_core.jsteg as jsteg
        # JSteg limited capacity on small JPEG — use short payload
        payload = f"ST3GG|{cell['technique']}|{_rand_id(4)}".encode()
        encoded_path = ENCODED_DIR / f"{cell['id']}.jpg"

        jpeg_bytes = clean_path.read_bytes()
        encoded_bytes = jsteg.jsteg_encode(jpeg_bytes, payload)
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
        if decode_ok:
            details["payload_survives_decode"] = True
            if verdict == "RECODED":
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
        if verdict != "SURVIVES" and trailer_survives:
            verdict = "DEGRADED"
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
        """Wave 2/3/5: text stego → post message → retrieve → verify."""
        cfg = cell.get("encode_config", {})
        method = cfg["method"]

        # Generate cover text
        cover = cfg.get("cover_text", "The quick brown fox jumps over the lazy dog. " * 3)
        cover_path = CLEAN_DIR / f"cover_{cell['id']}.txt"
        cover_path.write_text(cover)

        payload = _make_payload(cell["technique"], self.timestamp)

        # Encode
        encoded_text = _run_stegg_text(
            "text", "encode",
            "-m", method,
            "-c", str(cover_path),
            "-s", payload,
        )
        result["evidence"]["payload"] = payload
        result["evidence"]["encoded_text"] = encoded_text
        pre_fp = {"sha256": _sha256(encoded_text.encode()), "size": len(encoded_text.encode()), "exists": True}
        result["evidence"]["pre"] = pre_fp

        if self.dry_run:
            result["verdict"] = "SKIPPED"
            return

        # Post to Slack
        msg = self.client.post_message(encoded_text)
        ts = msg["ts"]
        result["evidence"]["send_response"] = {"ts": ts}

        # Retrieve
        retrieved_text = self.client.get_message_text(ts)
        result["evidence"]["retrieved_text"] = retrieved_text
        post_fp = {"sha256": _sha256(retrieved_text.encode()), "size": len(retrieved_text.encode()), "exists": True}
        result["evidence"]["post"] = post_fp

        # Clean up message
        self.client.delete_message(ts)

        # Verify
        retrieved_path = RETRIEVED_DIR / f"{cell['id']}.txt"
        retrieved_path.write_text(retrieved_text)

        verdict, details = _classify(pre_fp, post_fp, cell["technique"], retrieved_path)
        details["text_match"] = (encoded_text == retrieved_text)
        details["len_delta"] = len(retrieved_text) - len(encoded_text)

        # Try decode on retrieved text
        decode_ok = False
        try:
            decoded = _run_stegg_text(
                "text", "decode",
                "-m", method,
                "-c", str(retrieved_path),
            )
            decode_ok = payload in decoded
            details["payload_survives_decode"] = decode_ok
            result["evidence"]["decode"] = {"ok": decode_ok, "output": decoded[:200]}
        except Exception as e:
            result["evidence"]["decode"] = {"ok": False, "error": str(e)}

        if decode_ok:
            details["payload_survives_decode"] = True
            if verdict != "SURVIVES":
                verdict = "DEGRADED"
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
        """Wave 5: text stego → upload as snippet → download → verify."""
        cfg = cell.get("encode_config", {})
        method = cfg["method"]

        cover = cfg.get("cover_text", "The quick brown fox jumps over the lazy dog. " * 3)
        cover_path = CLEAN_DIR / f"cover_{cell['id']}.txt"
        cover_path.write_text(cover)

        payload = _make_payload(cell["technique"], self.timestamp)

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

        verdict, details = _classify(pre_fp, post_fp, cell["technique"], retrieved_path)
        details["text_match"] = (encoded_text.encode() == raw_bytes)

        # Try decode
        try:
            decoded = _run_stegg_text(
                "text", "decode",
                "-m", method,
                "-c", str(retrieved_path),
            )
            details["payload_survives_decode"] = payload in decoded
        except Exception:
            details["payload_survives_decode"] = False

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
    results_path.write_text(json.dumps(results_doc, indent=2, default=str))
    print(f"\n{'='*60}")
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
