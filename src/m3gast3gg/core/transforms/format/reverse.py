"""Reverse — reverse the string by Unicode code points.

Note: combining marks are reversed too, so a base-glyph + combining-mark pair
becomes combining-mark + base-glyph and may render oddly. For pre-obfuscation
of ASCII payloads this is a non-issue. Involutive: reverse ∘ reverse = id.
"""

from __future__ import annotations

from ..base import BaseTransformer
from ..registry import register


def _encode(text: str, **_: object) -> str:
    return text[::-1]


reverse_transformer = BaseTransformer(
    name="Reverse",
    category="format",
    priority=50,
    description="Reverse the string by Unicode code points.",
    func=_encode,
    reverse=_encode,
)
register(reverse_transformer)
