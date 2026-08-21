"""ASCII85 (Base85) — 4 bytes → 5 ASCII characters.

Denser than base64, uses printable ASCII in the 33..117 range. No standard
delimiters here — round-trip via ``base64.a85decode``.
"""

from __future__ import annotations

import base64 as _b64
import re

from ..base import BaseTransformer
from ..registry import register


_ASCII85_RE = re.compile(r"^[!-u\s]+$")


def _encode(text: str, **_: object) -> str:
    return _b64.a85encode(text.encode("utf-8")).decode("ascii")


def _decode(text: str, **_: object) -> str:
    return _b64.a85decode(text.encode("ascii")).decode("utf-8")


def _detect(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 5:
        return False
    if not _ASCII85_RE.match(stripped):
        return False
    return any(0x21 <= ord(c) <= 0x75 and not c.isalnum() for c in stripped)


ascii85_transformer = BaseTransformer(
    name="ASCII85",
    category="encoding",
    priority=70,
    description="ASCII85 (Base85) encoding — 4 bytes → 5 printable ASCII chars.",
    func=_encode,
    reverse=_decode,
    detector=_detect,
)
register(ascii85_transformer)
