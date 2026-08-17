"""End-to-end tests for :class:`f5_core.F5Stegg`.

The acceptance bar for the stegg dialect: pinned JS-embed fixtures
(``tests/unit/fixtures/f5/jpeg/``) must extract byte-exact under the
Python port.  These are the "F5Stegg is byte-compatible with the JS
library" claim in one direction (JS-write → Python-read); the reverse
direction is covered by Python round-trip tests here plus an optional
Node-interop test that runs when ``node`` is available.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

pytest.importorskip("jpeglib")

from m3gast3gg.core.f5 import CapacityExceeded, F5Stegg


FIX_DIR = Path(__file__).parent / "fixtures" / "f5" / "jpeg"


# ---------- Python round-trip ------------------------------------------

@pytest.fixture(scope="module")
def clean_jpeg_bytes() -> bytes:
    """Generate a fixed-seed JPEG with non-trivial DCT coefficients."""
    rng = np.random.RandomState(42)
    pixels = rng.randint(0, 256, (128, 128, 3), dtype=np.uint8)
    img = Image.fromarray(pixels)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


@pytest.mark.parametrize("payload", [
    b"A",
    b"Hello, F5Stegg!",
    b"binary\x00\xff\x01\x02\x03bytes",
    b"x" * 500,
])
def test_python_roundtrip(clean_jpeg_bytes, payload):
    s = F5Stegg(b"\x01\x02\x03\x04")
    stego = s.embed(clean_jpeg_bytes, payload)
    got = s.extract(stego)
    assert got == payload


def test_str_key_rejected():
    with pytest.raises(TypeError, match="bytes key"):
        F5Stegg("password")  # type: ignore[arg-type]


def test_empty_key_rejected():
    with pytest.raises(ValueError):
        F5Stegg(b"")


def test_wrong_key_does_not_recover_payload(clean_jpeg_bytes):
    s1 = F5Stegg(b"correct-key")
    s2 = F5Stegg(b"wrong-key!!")
    stego = s1.embed(clean_jpeg_bytes, b"secret")

    from m3gast3gg.core.f5 import ExtractionFailed

    try:
        got = s2.extract(stego)
    except ExtractionFailed:
        return  # good: obvious failure
    # Or: extract might return a garbage byte string that happens to
    # decode.  Either way, it must not equal the real payload.
    assert got != b"secret"


def test_analyze_returns_capacity_list(clean_jpeg_bytes):
    s = F5Stegg(b"key")
    info = s.analyze(clean_jpeg_bytes)
    assert isinstance(info["capacity"], list)
    assert len(info["capacity"]) == 17
    assert info["capacity"][1] > 0  # any real JPEG has k=1 capacity


def test_capacity_exceeded_raises(clean_jpeg_bytes):
    s = F5Stegg(b"key")
    # Try to embed way more than clean.jpg can hold.
    huge = b"x" * 100_000
    with pytest.raises(CapacityExceeded):
        s.embed(clean_jpeg_bytes, huge)


# ---------- JS-embed → Python-extract (pinned fixtures) ----------------

def _iter_pinned():
    manifest_path = FIX_DIR / "manifest.json"
    if not manifest_path.exists():
        pytest.skip(
            f"missing fixture manifest at {manifest_path}; "
            "regenerate with node scripts/gen_f5_stegg_jpeg_fixtures.js"
        )
    manifest = json.loads(manifest_path.read_text())
    return [(c["label"], c) for c in manifest["cases"]]


@pytest.mark.parametrize("label, case", _iter_pinned())
def test_extracts_pinned_js_embed(label, case):
    """JS-embedded blob → F5Stegg.extract → payload bytes match.

    This is *the* interop test — if this passes, the port is
    bit-compatible with the JS library for extraction, on real JPEGs
    with real jpeglib IO.
    """
    blob = (FIX_DIR / case["blob"]).read_bytes()
    key = bytes.fromhex(case["key_hex"])
    expected = bytes.fromhex(case["payload_hex"])

    s = F5Stegg(key)
    got = s.extract(blob)
    assert got == expected, (
        f"{label}: extract drifted from JS embed; "
        f"expected {expected!r}, got {got!r}"
    )


# Python → JS interop test retired with f5stego-lib.js (Phase 5).
# Pinned fixture tests in this file cover JS→Python interop.
