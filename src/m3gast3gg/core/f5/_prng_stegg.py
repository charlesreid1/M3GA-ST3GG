"""RC4-KSA + PRGA keystream — the ``f5stegojs`` dialect PRNG.

Line-for-line port of ``shuffleInit`` (f5stego-lib.js 128–161) and the
Fisher-Yates + gamma layout used by ``stegShuffle`` (163–187).

The JS carves ``randPool`` (a ``maxPixels * 4.125``-byte RC4 keystream)
into two regions:

* offsets ``[0, l*4)`` — read as a ``Uint32Array`` little-endian, drives
  Fisher-Yates over the coefficient index array. Element 0 is skipped
  (the loop starts at ``k=1``) but its bytes still occupy the buffer.
* offsets ``[l*4, ...)`` — read byte-wise as the "gamma" mask XOR'd into
  every payload byte during embed/extract.

Callers are the two dialect classes; ``F5Stegg`` binds :class:`StegPRNG`
to a byte-string key. Parity vectors live at
``tests/unit/fixtures/f5/prng_stegg_vectors.json`` (regenerated with
``scripts/gen_f5_stegg_prng_vectors.js``).
"""

from __future__ import annotations

import numpy as np


DEFAULT_MAX_PIXELS = 4096 * 4096
# JS uses maxPixels * 4.125 -> maxPixels * 33 // 8.  Store as an exact
# integer so we don't rely on float rounding.
_POOL_NUMER = 33
_POOL_DENOM = 8


def _pool_size(max_pixels: int) -> int:
    return (max_pixels * _POOL_NUMER) // _POOL_DENOM


def _rc4_keystream(key: bytes, n_bytes: int) -> np.ndarray:
    """Standard RC4: KSA over ``key``, then ``n_bytes`` PRGA outputs.

    Returns a uint8 ndarray of length ``n_bytes``.  The JS wrote the
    output into an ``ArrayBuffer`` and later reinterpreted parts of it as
    ``Uint32Array``/``Uint8Array``; we keep it as raw bytes and reinterpret
    on demand.

    Uses a ``list[int]`` for the S-box in the hot PRGA loop: about 8×
    faster than numpy indexing per element, which matters because
    real JPEGs need ~3-5 MB of keystream and the loop is inherently
    sequential (state carries between iterations).
    """
    if not key:
        raise ValueError("key needed")

    # KSA: numpy is fine here — 256 iterations, not on the hot path.
    S = list(range(256))
    j = 0
    key_len = len(key)
    for i in range(256):
        j = (j + S[i] + key[i % key_len]) & 0xFF
        S[i], S[j] = S[j], S[i]

    # PRGA hot loop.  Local rebinds trim attribute lookups.
    out = bytearray(n_bytes)
    i = 0
    j = 0
    for k in range(n_bytes):
        i = (i + 1) & 0xFF
        Si = S[i]
        j = (j + Si) & 0xFF
        Sj = S[j]
        S[i] = Sj
        S[j] = Si
        # JS: rnd[k] = S[(t + S[i]) & 255];  where t = old S[i] = Si, new S[i] = Sj.
        out[k] = S[(Si + Sj) & 0xFF]
    return np.frombuffer(bytes(out), dtype=np.uint8).copy()


class StegPRNG:
    """The stegg-dialect PRNG bound to a specific byte key.

    Behaves like a factory around a single RC4 keystream: repeated calls
    to ``permute_indices`` are legal but expensive (each rebuilds the
    permutation from scratch, matching the JS which calls ``stegShuffle``
    afresh for embed and extract).  Callers that need to consume gamma
    bytes after permuting use :meth:`gamma_stream` to get a byte
    iterator.
    """

    def __init__(self, key: bytes, max_pixels: int = DEFAULT_MAX_PIXELS):
        if not isinstance(key, (bytes, bytearray, memoryview)):
            raise TypeError(f"key must be bytes; got {type(key).__name__}")
        if len(key) == 0:
            raise ValueError("key needed")
        self._key = bytes(key)
        self._max_pixels = int(max_pixels)
        self._pool: np.ndarray | None = None

    @property
    def pool(self) -> np.ndarray:
        """Materialise the RC4 keystream on first use, cache thereafter."""
        if self._pool is None:
            self._pool = _rc4_keystream(self._key, _pool_size(self._max_pixels))
        return self._pool

    # ---- permutation ------------------------------------------------------

    def permute_indices(self, n: int) -> np.ndarray:
        """Fisher-Yates permutation of ``[0, n)`` using the keystream.

        Port of the ``typeof pm == 'number'`` branch of ``stegShuffle``.
        JS reads ``randPool`` as ``Uint32Array`` little-endian; we do the
        same by taking the first ``n*4`` bytes and viewing them as LE
        u32.  The loop skips ``k = 0``.

        Returns an ``np.ndarray`` of ``int32`` — that's what
        ``Uint32Array`` becomes for our purposes since ``n`` fits.

        Uses a Python ``list`` for the working array in the hot loop:
        numpy indexing overhead per iteration dominates for n ~ 10⁶.
        """
        pool = self.pool
        if n * 4 > pool.size:
            raise ValueError(
                f"n={n} needs {n*4} bytes of keystream, "
                f"only {pool.size} available; raise max_pixels"
            )
        # LE u32 view of the first n*4 bytes. numpy is native-endian; on
        # all supported platforms that's LE. Force LE explicitly.
        rand32 = np.frombuffer(pool[: n * 4].tobytes(), dtype="<u4").tolist()

        pm = [0] * n
        for k in range(1, n):
            random_index = rand32[k] % (k + 1)
            if random_index != k:
                pm[k] = pm[random_index]
            pm[random_index] = k
        return np.asarray(pm, dtype=np.int32)

    def permute_in_place(self, arr: np.ndarray) -> np.ndarray:
        """Fisher-Yates shuffle applied to ``arr`` (mutated).

        Port of the ``else`` branch of ``stegShuffle`` — used by ``f5get``
        which passes the coefficient array itself.  Returns the same
        array for convenience.
        """
        n = arr.size
        pool = self.pool
        if n * 4 > pool.size:
            raise ValueError(
                f"array of size {n} needs {n*4} keystream bytes"
            )
        rand32 = np.frombuffer(pool[: n * 4].tobytes(), dtype="<u4").tolist()

        # Work in a Python list; assign back at the end.
        work = arr.tolist()
        for k in range(1, n):
            random_index = rand32[k] % (k + 1)
            work[k], work[random_index] = work[random_index], work[k]
        arr[:] = work
        return arr

    # ---- gamma ------------------------------------------------------------

    def gamma_at(self, l: int) -> np.ndarray:
        """Return the gamma tail: ``randPool[l*4:]`` as uint8 bytes.

        This mirrors the JS ``new Uint8Array(this.randPool, l*4)`` where
        ``l`` is the permutation length.  Callers index into the returned
        array with a running ``gammaI`` counter.
        """
        pool = self.pool
        offset = l * 4
        if offset > pool.size:
            raise ValueError(
                f"gamma offset {offset} beyond pool size {pool.size}"
            )
        return pool[offset:]
