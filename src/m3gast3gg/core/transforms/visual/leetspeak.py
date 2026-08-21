"""Leetspeak — digit/symbol substitutions for letters.

Transport survivability: universal. Pure ASCII output.

Round-trip: lossy — leetspeak substitutions collide (both 'l' and 'i' → '1'
under moderate intensity). Reverse recovers the most-common letter for each
sub, which is right for round-trip against the *original* ASCII text after
NFKC-lowercasing, but wrong in the general case. Listed in
LOSSY_TRANSFORMS.
"""

from __future__ import annotations

import random

from ..base import BaseTransformer, ConfigurableOption
from ..registry import register


_BASIC = {'a': '4', 'e': '3', 'i': '1', 'o': '0', 's': '5', 't': '7'}
_MODERATE = {**_BASIC, 'b': '8', 'g': '9', 'l': '1', 'z': '2'}
_HEAVY = {**_MODERATE, 'c': '(', 'd': '|)', 'h': '|-|', 'k': '|<', 'n': '|\\|',
          'u': '|_|', 'v': '\\/', 'w': '\\/\\/', 'x': '><', 'y': '`/'}


def _encode(text: str, intensity: int = 2, **_: object) -> str:
    mappings = [_BASIC, _MODERATE, _HEAVY][min(intensity, 3) - 1]
    result = []
    for char in text:
        lower = char.lower()
        if lower in mappings and random.random() < 0.7:
            result.append(mappings[lower])
        else:
            result.append(char)
    return "".join(result)


_REVERSE_HEAVY = {v: k for k, v in _HEAVY.items()}


def _decode(text: str, **_: object) -> str:
    for token in sorted(_REVERSE_HEAVY, key=len, reverse=True):
        text = text.replace(token, _REVERSE_HEAVY[token])
    return text


def _detect(text: str) -> bool:
    if not text:
        return False
    digit_ratio = sum(1 for ch in text if ch in "01345789") / len(text)
    letter_ratio = sum(1 for ch in text if ch.isalpha()) / len(text)
    return digit_ratio > 0.15 and letter_ratio > 0.3


leetspeak_transformer = BaseTransformer(
    name="Leetspeak",
    category="visual",
    priority=50,
    description="Leetspeak — digit/symbol substitutions for letters.",
    func=_encode,
    reverse=_decode,
    detector=_detect,
    configurable_options=[
        ConfigurableOption(
            id="intensity", label="Intensity",
            type="number", default=2, min=1, max=3, step=1,
        ),
    ],
)
register(leetspeak_transformer)
