"""URL percent-encoding (RFC 3986).

Non-unreserved bytes become ``%XX``. UTF-8 input, ASCII output.
"""

from __future__ import annotations

import re
import urllib.parse

from ..base import BaseTransformer
from ..registry import register


_URL_ENCODED_RE = re.compile(r"%[0-9A-Fa-f]{2}")


def _encode(text: str, **_: object) -> str:
    return urllib.parse.quote(text, safe="")


def _decode(text: str, **_: object) -> str:
    return urllib.parse.unquote(text)


def _detect(text: str) -> bool:
    matches = _URL_ENCODED_RE.findall(text)
    return len(matches) >= 1 and len(text) >= 3


url_transformer = BaseTransformer(
    name="URL",
    category="encoding",
    priority=70,
    description="URL percent-encoding (RFC 3986).",
    func=_encode,
    reverse=_decode,
    detector=_detect,
)
register(url_transformer)
