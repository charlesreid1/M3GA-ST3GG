"""Hex — 2 lowercase base-16 digits per UTF-8 byte.

Transport survivability: universal.
"""

from __future__ import annotations

import re

from ..base import BaseTransformer
from ..registry import register
from ._base_n import base_n_decode, base_n_encode


_HEX_RE = re.compile(r"^[0-9a-fA-F\s]+$")


def _encode(text: str, **_: object) -> str:
    return base_n_encode(text, 16)


def _decode(text: str, **_: object) -> str:
    return base_n_decode(text.lower(), 16)


def _detect(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 2:
        return False
    condensed = stripped.replace(" ", "")
    return bool(_HEX_RE.match(stripped)) and len(condensed) % 2 == 0


hex_transform = BaseTransformer(
    name="Hex",
    category="encoding",
    priority=290,
    description="Hexadecimal — 2 lowercase digits per UTF-8 byte.",
    func=_encode,
    reverse=_decode,
    detector=_detect,
)
register(hex_transform)
