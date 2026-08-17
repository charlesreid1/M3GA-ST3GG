"""Round-trip tests for the JPEG DCT codec substrate ``f5_core._dct``.

Phase 1 acceptance: reading a clean JPEG, then re-encoding it, produces
bit-exact DCT coefficients and quantization tables. Subsampling factors
survive. Marker count does not grow.

Non-JPEG input and CMYK JPEGs are rejected.
"""

from __future__ import annotations

import io
import pytest

# Skip the whole module cleanly if jpeglib isn't installed.
pytest.importorskip("jpeglib")

import numpy as np
from PIL import Image

from m3gast3gg.core.f5 import InvalidJPEG
from m3gast3gg.core.f5._dct import load_coeffs, save_coeffs


# ---------- Fixtures ----------

@pytest.fixture(scope="module")
def clean_jpeg_bytes() -> bytes:
    """Generate a fixed-seed JPEG with non-trivial DCT coefficients."""
    rng = np.random.RandomState(42)
    pixels = rng.randint(0, 256, (128, 128, 3), dtype=np.uint8)
    img = Image.fromarray(pixels)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


# ---------- Round-trip ----------

def test_load_returns_yccbcr_shapes(clean_jpeg_bytes):
    c = load_coeffs(clean_jpeg_bytes)
    assert c.Y is not None and c.Y.dtype == np.int16
    assert c.Cb is not None and c.Cr is not None
    assert c.Y.ndim == 4 and c.Y.shape[2:] == (8, 8)
    assert c.qt.ndim == 3 and c.qt.shape[1:] == (8, 8)


def test_dct_roundtrip_is_bit_exact(clean_jpeg_bytes):
    """Load → save → re-load must produce identical DCT coefficients on
    every component, plus identical quantization tables. F5 embed/extract
    fundamentally depends on this property of the codec substrate.
    """
    c1 = load_coeffs(clean_jpeg_bytes)
    out = save_coeffs(c1)
    c2 = load_coeffs(out)

    assert np.array_equal(c1.Y, c2.Y), "Y coefficients drifted through round-trip"
    assert np.array_equal(c1.Cb, c2.Cb), "Cb coefficients drifted through round-trip"
    assert np.array_equal(c1.Cr, c2.Cr), "Cr coefficients drifted through round-trip"
    assert np.array_equal(c1.qt, c2.qt), "quantization tables drifted through round-trip"


def test_subsampling_preserved(clean_jpeg_bytes):
    c1 = load_coeffs(clean_jpeg_bytes)
    c2 = load_coeffs(save_coeffs(c1))
    assert c1.samp_factor.tolist() == c2.samp_factor.tolist()


def test_markers_do_not_grow(clean_jpeg_bytes):
    """The whole point of save_coeffs' APP0 scrub: markers must not
    multiply across a round-trip. libjpeg auto-emits its own APP0 on
    write, so preserving the source APP0 would double it.
    """
    c1 = load_coeffs(clean_jpeg_bytes)
    c2 = load_coeffs(save_coeffs(c1))
    assert len(c2.markers) <= len(c1.markers)


def test_perturbing_Y_survives_roundtrip(clean_jpeg_bytes):
    """Regression for the F5 write path: mutating a DC coefficient in Y
    and going through save/load must preserve that mutation exactly.
    """
    c = load_coeffs(clean_jpeg_bytes)
    new_Y = c.Y.copy()
    # Flip a mid-block AC coefficient. Pick a location every JPEG has.
    new_Y[10, 10, 3, 4] = np.int16(int(new_Y[10, 10, 3, 4]) + 1)
    expected = int(new_Y[10, 10, 3, 4])

    c.set_Y(new_Y)
    c2 = load_coeffs(save_coeffs(c))
    assert int(c2.Y[10, 10, 3, 4]) == expected


# ---------- Input validation ----------

def test_rejects_non_jpeg():
    with pytest.raises(InvalidJPEG):
        load_coeffs(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)


def test_rejects_short_input():
    with pytest.raises(InvalidJPEG):
        load_coeffs(b"")
    with pytest.raises(InvalidJPEG):
        load_coeffs(b"\xff")
