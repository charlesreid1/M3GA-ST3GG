"""Ternary — 6 base-3 digits per UTF-8 byte.

M3GA-native transform (P4RS3LT0NGV3 has no counterpart). Included in the
inventory as one of the small handful of Python-native additions.
"""

from __future__ import annotations

import re

from ..base import BaseTransformer
from ..registry import register
from ._base_n import base_n_decode, base_n_encode


_TERNARY_RE = re.compile(r"^[012\s]+$")


def _encode(text: str, **_: object) -> str:
    return base_n_encode(text, 3)


def _decode(text: str, **_: object) -> str:
    return base_n_decode(text, 3)


def _detect(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 6:
        return False
    return bool(_TERNARY_RE.match(stripped)) and len(stripped.replace(" ", "")) % 6 == 0


ternary_transform = BaseTransformer(
    name="Ternary",
    category="encoding",
    priority=70,
    description="Ternary — 6 base-3 digits per UTF-8 byte.",
    func=_encode,
    reverse=_decode,
    detector=_detect,
)
register(ternary_transform)
