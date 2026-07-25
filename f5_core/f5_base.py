"""``F5Base`` — abstract F5 embedder/extractor.

Owns everything the F5 paper actually specifies:

* JPEG DCT coefficient IO (via :mod:`f5_core._dct`).
* Y-component staging: natural → zigzag reorder, DC preservation.
* Matrix encoding with parameter ``k`` and shrinkage
  (via :mod:`f5_core._matrix`).
* ``k`` auto-selection with the ``k-1`` capacity-retry fallback.

Subclasses pick the three choices the paper leaves open:

* ``_make_prng(coeff_count)`` — the PRNG that drives permutation + gamma.
* ``_frame(payload) -> bytes`` — how the payload length is packed.
* ``_unframe(raw) -> bytes`` — reverse of ``_frame``, applied to the
  raw byte stream ``_matrix.extract_raw`` returns.

Concrete subclasses also handle their own key/password type validation
in ``__init__``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import numpy as np

from ._dct import load_coeffs, save_coeffs
from ._errors import CapacityExceeded
from ._matrix import PRNGBackend, analyze, embed_coefficients, extract_raw


# JPEG standard zigzag scan order.  ZIGZAG[i] = natural-order index of
# the coefficient at zigzag position i.  Applied per 8×8 block, this
# makes the flat Y view match ``f5stegojs``'s ``comp.blocks`` layout and
# the Westfeld ``deZigZag`` remap.
_ZIGZAG = np.array([
     0,  1,  8, 16,  9,  2,  3, 10,
    17, 24, 32, 25, 18, 11,  4,  5,
    12, 19, 26, 33, 40, 48, 41, 34,
    27, 20, 13,  6,  7, 14, 21, 28,
    35, 42, 49, 56, 57, 50, 43, 36,
    29, 22, 15, 23, 30, 37, 44, 51,
    58, 59, 52, 45, 38, 31, 39, 46,
    53, 60, 61, 54, 47, 55, 62, 63,
], dtype=np.int32)
_INV_ZIGZAG = np.argsort(_ZIGZAG).astype(np.int32)


class F5Base(ABC):
    """Abstract F5 codec — subclass to bind a PRNG and framing scheme."""

    # ---- hooks subclasses must implement ---------------------------------

    @abstractmethod
    def _make_prng(self, coeff_count: int) -> PRNGBackend:
        """Return a PRNG sized for ``coeff_count`` DCT coefficients."""

    @abstractmethod
    def _frame(self, payload: bytes) -> bytes:
        """Pack ``payload`` with the dialect's length prefix."""

    @abstractmethod
    def _unframe(self, raw: bytes) -> bytes:
        """Strip the length prefix from ``_matrix.extract_raw``'s output."""

    # ---- public API ------------------------------------------------------

    def analyze(self, jpeg_bytes: bytes) -> dict:
        c = load_coeffs(jpeg_bytes)
        flat, _dc, _shape = _stage_y(c.Y)
        return analyze(flat)

    def embed(self, jpeg_bytes: bytes, payload: bytes) -> bytes:
        if not isinstance(payload, (bytes, bytearray, memoryview)):
            raise TypeError(f"payload must be bytes; got {type(payload).__name__}")
        framed = self._frame(bytes(payload))

        c = load_coeffs(jpeg_bytes)
        flat, dc_backup, y_shape = _stage_y(c.Y)

        k = self._pick_k(flat, len(framed))
        attempt_flat = flat.copy()
        prng = self._make_prng(flat.size)
        try:
            embed_coefficients(attempt_flat, framed, k, prng)
        except CapacityExceeded:
            if k <= 1:
                raise
            k -= 1
            attempt_flat = flat.copy()
            prng = self._make_prng(flat.size)
            embed_coefficients(attempt_flat, framed, k, prng)

        new_Y = _unstage_y(attempt_flat, dc_backup, y_shape)
        c.set_Y(new_Y)
        return save_coeffs(c)

    def extract(self, jpeg_bytes: bytes) -> bytes:
        c = load_coeffs(jpeg_bytes)
        flat, _dc, _shape = _stage_y(c.Y)
        prng = self._make_prng(flat.size)
        raw = extract_raw(flat, prng)
        return self._unframe(raw)

    # ---- internal --------------------------------------------------------

    def _pick_k(self, flat: np.ndarray, framed_len: int) -> int:
        """Highest ``k`` whose capacity fits ``framed_len`` bytes."""
        prop = analyze(flat)
        for i in range(len(prop["capacity"]) - 1, 0, -1):
            if prop["capacity"][i] >= framed_len:
                return i
        raise CapacityExceeded(
            f"framed payload ({framed_len} bytes) does not fit at any k; "
            f"max k=1 capacity is {prop['capacity'][1]}"
        )


# ---------------------------------------------------------------------------
# Y-array staging (jpeglib <-> _matrix)
# ---------------------------------------------------------------------------

def _stage_y(Y: np.ndarray) -> tuple[np.ndarray, np.ndarray, tuple]:
    """Flatten Y for the matrix layer; return (flat, dc_backup, shape).

    Reorders each 8×8 block from natural (jpeglib) to zigzag (JS/Java)
    order before flattening. Zeros the DC of each block; backs it up so
    :func:`_unstage_y` can restore.
    """
    shape = Y.shape
    nrows, ncols = shape[0], shape[1]
    per_block = Y.reshape(nrows * ncols, 64).astype(np.int16, copy=True)
    zz = per_block[:, _ZIGZAG]
    flat = zz.reshape(-1)
    dc_backup = flat[::64].copy()
    flat[::64] = 0
    return flat, dc_backup, shape


def _unstage_y(flat: np.ndarray, dc_backup: np.ndarray, shape: tuple) -> np.ndarray:
    flat = flat.copy()
    flat[::64] = dc_backup
    nrows, ncols = shape[0], shape[1]
    per_block_zz = flat.reshape(nrows * ncols, 64)
    per_block_nat = per_block_zz[:, _INV_ZIGZAG]
    return np.ascontiguousarray(per_block_nat.reshape(shape), dtype=np.int16)
