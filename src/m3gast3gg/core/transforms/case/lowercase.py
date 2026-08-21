"""Lowercase — trivial ``str.lower``.

Lossy (loses original case), so ``can_decode=False``.
"""

from __future__ import annotations

from ..base import BaseTransformer
from ..registry import register


def _encode(text: str, **_: object) -> str:
    return text.lower()


lowercase_transformer = BaseTransformer(
    name="Lowercase",
    category="case",
    priority=50,
    description="Lowercase all letters (str.lower).",
    func=_encode,
    can_decode=False,
    detector=None,
)
register(lowercase_transformer)
