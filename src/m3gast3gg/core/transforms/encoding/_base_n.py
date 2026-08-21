"""Shared base-N encoder for binary, ternary, and hex.

Each UTF-8 byte becomes exactly ``ceil(8 / log2(base))`` digits from the
lowercase alphabet ``0-9a-f`` (truncated to ``base`` digits). Fixed-width
padding makes the output unambiguous to decode.
"""

from __future__ import annotations

import math

_DIGITS = "0123456789abcdef"


def base_n_encode(text: str, base: int) -> str:
    if not isinstance(base, int) or base < 2 or base > 16:
        raise ValueError(f"base must be an integer in 2..16, got {base!r}")
    width = math.ceil(8 / math.log2(base))
    alphabet = _DIGITS[:base]
    out = []
    for byte in text.encode("utf-8"):
        digits = []
        n = byte
        for _ in range(width):
            digits.append(alphabet[n % base])
            n //= base
        out.append("".join(reversed(digits)))
    return "".join(out)


def base_n_decode(text: str, base: int) -> str:
    if not isinstance(base, int) or base < 2 or base > 16:
        raise ValueError(f"base must be an integer in 2..16, got {base!r}")
    width = math.ceil(8 / math.log2(base))
    alphabet = _DIGITS[:base]
    lookup = {c: i for i, c in enumerate(alphabet)}
    stripped = "".join(text.split())
    if len(stripped) % width != 0:
        raise ValueError(
            f"base-{base} input length {len(stripped)} is not a multiple of {width}"
        )
    out = bytearray()
    for i in range(0, len(stripped), width):
        chunk = stripped[i:i + width]
        n = 0
        for ch in chunk:
            if ch not in lookup:
                raise ValueError(f"invalid base-{base} digit {ch!r}")
            n = n * base + lookup[ch]
        if n > 255:
            raise ValueError(f"base-{base} chunk decodes to {n} > 255")
        out.append(n)
    return out.decode("utf-8")
