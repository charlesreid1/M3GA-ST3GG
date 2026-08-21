"""Zero-width steganography — hide the input in invisible ZWJ/ZWSP/ZWNJ bits.

Thin bridge around ``m3gast3gg.core.text.encode_zero_width`` /
``decode_zero_width``. The transform's ``func(text, cover=...)`` returns a
carrier string with ``text`` embedded as a zero-width bitstring inside
``cover``. Default cover is a short filler so the transform is usable from
the CLI without a separate ``--cover`` argument.
"""

from __future__ import annotations

from m3gast3gg.core import text as _text

from ..base import BaseTransformer, ConfigurableOption
from ..registry import register


_DEFAULT_COVER = "carrier text"


def _encode(text: str, cover: str = _DEFAULT_COVER, **_: object) -> str:
    return _text.encode_zero_width(cover or _DEFAULT_COVER, text)


def _decode(text: str, **_: object) -> str:
    return _text.decode_zero_width(text)


def _detect(text: str) -> bool:
    return any(c in text for c in (_text.ZWJ, _text.ZWSP, _text.ZWNJ))


zero_width_transformer = BaseTransformer(
    name="Zero-Width",
    category="concealment",
    priority=1,
    description="Hide the input as a zero-width (ZWJ/ZWSP/ZWNJ) bitstring inside a cover.",
    func=_encode,
    reverse=_decode,
    detector=_detect,
    configurable_options=[
        ConfigurableOption(
            id="cover", label="Cover text (any non-empty string)",
            type="text", default=_DEFAULT_COVER,
        ),
    ],
)
register(zero_width_transformer)
