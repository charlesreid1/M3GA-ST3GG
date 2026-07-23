"""Payload framing for the stegg dialect.

The ``f5stegojs`` layout (``f5put`` lines 411–429) prefixes the raw
payload with a **2- or 3-byte little-endian length**:

* If ``len < 32768``: two bytes, ``lo = len & 0xFF``, ``hi = len >> 8``.
  The high bit of the second byte is zero — that's how the decoder tells
  the two forms apart.
* Otherwise (up to 8_388_607 bytes): three bytes, ``lo = len & 0xFF``,
  ``mid = ((len >> 8) & 0x7F) | 0x80``, ``hi = len >> 15``.  The
  ``0x80`` flag in the middle byte signals the 3-byte form.

Extract's length-decode (``f5get`` lines 585–593) reverses the same
scheme.  We do the reverse here in :func:`stegg_unframe`; the raw
extraction path in :func:`f5_core._matrix.extract_bytes` already applies
the length prefix internally and returns the unframed payload — this
module exists mainly for the embed side and for tests that want to
inspect the framed shape.
"""

from __future__ import annotations

MAX_PAYLOAD = (1 << 23) - 1  # JS: 'Data too big. Max 8388607 bytes allowed.'


def stegg_frame(payload: bytes) -> bytes:
    """Prefix ``payload`` with the stegg 2/3-byte length header."""
    n = len(payload)
    if n > MAX_PAYLOAD:
        raise ValueError(
            f"payload too large: {n} bytes; stegg max is {MAX_PAYLOAD}"
        )
    if n < 32768:
        header = bytes([n & 0xFF, (n >> 8) & 0xFF])
    else:
        header = bytes([
            n & 0xFF,
            ((n >> 8) & 0x7F) | 0x80,
            (n >> 15) & 0xFF,
        ])
    return header + payload


def stegg_unframe(framed: bytes) -> bytes:
    """Strip the stegg length prefix from ``framed`` and return payload.

    Raises :class:`ValueError` if the prefix is malformed or overflows
    the buffer.
    """
    if len(framed) < 2:
        raise ValueError("framed payload too short to hold a length prefix")

    lo = framed[0]
    mid = framed[1]
    if mid & 0x80:
        if len(framed) < 3:
            raise ValueError("3-byte length prefix truncated")
        n = lo + ((mid & 0x7F) << 8) + (framed[2] << 15)
        header_len = 3
    else:
        n = lo + (mid << 8)
        header_len = 2

    if header_len + n > len(framed):
        raise ValueError(
            f"length prefix claims {n} bytes but only {len(framed) - header_len} available"
        )
    return framed[header_len : header_len + n]
