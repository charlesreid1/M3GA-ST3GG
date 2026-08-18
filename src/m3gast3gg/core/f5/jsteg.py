"""JSteg — LSB of nonzero DCT coefficients.

JSteg (Derek Upham, c. 2001) is the simplest JPEG steganography algorithm:
replace the least significant bits of **nonzero** quantized DCT coefficients
with payload bits, skipping coefficients whose absolute value is 0 or 1
(to avoid shrinkage that would lose the bit on decode).

Uses the same JPEG I/O layer (:mod:`f5_core._dct`) as F5, so the dependency
surface is identical.  Unlike F5, there is no matrix encoding, no
permutation, and no key — this is a straight sequential LSB replacement.

Shrinkage handling
------------------

A coefficient v=±2 that has its LSB flipped becomes ±1, which the decoder
skips (|v| < 2).  When this happens the encoder retries the same payload
bit on the next usable coefficient — the bit index only advances when the
modified coefficient stays usable.  This keeps encoder and decoder in sync
without matrix encoding.

Payload framing
---------------

We prefix the payload with a 4-byte big-endian length (max 2³¹−1 bytes).
On extract we read that length, then extract exactly that many payload
bytes.
"""

from __future__ import annotations

import struct

import numpy as np

from ._dct import load_coeffs, save_coeffs
from ._errors import CapacityExceeded, ExtractionFailed

# Max payload bytes (length prefix is 4 bytes).
_MAX_PAYLOAD = (1 << 31) - 1


def _frame(payload: bytes) -> bytes:
    """Prefix ``payload`` with a 4-byte big-endian length header."""
    n = len(payload)
    if n > _MAX_PAYLOAD:
        raise ValueError(f"payload too large: {n} bytes; max {_MAX_PAYLOAD}")
    return struct.pack(">I", n) + payload


def _unframe(framed: bytes) -> bytes:
    """Strip a 4-byte big-endian length header from ``framed``."""
    if len(framed) < 4:
        raise ExtractionFailed("framed data too short for 4-byte length prefix")
    n = struct.unpack(">I", framed[:4])[0]
    if n > _MAX_PAYLOAD:
        raise ExtractionFailed(
            f"length prefix claims {n} bytes; max {_MAX_PAYLOAD}"
        )
    if 4 + n > len(framed):
        raise ExtractionFailed(
            f"length prefix claims {n} bytes but only "
            f"{len(framed) - 4} available"
        )
    return framed[4 : 4 + n]


def _count_usable(coeff_flat: np.ndarray) -> int:
    """Count AC coefficients with |v| >= 2 — usable for JSteg."""
    n = coeff_flat.size
    usable_mask = (np.arange(n) % 64) != 0
    usable_mask &= np.abs(coeff_flat) >= 2
    return int(np.count_nonzero(usable_mask))


def jsteg_capacity(jpeg_bytes: bytes) -> dict:
    """Analyse a JPEG for JSteg embedding capacity.

    Returns a dict with keys ``usable_coefficients``, ``usable_bytes``,
    and ``max_payload_bytes`` (accounting for the 4-byte length prefix).
    Capacity is an *optimistic* estimate — shrinkage during encoding may
    reduce actual capacity slightly.
    """
    c = load_coeffs(jpeg_bytes)
    flat = c.Y.reshape(-1).astype(np.int16, copy=True)
    usable = _count_usable(flat)
    usable_bytes = usable // 8
    return {
        "usable_coefficients": usable,
        "usable_bytes": usable_bytes,
        "max_payload_bytes": max(0, usable_bytes - 4),
    }


def jsteg_encode(jpeg_bytes: bytes, payload: bytes) -> bytes:
    """Embed ``payload`` into ``jpeg_bytes`` via JSteg.

    Returns the modified JPEG as ``bytes``.  Raises :exc:`CapacityExceeded`
    if the payload does not fit.

    Coefficients with |v| < 2 are skipped (DC and fragile ±1).  When a
    coefficient shrinks to |v| < 2 after LSB flipping, the bit is retried
    on the next usable coefficient — encoder and decoder stay in sync
    because both skip |v| < 2.
    """
    if not isinstance(payload, (bytes, bytearray, memoryview)):
        raise TypeError(f"payload must be bytes; got {type(payload).__name__}")

    framed = _frame(bytes(payload))
    bits_needed = len(framed) * 8

    c = load_coeffs(jpeg_bytes)
    flat = c.Y.reshape(-1).astype(np.int16, copy=True)
    n = flat.size

    usable = _count_usable(flat)
    if usable < bits_needed:
        raise CapacityExceeded(
            f"JSteg needs {bits_needed} usable coefficients but only "
            f"{usable} available ({len(framed)} framed bytes, "
            f"{len(payload)} payload bytes)"
        )

    bit_idx = 0
    examined = 0
    for i in range(n):
        if i % 64 == 0:
            continue  # skip DC
        v = int(flat[i])
        if abs(v) < 2:
            continue  # skip fragile
        examined += 1
        if bit_idx >= bits_needed:
            break

        bit = (framed[bit_idx // 8] >> (bit_idx % 8)) & 1
        if (v & 1) != bit:
            if v > 0:
                flat[i] = np.int16(v - 1)
            else:
                flat[i] = np.int16(v + 1)
            # Shrinkage check: if the coefficient is now |v| < 2 the
            # decoder will skip it.  Retry the same bit on the next
            # usable coefficient.
            if abs(int(flat[i])) < 2:
                continue  # don't advance bit_idx
        bit_idx += 1

    if bit_idx < bits_needed:
        raise CapacityExceeded(
            f"JSteg: only embedded {bit_idx} of {bits_needed} bits "
            f"(examined {examined} usable coefficients out of {n} total)"
        )

    c.set_Y(flat.reshape(c.Y.shape))
    return save_coeffs(c)


def jsteg_decode(jpeg_bytes: bytes) -> bytes:
    """Recover a JSteg-hidden payload from a JPEG.

    Returns the extracted ``bytes``.  Raises :exc:`ExtractionFailed` if the
    length prefix is invalid or the data is truncated.
    """
    c = load_coeffs(jpeg_bytes)
    flat = c.Y.reshape(-1).astype(np.int16, copy=False)
    n = flat.size

    all_bytes = bytearray()
    byte_buf = 0
    bit_count = 0

    for i in range(n):
        if i % 64 == 0:
            continue  # skip DC
        v = int(flat[i])
        if abs(v) < 2:
            continue  # skip fragile
        bit = v & 1
        byte_buf |= bit << bit_count  # LSB first, matches encode
        bit_count += 1
        if bit_count == 8:
            all_bytes.append(byte_buf)
            byte_buf = 0
            bit_count = 0

    if len(all_bytes) < 4:
        raise ExtractionFailed(
            f"JSteg: only extracted {len(all_bytes)} bytes from LSBs; "
            f"need at least 4 for length prefix"
        )

    payload_len = struct.unpack(">I", bytes(all_bytes[:4]))[0]
    if payload_len > _MAX_PAYLOAD:
        raise ExtractionFailed(
            f"JSteg: length prefix claims {payload_len} bytes "
            f"(max {_MAX_PAYLOAD})"
        )

    framed_len = 4 + payload_len
    if framed_len > len(all_bytes):
        raise ExtractionFailed(
            f"JSteg: length prefix claims {payload_len} payload bytes "
            f"({framed_len} framed) but only {len(all_bytes)} bytes extracted"
        )

    framed = bytes(all_bytes[:framed_len])
    try:
        return _unframe(framed)
    except ExtractionFailed:
        raise
    except Exception as e:
        raise ExtractionFailed(str(e)) from e
