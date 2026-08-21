"""Titlecase — trivial ``str.title``.

Lossy (loses original case + turns anomalies like ``it's`` into ``It'S``),
so ``can_decode=False``.
"""

from __future__ import annotations

from ..base import BaseTransformer
from ..registry import register


def _encode(text: str, **_: object) -> str:
    return text.title()


titlecase_transformer = BaseTransformer(
    name="Titlecase",
    category="case",
    priority=50,
    description="Capitalize first letter of each word (str.title).",
    func=_encode,
    can_decode=False,
    detector=None,
)
register(titlecase_transformer)
