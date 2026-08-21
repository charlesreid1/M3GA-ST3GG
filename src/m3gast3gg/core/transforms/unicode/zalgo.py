"""Zalgo — stack random combining marks above/below/through each alphanumeric.

Transport survivability: survives most channels (Slack, Discord, raw HTTP,
email, GitHub). Dies under aggressive combining-mark stripping and under
terminal mouse-copy (visible glyph stream only).

Round-trip: NFKC-normalization strips combining marks, so the reverse is
"strip combining marks in the U+0300–U+036F range and related zalgo blocks".
Lossy on inputs that legitimately contain those marks — those inputs are
listed under LOSSY_TRANSFORMS in the round-trip tests.
"""

from __future__ import annotations

import random
import unicodedata

from ..base import BaseTransformer, ConfigurableOption
from ..registry import register


ZALGO_CHARS = {
    'above': [
        '̀', '́', '̂', '̃', '̄', '̅', '̆', '̇',
        '̈', '̉', '̊', '̋', '̌', '̍', '̎', '̏',
        '̐', '̑', '̒', '̓', '̔', '̕', '̚', '̛',
        '̽', '̾', '̿', '̀', '́', '͂', '̓', '̈́',
        '͆', '͊', '͋', '͌', '͐', '͑', '͒', '͗',
        '͛', 'ͣ', 'ͤ', 'ͥ', 'ͦ', 'ͧ', 'ͨ', 'ͩ',
        'ͪ', 'ͫ', 'ͬ', 'ͭ', 'ͮ', 'ͯ',
    ],
    'below': [
        '̖', '̗', '̘', '̙', '̜', '̝', '̞', '̟',
        '̠', '̡', '̢', '̣', '̤', '̥', '̦', '̧',
        '̨', '̩', '̪', '̫', '̬', '̭', '̮', '̯',
        '̰', '̱', '̲', '̳', '̹', '̺', '̻', '̼',
        'ͅ', '͇', '͈', '͉', '͍', '͎', '͓', '͔',
        '͕', '͖', '͙', '͚', '͜', '͟', '͢',
    ],
    'middle': [
        '̴', '̵', '̶', '̷', '̸', '͘',
    ],
}


def _encode(text: str, intensity: int = 3, **_: object) -> str:
    result = []
    for char in text:
        result.append(char)
        if char.isalnum():
            for _ in range(random.randint(0, intensity)):
                result.append(random.choice(ZALGO_CHARS['above']))
            for _ in range(random.randint(0, intensity)):
                result.append(random.choice(ZALGO_CHARS['below']))
            for _ in range(random.randint(0, max(1, intensity // 2))):
                result.append(random.choice(ZALGO_CHARS['middle']))
    return ''.join(result)


def _decode(text: str, **_: object) -> str:
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def _detect(text: str) -> bool:
    return any(unicodedata.category(ch) == "Mn" for ch in text) and \
        sum(1 for ch in text if unicodedata.category(ch) == "Mn") >= 2


zalgo_transformer = BaseTransformer(
    name="Zalgo",
    category="unicode",
    priority=85,
    description="Zalgo — stack random combining marks over each alphanumeric.",
    func=_encode,
    reverse=_decode,
    detector=_detect,
    configurable_options=[
        ConfigurableOption(
            id="intensity", label="Intensity",
            type="number", default=3, min=1, max=10, step=1,
        ),
    ],
)
register(zalgo_transformer)
