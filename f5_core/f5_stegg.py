"""``F5Stegg`` — the ``f5stegojs`` dialect of F5.

Byte-compatible with the JS library shipped at ``f5stego-lib.js``.  Keys
are raw byte strings; framing is the 2/3-byte length prefix from
:mod:`f5_core._framing`.  Auto-selects the matrix parameter ``k`` from
:func:`f5_core._matrix.analyze`, with the same fallback to ``k-1`` on
capacity exceptions that ``f5put`` does.

Coefficient staging
-------------------

The JS reference stores DCT coefficients in **zigzag** order — that's
JPEG's on-disk order and matches the AC decoder's output.  jpeglib
returns the same coefficients in **natural (row-major spatial)** order:
its ``Y`` array is ``(nrows, ncols, 8, 8)`` where the trailing 8×8 is
spatial, so ``Y[..., 0, 0]`` is DC and ``Y[..., 0, 1]`` is AC(1) in the
*spatial* sense, not zigzag(1).

F5's shuffle-then-embed pipeline reorders coefficients across the whole
Y array.  If the JS embeds a payload at zigzag positions
``{5, 12, 21, ...}`` of specific blocks, jpeglib decoding shows those
modifications at *natural* positions ``{4, 2, ...}`` of the same blocks.
Fisher-Yates walking the natural-order flat view would then visit a
different sequence of coefficients than the JS did — and interop fails.

Fix: apply the JPEG zigzag reorder to each 8×8 block before flattening
and running the matrix layer, then invert on the way out.  This makes
the flat view identical to the JS's ``comp.blocks``.

DC positions (index 0 mod 64 in the zigzag-flat view) get zeroed for
the F5 pass; we back them up and restore before saving.  See the
``_matrix`` module docstring for why.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from ._dct import load_coeffs, save_coeffs
from ._errors import CapacityExceeded, ExtractionFailed, F5Error, InvalidJPEG
from ._framing import stegg_frame
from ._matrix import analyze, embed_coefficients, extract_bytes
from ._prng_stegg import DEFAULT_MAX_PIXELS, StegPRNG


class F5Stegg:
    """F5 stegg-dialect embedder / extractor.

    Parameters
    ----------
    key
        Raw byte string, at least one byte.  Passing a ``str`` raises
        :class:`TypeError` with a pointer to :class:`F5Classic` — the
        two-class split is the whole point of the API.
    max_pixels
        Upper bound on the coefficient count the RC4 keystream will
        cover.  Defaults to 16M (the JS default).  Callers embedding
        into unusually large JPEGs may need to raise this.
    """

    def __init__(self, key: bytes, *, max_pixels: Optional[int] = None):
        if isinstance(key, str):
            raise TypeError(
                "F5Stegg requires a bytes key; use F5Classic for a password string."
            )
        if not isinstance(key, (bytes, bytearray, memoryview)):
            raise TypeError(f"key must be bytes; got {type(key).__name__}")
        if len(key) == 0:
            raise ValueError("key must not be empty")
        self._key = bytes(key)
        # When None: size the PRNG to fit the actual JPEG at call time.
        # This mirrors the JS behaviour without forcing every embed to
        # burn 66 MB (default 4096*4096 pixels * 4.125 bytes) of RC4
        # keystream up front — pure-Python RC4 is much slower than V8's.
        self._max_pixels = int(max_pixels) if max_pixels is not None else None

    # ---- public API -------------------------------------------------------

    def analyze(self, jpeg_bytes: bytes) -> dict:
        """Return capacity info for ``jpeg_bytes`` without touching it."""
        c = load_coeffs(jpeg_bytes)
        flat, _dc, _shape = _stage_y(c.Y)
        return analyze(flat)

    def embed(self, jpeg_bytes: bytes, payload: bytes) -> bytes:
        """Embed ``payload`` into the Y component of ``jpeg_bytes``.

        Auto-selects ``k`` via :func:`~f5_core._matrix.analyze`, then
        retries with ``k-1`` if the first attempt exceeds capacity —
        same behaviour as the JS ``f5put``.

        Raises :class:`CapacityExceeded` when no ``k`` can fit the
        framed payload, :class:`InvalidJPEG` for malformed input.
        """
        if not isinstance(payload, (bytes, bytearray, memoryview)):
            raise TypeError(f"payload must be bytes; got {type(payload).__name__}")
        framed = stegg_frame(bytes(payload))

        c = load_coeffs(jpeg_bytes)
        flat, dc_backup, y_shape = _stage_y(c.Y)

        try:
            k = self._pick_k(flat, len(framed))
            attempt_flat = flat.copy()
            prng = StegPRNG(self._key, max_pixels=self._effective_max_pixels(flat.size))
            try:
                embed_coefficients(attempt_flat, framed, k, prng)
            except CapacityExceeded:
                # Retry with k-1, same as JS f5put's catch clause.
                if k <= 1:
                    raise
                k -= 1
                attempt_flat = flat.copy()
                prng = StegPRNG(self._key, max_pixels=self._effective_max_pixels(flat.size))
                embed_coefficients(attempt_flat, framed, k, prng)
        finally:
            # Nothing to restore on ``flat`` — attempt_flat is a copy.
            pass

        # Merge changed AC coefficients back with the preserved DCs.
        new_Y = _unstage_y(attempt_flat, dc_backup, y_shape)
        c.set_Y(new_Y)
        return save_coeffs(c)

    def extract(self, jpeg_bytes: bytes) -> bytes:
        """Extract the payload previously embedded with the same key."""
        c = load_coeffs(jpeg_bytes)
        flat, _dc_backup, _y_shape = _stage_y(c.Y)
        prng = StegPRNG(self._key, max_pixels=self._effective_max_pixels(flat.size))
        return extract_bytes(flat, prng)

    # ---- internal ---------------------------------------------------------

    def _effective_max_pixels(self, coeff_count: int) -> int:
        """Size the RC4 pool to fit the coefficient array.

        The pool covers ``max_pixels * 33 // 8`` bytes; the matrix layer
        needs ``coeff_count * 4`` u32 permutation words plus a small
        gamma tail.  We round up to leave headroom for gamma without
        materialising the JS default 66 MB pool.
        """
        if self._max_pixels is not None:
            return self._max_pixels
        # Need pool >= coeff_count*4 + gamma_budget.  Solve for max_pixels
        # given pool = max_pixels * 33 // 8.  Use coeff_count as a safe
        # lower bound on max_pixels (pool = 4.125 * coeff_count bytes,
        # covers 4*coeff_count perm bytes + 0.125*coeff_count gamma bytes).
        # 0.125 * coeff_count is more gamma than any framed payload needs.
        return max(coeff_count, 1)

    def _pick_k(self, flat: np.ndarray, framed_len: int) -> int:
        """Highest ``k`` whose capacity fits the framed payload.

        Mirrors ``f5put`` lines 446–455.  Iterates from k=16 downwards
        so we get the most-efficient (highest-throughput, least-changes)
        matrix parameter.  Raises :class:`CapacityExceeded` if nothing
        fits.
        """
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

# JPEG standard zigzag scan order.  ZIGZAG[i] = natural-order index of the
# coefficient at zigzag position i.  Applied to each 8×8 block's flat
# view, this yields JS-comp.blocks layout.
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
# Inverse: natural → zigzag.  Used to un-zigzag on the way back.
_INV_ZIGZAG = np.argsort(_ZIGZAG).astype(np.int32)


def _stage_y(Y: np.ndarray) -> tuple[np.ndarray, np.ndarray, tuple]:
    """Flatten Y for the matrix layer; return (flat, dc_backup, shape).

    Reorders each 8×8 block from natural (jpeglib) to zigzag (JS) order
    before flattening.  Zeros the DC of each block; backs it up so the
    reverse can restore.
    """
    shape = Y.shape
    nrows, ncols = shape[0], shape[1]
    # Natural-order flat view of every 8×8 block.
    per_block = Y.reshape(nrows * ncols, 64).astype(np.int16, copy=True)
    # Zigzag each block: coefficient at zigzag position i is at natural
    # position ZIGZAG[i].
    zz = per_block[:, _ZIGZAG]
    flat = zz.reshape(-1)
    dc_backup = flat[::64].copy()
    flat[::64] = 0
    return flat, dc_backup, shape


def _unstage_y(flat: np.ndarray, dc_backup: np.ndarray, shape: tuple) -> np.ndarray:
    """Reverse of :func:`_stage_y`.  Restores DCs, un-zigzags each block,
    reshapes to the original ``Y`` shape.
    """
    flat = flat.copy()
    flat[::64] = dc_backup
    nrows, ncols = shape[0], shape[1]
    per_block_zz = flat.reshape(nrows * ncols, 64)
    # Undo zigzag: natural[i] = zigzag[INV_ZIGZAG[i]].
    per_block_nat = per_block_zz[:, _INV_ZIGZAG]
    # jpeglib.write_dct hands the array to ctypes; must be C-contiguous.
    return np.ascontiguousarray(per_block_nat.reshape(shape), dtype=np.int16)
