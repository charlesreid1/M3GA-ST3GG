"""JPEG DCT-coefficient IO — thin wrapper around ``jpeglib``.

Design notes:

* Inputs and outputs are ``bytes``. jpeglib itself only speaks file paths
  (see :func:`jpeglib.read_dct`), so we go via ``NamedTemporaryFile``. F5
  callers stay path-agnostic and it matches the API surface of the rest of
  the toolkit.
* :func:`save_coeffs` scrubs any pre-existing APP0 (JFIF) marker before
  writing. libjpeg re-emits its own APP0 on write, so preserving the
  source APP0 in ``markers`` doubles it. Every other marker (APP1/EXIF,
  APP2/ICC, COM, …) is kept.
* Non-JPEG input and CMYK JPEGs raise :class:`~f5_core.InvalidJPEG` — the
  JS ancestor silently picked the first component of a CMYK image, which
  is wrong. We refuse instead.
* ``jpeglib`` is an optional dependency, gated behind the ``jpeg`` extra.
  Importing this module raises a clear :class:`ImportError` if it's
  missing.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from ._errors import InvalidJPEG

try:
    import jpeglib
except ImportError as _exc:  # pragma: no cover — exercised only when extra missing
    raise ImportError(
        "f5_core requires the 'jpeglib' package. Install it with "
        "`pip install stegg[jpeg]` (or `pip install jpeglib`)."
    ) from _exc


# Bytes 0-1 of every JPEG file.
_SOI = b"\xff\xd8"


@dataclass
class Coeffs:
    """Decoded DCT coefficients + the underlying jpeglib handle.

    We keep the ``jpeglib.DCTJPEG`` instance around because reconstructing
    one from scratch means matching a moving-target constructor (huffman
    tables, num_scans, block_dims, …). Instead, F5 mutates ``.Y`` in place
    on the same object and hands it back to :func:`save_coeffs`.

    The named attributes below are convenience views into ``jpeg`` — they
    stay in sync as long as callers use ``.Y = new_Y`` (jpeglib's
    ``DCTJPEG`` has ``Y`` as a settable property).
    """

    jpeg: "jpeglib.DCTJPEG"
    Y: np.ndarray                            # (nY_rows, nY_cols, 8, 8) int16
    Cb: Optional[np.ndarray]                 # None on grayscale
    Cr: Optional[np.ndarray]
    qt: np.ndarray                           # (n_tables, 8, 8) int16
    samp_factor: np.ndarray                  # (n_components, 2) int
    height: int
    width: int
    progressive_mode: bool
    markers: List["jpeglib.Marker"]          # jpeglib.Marker instances

    def set_Y(self, new_Y: np.ndarray) -> None:
        """Write modified Y coefficients back to the underlying handle.

        F5 mutates Y (luminance) coefficients only. Use this to keep the
        Coeffs view and the jpeglib handle in sync before save_coeffs.
        """
        self.jpeg.Y = new_Y
        self.Y = self.jpeg.Y


def _is_probably_jpeg(data: bytes) -> bool:
    return len(data) >= 2 and data[:2] == _SOI


def load_coeffs(jpeg_bytes: bytes) -> Coeffs:
    """Decode DCT coefficients from a JPEG byte string.

    Raises :class:`InvalidJPEG` if ``jpeg_bytes`` isn't a JPEG or is CMYK.
    """
    if not _is_probably_jpeg(jpeg_bytes):
        raise InvalidJPEG("input does not start with JPEG SOI marker (FFD8)")

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as fh:
        fh.write(jpeg_bytes)
        tmp_path = fh.name
    try:
        im = jpeglib.read_dct(tmp_path)
    finally:
        os.unlink(tmp_path)

    # jpeglib exposes a K attribute for CMYK; also check colorspace.
    if getattr(im, "K", None) is not None or im.num_components == 4:
        raise InvalidJPEG(
            f"CMYK JPEGs are not supported (num_components={im.num_components}); "
            "F5 targets the luminance component of a YCbCr or grayscale JPEG."
        )
    if im.num_components not in (1, 3):
        raise InvalidJPEG(
            f"unsupported num_components={im.num_components}; "
            "F5 targets grayscale (1) or YCbCr (3) JPEGs."
        )

    return Coeffs(
        jpeg=im,
        Y=im.Y,
        Cb=im.Cb,
        Cr=im.Cr,
        qt=im.qt,
        samp_factor=im.samp_factor,
        height=im.height,
        width=im.width,
        progressive_mode=bool(im.progressive_mode),
        markers=list(im.markers) if im.markers is not None else [],
    )


def _scrub_duplicate_app0(markers: list) -> list:
    """libjpeg auto-emits an APP0 (JFIF) on write. If the source carried
    one and we hand it back through ``markers``, the output ends up with
    two. Drop the first APP0 the caller preserved so we net one.
    """
    seen_app0 = False
    scrubbed = []
    for m in markers:
        if getattr(m, "type", None) == jpeglib.MarkerType.JPEG_APP0 and not seen_app0:
            seen_app0 = True
            continue
        scrubbed.append(m)
    return scrubbed


def save_coeffs(c: Coeffs, *, quality: int = -1) -> bytes:
    """Re-encode a :class:`Coeffs` back to JPEG bytes.

    ``quality`` defaults to -1 (jpeglib's "use existing qt" sentinel).
    Coefficients are written losslessly regardless of quality; the
    parameter only affects the qt if callers want to replace it.

    The underlying :class:`jpeglib.DCTJPEG` handle is mutated in place —
    its ``markers`` list is rewritten to drop a source APP0 that would
    otherwise duplicate libjpeg's auto-emitted one on write.  We also
    post-process the SOF marker to force component IDs 1/2/3 (JFIF
    convention) — libjpeg defaults to 0/1/2, which trips up JPEG
    consumers that use ``componentId==1`` as their "find Y" heuristic
    (the ``f5stegojs`` reference implementation is one such consumer).
    """
    c.jpeg.markers = _scrub_duplicate_app0(list(c.markers))
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as fh:
        tmp_path = fh.name
    try:
        c.jpeg.write_dct(tmp_path, quality=quality)
        with open(tmp_path, "rb") as f:
            raw = f.read()
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
    return _normalize_component_ids(raw)


def _normalize_component_ids(jpeg_bytes: bytes) -> bytes:
    """Rewrite SOF **and** SOS component IDs to the JFIF convention (1, 2, 3, ...).

    Some libjpeg builds emit component IDs 0/1/2 instead of the
    JFIF-standard 1/2/3.  The SOF marker declares the IDs; every SOS
    (Start Of Scan) marker in the file then references them.  Both must
    be rewritten together — updating only SOF corrupts the file because
    SOS's Csj values would no longer resolve.

    Walks the marker sequence once, remembering the old→new ID map from
    the first SOFn, then patches every subsequent SOS.  Marker lengths
    are left alone.
    """
    b = bytearray(jpeg_bytes)
    n = len(b)
    if n < 2 or b[0] != 0xFF or b[1] != 0xD8:
        return jpeg_bytes  # not a JPEG — leave alone

    id_map: dict[int, int] = {}
    i = 2
    while i < n - 1:
        if b[i] != 0xFF:
            return jpeg_bytes  # desync; give up rather than corrupt
        marker = b[i + 1]
        # Skip FF padding bytes.
        if marker == 0xFF:
            i += 1
            continue
        # Standalone markers (no length field): SOI, EOI, RSTn, TEM.
        if marker in (0x00, 0x01, 0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9):
            i += 2
            continue
        # Everything else is a length-prefixed segment.
        if i + 4 > n:
            return jpeg_bytes
        seg_len = (b[i + 2] << 8) | b[i + 3]
        seg_start = i + 2
        seg_end = seg_start + seg_len
        if seg_end > n:
            return jpeg_bytes

        # SOFn markers: FFC0..FFCF except FFC4 (DHT), FFC8 (reserved), FFCC (DAC).
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            # Layout: len(2) P(1) Y(2) X(2) Nf(1) then Nf*3 bytes.
            nf_idx = seg_start + 2 + 1 + 2 + 2  # skip len(2), P(1), Y(2), X(2)
            if nf_idx >= seg_end:
                return jpeg_bytes
            nf = b[nf_idx]
            comp_spec = nf_idx + 1
            if comp_spec + nf * 3 > seg_end:
                return jpeg_bytes
            for k in range(nf):
                old_id = b[comp_spec + k * 3]
                new_id = k + 1
                if old_id not in id_map:
                    id_map[old_id] = new_id
                b[comp_spec + k * 3] = new_id

        # SOS marker: FFDA.  Layout: len(2) Ns(1) then Ns*(Csj(1) Tdj/Taj(1))
        elif marker == 0xDA:
            ns_idx = seg_start + 2
            if ns_idx >= seg_end:
                return jpeg_bytes
            ns = b[ns_idx]
            comp_spec = ns_idx + 1
            if comp_spec + ns * 2 > seg_end:
                return jpeg_bytes
            for k in range(ns):
                old_id = b[comp_spec + k * 2]
                if old_id in id_map:
                    b[comp_spec + k * 2] = id_map[old_id]
            # After SOS the entropy-coded segment follows — resume scanning
            # from seg_end; scan_for_marker below jumps FF00 stuffing.
            i = seg_end
            while i < n - 1:
                if b[i] == 0xFF and b[i + 1] != 0x00 and not (0xD0 <= b[i + 1] <= 0xD7):
                    break
                i += 1
            continue

        i = seg_end

    return bytes(b)
