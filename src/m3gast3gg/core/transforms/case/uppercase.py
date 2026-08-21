"""Uppercase — trivial ``str.upper``.

Lossy (loses original case), so ``can_decode=False``.
"""

from __future__ import annotations

from ..base import BaseTransformer
from ..registry import register


def _encode(text: str, **_: object) -> str:
    return text.upper()


uppercase_transformer = BaseTransformer(
    name="Uppercase",
    category="case",
    priority=50,
    description="Uppercase all letters (str.upper).",
    func=_encode,
    can_decode=False,
    detector=None,
)
register(uppercase_transformer)
