"""Atbash — reverse the alphabet (A↔Z, B↔Y, ...).

Involutive; no key. Not encryption.
"""

from __future__ import annotations

from ..base import BaseTransformer
from ..registry import register


def _atbash(text: str, **_: object) -> str:
    out = []
    for c in text:
        code = ord(c)
        if 0x41 <= code <= 0x5A:
            out.append(chr(0x5A - (code - 0x41)))
        elif 0x61 <= code <= 0x7A:
            out.append(chr(0x7A - (code - 0x61)))
        else:
            out.append(c)
    return "".join(out)


atbash_transformer = BaseTransformer(
    name="Atbash",
    category="cipher",
    priority=60,
    description="Reverse-alphabet cipher (A↔Z). Self-inverse.",
    func=_atbash,
    reverse=_atbash,
    detector=None,
)
register(atbash_transformer)
