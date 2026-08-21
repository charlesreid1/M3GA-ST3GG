"""Caesar cipher — classic alphabet shift.

Encode/decode are the same operation with opposite shifts. Not encryption —
the keyspace is 25. Preserved for CTF work, jailbreak-obfuscation chains, and
"what shift is this" universal-decode candidates.
"""

from __future__ import annotations

from ..base import BaseTransformer, ConfigurableOption
from ..registry import register


def _shift(text: str, shift: int) -> str:
    s = ((shift % 26) + 26) % 26
    out = []
    for c in text:
        code = ord(c)
        if 0x41 <= code <= 0x5A:
            out.append(chr((code - 65 + s) % 26 + 65))
        elif 0x61 <= code <= 0x7A:
            out.append(chr((code - 97 + s) % 26 + 97))
        else:
            out.append(c)
    return "".join(out)


def _encode(text: str, shift: int = 3, **_: object) -> str:
    return _shift(text, shift)


def _decode(text: str, shift: int = 3, **_: object) -> str:
    return _shift(text, -shift)


caesar_transformer = BaseTransformer(
    name="Caesar",
    category="cipher",
    priority=60,
    description="Classic alphabet shift (configurable, default 3).",
    func=_encode,
    reverse=_decode,
    detector=None,
    configurable_options=[
        ConfigurableOption(
            id="shift", label="Shift (1-25)",
            type="number", default=3, min=1, max=25, step=1,
        ),
    ],
)
register(caesar_transformer)
