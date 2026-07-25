"""``F5Stegg`` — the ``f5stegojs`` dialect of F5.

Byte-compatible with the JS library at ``f5stego-lib.js``. Layers three
choices onto :class:`f5_core.f5_base.F5Base`:

* PRNG: RC4-KSA + PRGA keystream driven by a raw byte key
  (:class:`f5_core._prng_stegg.StegPRNG`).
* Framing: 2/3-byte little-endian length prefix
  (:mod:`f5_core._framing`).
* Key format: raw bytes; ``str`` is rejected at construction to steer
  users to the password-based dialect.

The DC-preservation and zigzag staging live in :mod:`f5_core.f5_base` —
they are F5 paper mechanics, not stegg-specific.
"""

from __future__ import annotations

from typing import Optional

from ._errors import ExtractionFailed
from ._framing import stegg_frame, stegg_unframe
from ._matrix import PRNGBackend
from ._prng_stegg import StegPRNG
from .f5_base import F5Base


class F5Stegg(F5Base):
    """F5 stegg-dialect embedder / extractor.

    Parameters
    ----------
    key
        Raw byte string, at least one byte.
    max_pixels
        Upper bound on the coefficient count the RC4 keystream will
        cover. Default sizes the pool to fit the actual JPEG at call
        time (avoids materialising the JS default 66 MB pool for small
        images — pure-Python RC4 is much slower than V8's).
    """

    def __init__(self, key: bytes, *, max_pixels: Optional[int] = None):
        if isinstance(key, str):
            raise TypeError(
                "F5Stegg requires a bytes key; use a password-based dialect for a string."
            )
        if not isinstance(key, (bytes, bytearray, memoryview)):
            raise TypeError(f"key must be bytes; got {type(key).__name__}")
        if len(key) == 0:
            raise ValueError("key must not be empty")
        self._key = bytes(key)
        self._max_pixels = int(max_pixels) if max_pixels is not None else None

    # ---- F5Base hooks ----------------------------------------------------

    def _make_prng(self, coeff_count: int) -> PRNGBackend:
        # Pool = max_pixels * 33 // 8 bytes; we need coeff_count*4 perm
        # bytes plus a small gamma tail. Using coeff_count itself as
        # max_pixels gives pool = 4.125 * coeff_count, which is well
        # above the actual requirement.
        mp = self._max_pixels if self._max_pixels is not None else max(coeff_count, 1)
        return StegPRNG(self._key, max_pixels=mp)

    def _frame(self, payload: bytes) -> bytes:
        return stegg_frame(payload)

    def _unframe(self, raw: bytes) -> bytes:
        try:
            return stegg_unframe(raw)
        except ValueError as e:
            raise ExtractionFailed(str(e)) from e
