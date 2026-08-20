"""ROT13 — Caesar with a fixed shift of 13.

Involutive: rot13(rot13(x)) == x. Not encryption. Kept because it's the
one every CTF and IRC user still hits by reflex.
"""

from __future__ import annotations

import codecs

from ..base import BaseTransformer
from ..registry import register


def _rot13(text: str, **_: object) -> str:
    return codecs.encode(text, "rot_13")


rot13_transformer = BaseTransformer(
    name="ROT13",
    category="cipher",
    priority=60,
    description="Caesar cipher with a shift of 13 (self-inverse).",
    func=_rot13,
    reverse=_rot13,
    detector=None,
)
register(rot13_transformer)
