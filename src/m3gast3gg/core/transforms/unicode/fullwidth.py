"""Fullwidth — map printable ASCII to U+FF01–U+FF5E fullwidth forms.

Space (0x20) maps to U+3000. Everything else passes through unchanged.

Transport survivability: survives Slack, Discord, raw HTTP, email, GitHub.
Dies under NFKC normalization (U+FF01 → ASCII `!`), which many search boxes,
some database columns, and some LLM tokenizers apply.
"""

from __future__ import annotations

from ..base import BaseTransformer
from ..registry import register


def _encode(text: str, **_: object) -> str:
    out = []
    for ch in text:
        cp = ord(ch)
        if 0x21 <= cp <= 0x7E:
            out.append(chr(cp + 0xFEE0))
        elif cp == 0x20:
            out.append('　')
        else:
            out.append(ch)
    return "".join(out)


def _decode(text: str, **_: object) -> str:
    out = []
    for ch in text:
        cp = ord(ch)
        if 0xFF01 <= cp <= 0xFF5E:
            out.append(chr(cp - 0xFEE0))
        elif cp == 0x3000:
            out.append(" ")
        else:
            out.append(ch)
    return "".join(out)


def _detect(text: str) -> bool:
    return any(0xFF01 <= ord(ch) <= 0xFF5E or ord(ch) == 0x3000 for ch in text)


fullwidth_transformer = BaseTransformer(
    name="Fullwidth",
    category="unicode",
    priority=85,
    description="Fullwidth Latin — printable ASCII shifted to the U+FF01–U+FF5E block.",
    func=_encode,
    reverse=_decode,
    detector=_detect,
)
register(fullwidth_transformer)
