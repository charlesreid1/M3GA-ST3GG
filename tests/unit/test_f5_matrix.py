"""Parity + round-trip tests for :mod:`f5_core._matrix`."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from m3gast3gg.core.f5._matrix import analyze, embed_coefficients, extract_raw
from m3gast3gg.core.f5._framing import stegg_unframe
from m3gast3gg.core.f5._prng_stegg import StegPRNG


FIX = Path(__file__).parent / "fixtures" / "f5"


# ---------- helpers -----------------------------------------------------

def _xorshift32_stream(seed: int, n: int, dc_zero: bool = False) -> np.ndarray:
    """Same xorshift32 the JS fixture generators use, materialised as
    int16 coefficient array with the same class distribution.

    When ``dc_zero=True`` we force positions ``i % 64 == 0`` to zero,
    matching the JS ``comp.blocks`` layout that ``_matrix`` expects.
    The JS fixture generators DON'T zero DCs (they let xorshift produce
    a value there and rely on embed/analyze to skip them), so JS-parity
    tests keep the raw stream — but our Python round-trip test needs
    dc_zero=True to reflect what a real JPEG's Y-with-DC-cleared looks
    like.
    """
    s = seed & 0xFFFFFFFF
    buf = np.zeros(n, dtype=np.int16)
    for i in range(n):
        s ^= (s << 13) & 0xFFFFFFFF
        s ^= s >> 17
        s ^= (s << 5) & 0xFFFFFFFF
        s &= 0xFFFFFFFF
        if i % 64 == 0:
            if dc_zero:
                buf[i] = 0
                continue
            # int16 wraparound from low 16 bits
            buf[i] = np.int16((s & 0xFFFF) - 0x8000)
            continue
        roll = s % 100
        if roll < 60:
            v = 0
        elif roll < 85:
            v = 1 if (s & 1) else -1
        else:
            # JS: ((s & 0xffff) - 0x8000) >> 8
            # JS >> is arithmetic on signed-int32; the value is already in
            # int16 range so arithmetic == logical here.
            raw = (s & 0xFFFF) - 0x8000
            # emulate arithmetic >>8 on the signed int32 result
            v = raw >> 8 if raw >= 0 else -((-raw) >> 8) - (1 if (-raw) & 0xFF else 0)
            v = int(np.int16(v))
        buf[i] = np.int16(v)
    return buf


# ---------- analyze parity ---------------------------------------------

def test_xorshift_reproduces_js_coeffs():
    vec = json.loads((FIX / "analyze_stegg_vectors.json").read_text())
    coeffs = _xorshift32_stream(vec["seed"], vec["n"])
    assert coeffs[:32].tolist() == vec["coeff_first_bytes"]


def test_analyze_matches_js():
    vec = json.loads((FIX / "analyze_stegg_vectors.json").read_text())
    coeffs = _xorshift32_stream(vec["seed"], vec["n"])
    got = analyze(coeffs)
    exp = vec["analyze"]
    assert got["coeff_total"] == exp["coeff_total"]
    assert got["coeff_zero"] == exp["coeff_zero"]
    assert got["coeff_one"] == exp["coeff_one"]
    assert got["coeff_large"] == exp["coeff_large"]
    assert got["coeff_one_ratio"] == pytest.approx(exp["coeff_one_ratio"])
    assert got["capacity"] == exp["capacity"]


# ---------- _f5write parity --------------------------------------------

def test_embed_matches_js_for_pinned_cases():
    vec = json.loads((FIX / "matrix_stegg_vectors.json").read_text())
    key = bytes.fromhex(vec["key_hex"])
    n = vec["n"]

    # Sanity — the pre-embed coeffs the JS wrote should match what we
    # regenerate from the same xorshift32 seed.
    regen = _xorshift32_stream(vec["seed"], n).tolist()

    for case in vec["cases"]:
        assert case["pre_coeffs"] == regen, f"{case['label']}: pre-coeffs drift"

        # Fresh PRNG per case matches how the JS creates a fresh f5stego.
        prng = StegPRNG(key, max_pixels=vec["max_pixels"])
        coeffs = np.array(case["pre_coeffs"], dtype=np.int16)
        payload = bytes.fromhex(case["payload_hex"])

        stats = embed_coefficients(coeffs, payload, case["k"], prng)

        assert coeffs.tolist() == case["post_coeffs"], (
            f"{case['label']}: post-coefficient drift from JS"
        )
        exp = case["stats"]
        assert stats["k"] == exp["k"], case["label"]
        assert stats["embedded"] == exp["embedded"], case["label"]
        assert stats["examined"] == exp["examined"], case["label"]
        assert stats["changed"] == exp["changed"], case["label"]
        assert stats["thrown"] == exp["thrown"], case["label"]
        assert stats["efficiency"] == exp["efficiency"], case["label"]


# ---------- Python round-trip: embed + extract -------------------------

@pytest.mark.parametrize("k", [1, 2, 3, 4])
def test_embed_extract_python_roundtrip(k):
    """Round-trip against a JPEG-shaped coefficient array (DCs zeroed).

    The JS ``_f5write`` / ``f5get`` symmetry relies on ``blocks[i % 64
    == 0]`` reading as zero at extract time (see ``_matrix`` module
    docstring).  With random DC values the extract stream picks up their
    LSBs and corrupts the payload.  ``dc_zero=True`` mirrors what
    :class:`F5Stegg` will do when it stages jpeglib's Y coefficients.
    """
    coeffs = _xorshift32_stream(0xdeadbeef, 64 * 128, dc_zero=True)
    payload_body = b"round-trip payload"
    L = len(payload_body)
    assert L < 32768
    framed = bytes([L & 0xFF, (L >> 8) & 0xFF]) + payload_body

    key = b"round-trip-key"
    prng_embed = StegPRNG(key, max_pixels=16384)
    embed_coefficients(coeffs, framed, k, prng_embed)

    prng_extract = StegPRNG(key, max_pixels=16384)
    raw = extract_raw(coeffs, prng_extract)
    got = stegg_unframe(raw)
    assert got == payload_body


def test_extract_rejects_bogus_length():
    """A wrong key gives a garbage length prefix that overshoots what
    was extracted — extract must raise (or at least not return the
    real payload).
    """
    from m3gast3gg.core.f5._errors import ExtractionFailed

    coeffs = _xorshift32_stream(0xcafebabe, 64 * 128, dc_zero=True)
    framed = bytes([16, 0]) + b"sixteen-bytes!!!"
    good_key = b"good-key"
    bad_key = b"bad-key!"

    prng_embed = StegPRNG(good_key, max_pixels=16384)
    embed_coefficients(coeffs, framed, 2, prng_embed)

    prng_wrong = StegPRNG(bad_key, max_pixels=16384)
    raw = extract_raw(coeffs, prng_wrong)
    try:
        got = stegg_unframe(raw)
    except (ValueError, ExtractionFailed):
        pass  # expected: garbage length prefix overshoots the stream
    else:
        assert got != b"sixteen-bytes!!!", (
            "wrong key produced correct payload — key isn't being used"
        )
