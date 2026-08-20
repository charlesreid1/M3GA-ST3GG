"""Base32 — standard RFC 4648 uppercase encoding.

Transport survivability: universal. Case-insensitive alphabet ``A-Z 2-7``.
"""

from __future__ import annotations

import base64 as _b64
import re

from ..base import BaseTransformer
from ..registry import register


_BASE32_RE = re.compile(r"^[A-Z2-7]+=*$")


def _encode(text: str, **_: object) -> str:
    return _b64.b32encode(text.encode("utf-8")).decode("ascii")


def _decode(text: str, **_: object) -> str:
    return _b64.b32decode(text.encode("ascii")).decode("utf-8")


def _detect(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 8 or len(stripped) % 8 != 0:
        return False
    return bool(_BASE32_RE.match(stripped))


base32_transform = BaseTransformer(
    name="Base32",
    category="encoding",
    priority=280,
    description="Standard RFC 4648 Base32 encoding of UTF-8 bytes.",
    func=_encode,
    reverse=_decode,
    detector=_detect,
)
register(base32_transform)
