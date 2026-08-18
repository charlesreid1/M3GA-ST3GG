"""Matrix-encoding core, dialect-agnostic.

Line-for-line port of ``_analyze`` (191–232), ``_f5write`` (234–392), and
the extraction loop of ``f5get`` (470–596) from ``f5stego-lib.js``.  This
module never touches keys or passwords — it takes a
:class:`PRNGBackend` protocol and lets the dialect classes bind their own
PRNG (RC4 for stegg, Java LCG for classic).

Coefficient array contract
--------------------------

Callers pass a flat int16 array where **positions divisible by 64 must be
zero**.  This mirrors the JS ``comp.blocks`` layout, where the DC
coefficient of each 8×8 block lives in a separate ``blocksDC`` array and
``blocks[i]`` at ``i % 64 === 0`` is unused (structurally zero).  Embed
uses ``i % 64 === 0`` as a "skip DC" fast test; extract skips zero
coefficients — so extract needs those DC positions to *read* as zero.
If they hold real DC values, extract picks up their LSBs and corrupts
the payload.

:class:`f5_core.f5_base.F5Base` handles staging jpeglib's ``Y`` array
into this shape: save the DCs, zero them, call embed/extract, restore.

Design constraint: the port is deliberately un-Pythonic in structure so
that reviewers can diff it against the JS.  Micro-optimising the shrinkage
retry loop into vectorised numpy would obscure the F5 matrix encoding.
"""

from __future__ import annotations

from typing import Protocol

import numpy as np

from ._errors import CapacityExceeded


class PRNGBackend(Protocol):
    """What ``_matrix`` needs from a dialect PRNG.

    Two shapes: build a fresh permutation of length ``n`` (for embed), or
    shuffle an existing array in place (for extract, where the JS calls
    ``stegShuffle(coeff)``).  Plus a gamma-tail accessor.
    """

    def permute_indices(self, n: int) -> np.ndarray: ...  # int32
    def permute_in_place(self, arr: np.ndarray) -> np.ndarray: ...
    def gamma_at(self, l: int) -> np.ndarray: ...  # uint8


# ---------------------------------------------------------------------------
# _analyze
# ---------------------------------------------------------------------------

def analyze(coeff: np.ndarray) -> dict:
    """Port of ``f5stego.prototype._analyze``.

    Returns a dict with a 17-element ``capacity`` list (index 0 unused,
    then k=1..16) plus per-class coefficient counts.  The formula is
    faithful to the JS including the ``| 0`` truncations and integer
    overflow semantics of JS bitwise ops.

    F5 targets AC coefficients only; ``i % 64 === 0`` (DC) is skipped.
    """
    coeff = coeff.reshape(-1)
    n = coeff.size

    # DC positions to skip.
    dc_mask = (np.arange(n) % 64) == 0

    ac = coeff[~dc_mask]
    _zero = int(np.count_nonzero(ac == 0))
    _one = int(np.count_nonzero((ac == 1) | (ac == -1)))
    _large = n - _zero - _one - (n // 64)   # JS: coeff.length / 64 (integer since len%64==0 in practice)

    denom = _large + _one
    _ratio = (_one / denom) if denom else 0.0

    res = {
        "capacity": [0] * 17,
        "coeff_total": n,
        "coeff_large": _large,
        "coeff_zero": _zero,
        "coeff_one": _one,
        "coeff_one_ratio": _ratio,
    }

    # k = 1 capacity.  JS: ((_large + 0.49 * _one) >> 3) - 1.
    # >> 3 in JS is a signed 32-bit shift-truncate, i.e. int-divide-by-8 for
    # non-negative operands.  We match by floor-dividing after truncation.
    res["capacity"][1] = int(_large + 0.49 * _one) // 8 - 1

    # k = 2..16.  Port of the exact JS loop, including the ``| 0`` truncations
    # that JS uses as "floor to int32".
    for i in range(2, 17):
        k = (1 << i) - 1
        usable = _large + _one
        embedded = 0
        while usable > k:
            matched = int(usable / k / (1 << i) / (1 << i))          # | 0
            usable -= matched * k
            changed = int(usable * (1 - _ratio) / k * 0.96)          # | 0
            usable -= changed * k
            embedded += changed + matched
            k += 1
        res["capacity"][i] = (i * embedded) // 8 - 1                 # JS: >> 3

    return res


# ---------------------------------------------------------------------------
# _f5write
# ---------------------------------------------------------------------------

def embed_coefficients(
    coeff: np.ndarray,
    data: bytes,
    k: int,
    prng: PRNGBackend,
) -> dict:
    """Port of ``f5stego.prototype._f5write``.

    Mutates ``coeff`` in place.  Returns a stats dict with the same keys
    the JS returned: ``k``, ``embedded``, ``examined``, ``changed``,
    ``thrown``, ``efficiency``.

    Raises :class:`CapacityExceeded` when the JS would ``throw 'capacity
    exceeded ...'`` — either the k=1 fast path can't fit all the bits, or
    the matrix path runs off the end of the permutation looking for a
    code word.
    """
    if coeff.dtype != np.int16:
        # F5 semantics need signed 16-bit wraparound behaviour and the
        # int16 dtype ensures ``coeff[...] -= 1`` etc. keeps the right
        # width for downstream JPEG re-encoding.
        raise TypeError(f"coeff must be int16; got {coeff.dtype}")

    coeff_count = coeff.size
    _changed = 0
    _embedded = 0
    _examined = 0
    _thrown = 0

    pm = prng.permute_indices(coeff_count)
    gamma = prng.gamma_at(coeff_count)
    gammaI = 0

    n = (1 << k) - 1

    # JS: byte_to_embed = k - 1;  byte_to_embed ^= gamma[gammaI++];
    byte_to_embed = k - 1
    byte_to_embed ^= int(gamma[gammaI]); gammaI += 1
    next_bit_to_embed = byte_to_embed & 1
    byte_to_embed >>= 1
    available_bits_to_embed = 3

    data_idx = 0
    data_len = len(data)

    ii = -1  # will be pre-incremented in the shrinkage loop; the top loop uses ``ii = 0`` fresh
    # Top-level pass — mirror of the JS for-loop over ii = 0..coeff_count.
    ii = 0
    while ii < coeff_count:
        shuffled_index = int(pm[ii])

        if shuffled_index % 64 == 0 or coeff[shuffled_index] == 0:
            ii += 1
            continue

        cc = int(coeff[shuffled_index])
        _examined += 1

        if cc > 0 and (cc & 1) != next_bit_to_embed:
            coeff[shuffled_index] = np.int16(cc - 1)
            _changed += 1
        elif cc < 0 and (cc & 1) == next_bit_to_embed:
            coeff[shuffled_index] = np.int16(cc + 1)
            _changed += 1

        if coeff[shuffled_index] != 0:
            _embedded += 1
            if available_bits_to_embed == 0:
                # k == 1 fast-path exit condition: run out of data.
                if k != 1 or data_idx >= data_len:
                    break
                byte_to_embed = data[data_idx]; data_idx += 1
                byte_to_embed ^= int(gamma[gammaI]); gammaI += 1
                available_bits_to_embed = 8
            next_bit_to_embed = byte_to_embed & 1
            byte_to_embed >>= 1
            available_bits_to_embed -= 1
        else:
            _thrown += 1
        ii += 1

    # k == 1 short-circuit — everything is embedded in the top loop.
    if k == 1 and _embedded < data_len * 8:
        raise CapacityExceeded(
            f"k=1: only embedded {_embedded / 8:.2f} of {data_len} bytes"
        )

    if k != 1:
        # Matrix-encoding pass — shrinkage retry loop.
        # ``ii`` is where the top-level loop broke out; do not reset.
        is_last_byte = False
        while (not is_last_byte) or (available_bits_to_embed != 0 and is_last_byte):
            k_bits_to_embed = 0

            for i in range(k):
                if available_bits_to_embed == 0:
                    if data_idx >= data_len:
                        is_last_byte = True
                        break
                    byte_to_embed = data[data_idx]; data_idx += 1
                    byte_to_embed ^= int(gamma[gammaI]); gammaI += 1
                    available_bits_to_embed = 8
                next_bit_to_embed = byte_to_embed & 1
                byte_to_embed >>= 1
                available_bits_to_embed -= 1
                k_bits_to_embed |= next_bit_to_embed << i

            code_word: list[int] = []
            ci = -1

            # Fill the code word with n usable coefficient positions.
            for _ in range(n):
                while True:
                    ii += 1
                    if ii >= coeff_count:
                        raise CapacityExceeded(
                            f"exhausted coefficients while filling code word "
                            f"(embedded {_embedded / 8:.2f} bytes)"
                        )
                    ci = int(pm[ii])
                    if ci % 64 != 0 and coeff[ci] != 0:
                        break
                code_word.append(ci)
            _examined += n

            # Retry loop: hash the code word, XOR into what we want to embed,
            # decrement the offending coefficient by 1 (toward zero) until
            # hash == k_bits_to_embed.
            while True:
                vhash = 0
                for i, pos in enumerate(code_word):
                    v = int(coeff[pos])
                    if v > 0:
                        extracted_bit = v & 1
                    else:
                        extracted_bit = 1 - (v & 1)
                    if extracted_bit == 1:
                        vhash ^= i + 1

                i = vhash ^ k_bits_to_embed
                if not i:
                    _embedded += k
                    break

                i -= 1
                v = int(coeff[code_word[i]])
                coeff[code_word[i]] = np.int16(v + (1 if v < 0 else -1))
                _changed += 1

                if coeff[code_word[i]] == 0:
                    _thrown += 1
                    code_word.pop(i)
                    # Refill the code word with a fresh usable coefficient.
                    while True:
                        ii += 1
                        if ii >= coeff_count:
                            raise CapacityExceeded(
                                f"exhausted coefficients during shrinkage "
                                f"(embedded {_embedded / 8:.2f} bytes)"
                            )
                        ci = int(pm[ii])
                        if ci % 64 != 0 and coeff[ci] != 0:
                            break
                    _examined += 1
                    code_word.append(ci)
                else:
                    _embedded += k
                    break

    efficiency = f"{(_embedded / _changed):.2f}" if _changed else "0.00"
    return {
        "k": k,
        "embedded": _embedded / 8,
        "examined": _examined,
        "changed": _changed,
        "thrown": _thrown,
        "efficiency": efficiency,
    }


# ---------------------------------------------------------------------------
# f5get — extraction
# ---------------------------------------------------------------------------

def extract_raw(coeff: np.ndarray, prng: PRNGBackend) -> bytes:
    """Port of the extraction half of ``f5stego.prototype.f5get``.

    Returns the raw framed byte stream — length prefix decode lives in
    the dialect class (:meth:`f5_core.f5_base.F5Base._unframe`), not
    here, so the matrix layer stays dialect-agnostic.
    """
    # JS: coeff = new Int16Array(comp.blocks.length);  coeff.set(comp.blocks);
    # We take a defensive copy — extract must not mutate the JPEG we
    # were handed.
    coeff = np.array(coeff.reshape(-1), dtype=np.int16, copy=True)
    cCount = coeff.size - 1

    # Note: stegShuffle here uses the *coeff-length* array branch — the JS
    # passes ``coeff`` itself, so the shuffle mutates coeff.  We pass a
    # dummy int32 array of the same length; only its length matters for
    # gamma offset computation.  The coeff mutation in the JS is a no-op
    # for extraction because we read coeff[pos] before the shuffle
    # reordering matters — wait: read that again.  JS:
    #   var pm = this.stegShuffle(coeff), gamma = pm.gamma;
    # then reads coeff[pos] in the main loop.  The shuffle *does* reorder
    # coeff, and the extract loop walks coeff sequentially by pos.  So
    # the shuffle IS the permutation, applied to coeff in place.
    prng.permute_in_place(coeff)
    gamma = prng.gamma_at(coeff.size)
    gammaI = 0

    pos = -1
    bitsAvail = 0
    k = 0

    # Recover k (4 bits) from the first 4 non-zero coefficients.
    while bitsAvail < 4:
        pos += 1
        if coeff[pos] == 0:
            continue
        extrBit = int(coeff[pos]) & 1
        if coeff[pos] < 0:
            extrBit = 1 - extrBit
        k |= extrBit << bitsAvail
        bitsAvail += 1

    k = (k ^ (int(gamma[gammaI]) & 15)) + 1; gammaI += 1
    n = (1 << k) - 1

    out = bytearray(coeff.size // 8)
    outPos = 0
    extrByte = 0
    bitsAvail = 0
    code = 0
    vhash = 0

    if k == 1:
        while pos < cCount:
            pos += 1
            if coeff[pos] == 0:
                continue
            extrBit = int(coeff[pos]) & 1
            if coeff[pos] < 0:
                extrBit = 1 - extrBit
            extrByte |= extrBit << bitsAvail
            bitsAvail += 1
            if bitsAvail == 8:
                out[outPos] = (extrByte ^ int(gamma[gammaI])) & 0xFF; gammaI += 1
                outPos += 1
                extrByte = 0
                bitsAvail = 0
    else:
        while pos < cCount:
            pos += 1
            if coeff[pos] == 0:
                continue
            extrBit = int(coeff[pos]) & 1
            if coeff[pos] < 0:
                extrBit = 1 - extrBit
            code += 1
            vhash ^= extrBit * code
            if code == n:
                extrByte |= vhash << bitsAvail
                bitsAvail += k
                code = 0
                vhash = 0
                while bitsAvail >= 8:
                    out[outPos] = (extrByte & 0xFF) ^ int(gamma[gammaI]); gammaI += 1
                    outPos += 1
                    bitsAvail -= 8
                    extrByte >>= 8

    while bitsAvail > 0:
        out[outPos] = (extrByte & 0xFF) ^ int(gamma[gammaI]); gammaI += 1
        outPos += 1
        bitsAvail -= 8
        extrByte >>= 8

    return bytes(out[:outPos])
