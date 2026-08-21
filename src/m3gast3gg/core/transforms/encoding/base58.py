"""Base58 (Bitcoin / IPFS variant).

Alphabet ``123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz`` —
omits 0/O/I/l to avoid visual confusion. Encodes leading zero bytes as
leading ``1`` chars. Round-trip via bignum + leading-1 count.
"""

from __future__ import annotations

import re

from ..base import BaseTransformer
from ..registry import register


ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_INDEX = {c: i for i, c in enumerate(ALPHABET)}
_BASE58_RE = re.compile(r"^[123456789A-HJ-NP-Za-km-z]+$")


def _encode(text: str, **_: object) -> str:
    data = text.encode("utf-8")
    if not data:
        return ""
    n = int.from_bytes(data, "big")
    out = ""
    while n > 0:
        n, r = divmod(n, 58)
        out = ALPHABET[r] + out
    zero_prefix = 0
    for b in data:
        if b == 0:
            zero_prefix += 1
        else:
            break
    return ALPHABET[0] * zero_prefix + out


def _decode(text: str, **_: object) -> str:
    if not text:
        return ""
    n = 0
    for c in text:
        if c not in _INDEX:
            raise ValueError(f"base58: invalid character {c!r}")
        n = n * 58 + _INDEX[c]
    zero_prefix = 0
    for c in text:
        if c == ALPHABET[0]:
            zero_prefix += 1
        else:
            break
    body = n.to_bytes((n.bit_length() + 7) // 8, "big") if n > 0 else b""
    return (b"\x00" * zero_prefix + body).decode("utf-8")


def _detect(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 4:
        return False
    return bool(_BASE58_RE.match(stripped))


base58_transformer = BaseTransformer(
    name="Base58",
    category="encoding",
    priority=270,
    description="Base58 (Bitcoin/IPFS variant) — no 0/O/I/l for visual clarity.",
    func=_encode,
    reverse=_decode,
    detector=_detect,
)
register(base58_transformer)
