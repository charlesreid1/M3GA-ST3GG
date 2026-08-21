"""Remove-whitespace — collapse every ``\\s+`` run to nothing.

Lossy (loses word boundaries), so ``can_decode=False``.
"""

from __future__ import annotations

import re

from ..base import BaseTransformer
from ..registry import register


_WS_RE = re.compile(r"\s+")


def _encode(text: str, **_: object) -> str:
    return _WS_RE.sub("", text)


remove_whitespace_transformer = BaseTransformer(
    name="Remove-Whitespace",
    category="format",
    priority=50,
    description="Strip every whitespace run.",
    func=_encode,
    can_decode=False,
    detector=None,
)
register(remove_whitespace_transformer)
