"""Binary — 8 bits per UTF-8 byte, no separators.

Transport survivability: universal. Members of `[01]` only.
"""

from __future__ import annotations

import re

from ..base import BaseTransformer
from ..registry import register
from ._base_n import base_n_decode, base_n_encode


_BINARY_RE = re.compile(r"^[01\s]+$")


def _encode(text: str, **_: object) -> str:
    return base_n_encode(text, 2)


def _decode(text: str, **_: object) -> str:
    return base_n_decode(text, 2)


def _detect(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 8:
        return False
    return bool(_BINARY_RE.match(stripped)) and len(stripped.replace(" ", "")) % 8 == 0


binary_transform = BaseTransformer(
    name="Binary",
    category="encoding",
    priority=300,
    description="Binary — 8 bits per UTF-8 byte.",
    func=_encode,
    reverse=_decode,
    detector=_detect,
)
register(binary_transform)
