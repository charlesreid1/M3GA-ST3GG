"""Homoglyph — replace Latin letters with visually-identical Cyrillic ones.

Direct 1:1 substitution using ``m3gast3gg.core.text.CYRILLIC_HOMOGLYPH_MAP``.
This is the *visible* homoglyph transform (visually indistinguishable, but a
byte-level diff catches it immediately). Distinct from the steg version in
``core.text.encode_cyrillic_homoglyph`` which hides bits by choosing per-char.

Survivability: dies under NFKC normalization; survives Slack/Discord/email/
GitHub.
"""

from __future__ import annotations

from m3gast3gg.core.text import CYRILLIC_HOMOGLYPH_MAP, CYRILLIC_HOMOGLYPH_REVERSE

from ..base import BaseTransformer
from ..registry import register


def _encode(text: str, **_: object) -> str:
    return "".join(CYRILLIC_HOMOGLYPH_MAP.get(c, c) for c in text)


def _decode(text: str, **_: object) -> str:
    return "".join(CYRILLIC_HOMOGLYPH_REVERSE.get(c, c) for c in text)


def _detect(text: str) -> bool:
    return any(c in CYRILLIC_HOMOGLYPH_REVERSE for c in text)


homoglyph_transformer = BaseTransformer(
    name="Homoglyph",
    category="concealment",
    priority=100,
    description="Latin → Cyrillic visual look-alikes (a→а, c→с, e→е, ...).",
    func=_encode,
    reverse=_decode,
    detector=_detect,
)
register(homoglyph_transformer)
