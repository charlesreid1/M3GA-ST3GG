"""Quoted-Printable encoding (RFC 2045 §6.7).

Common in MIME email bodies. Non-ASCII bytes become ``=XX``; long lines get
soft-broken with ``=\\r\\n``.
"""

from __future__ import annotations

import quopri
import re

from ..base import BaseTransformer
from ..registry import register


_QP_RE = re.compile(r"=[0-9A-F]{2}")


def _encode(text: str, **_: object) -> str:
    return quopri.encodestring(text.encode("utf-8"), quotetabs=False).decode("ascii")


def _decode(text: str, **_: object) -> str:
    return quopri.decodestring(text.encode("ascii")).decode("utf-8")


def _detect(text: str) -> bool:
    matches = _QP_RE.findall(text)
    return len(matches) >= 1


quoted_printable_transformer = BaseTransformer(
    name="Quoted-Printable",
    category="encoding",
    priority=70,
    description="Quoted-Printable encoding (RFC 2045 §6.7) — MIME-era.",
    func=_encode,
    reverse=_decode,
    detector=_detect,
)
register(quoted_printable_transformer)
