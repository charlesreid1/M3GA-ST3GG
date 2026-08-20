"""Base64 — standard RFC 4648 encoding.

Transport survivability: universal. Pure ASCII, survives every transport
including NFKC normalization. Round-trip via ``base64.b64decode``.
"""

from __future__ import annotations

import base64 as _b64
import re

from ..base import BaseTransformer
from ..registry import register


_BASE64_RE = re.compile(r"^[A-Za-z0-9+/]+={0,2}$")


def _encode(text: str, **_: object) -> str:
    return _b64.b64encode(text.encode("utf-8")).decode("ascii")


def _decode(text: str, **_: object) -> str:
    return _b64.b64decode(text.encode("ascii")).decode("utf-8")


def _detect(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 4 or len(stripped) % 4 != 0:
        return False
    return bool(_BASE64_RE.match(stripped))


base64_transform = BaseTransformer(
    name="Base64",
    category="encoding",
    priority=270,
    description="Standard RFC 4648 Base64 encoding of UTF-8 bytes.",
    func=_encode,
    reverse=_decode,
    detector=_detect,
)
register(base64_transform)
