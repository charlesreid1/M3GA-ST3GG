"""Invisible-text via Unicode Tag block — hide ASCII in U+E0020..U+E007E.

Thin bridge around ``m3gast3gg.core.unicode_tags.encode_tag_run`` /
``decode_tag_run``. Payload must be printable ASCII; that's the
prompt-injection use case.
"""

from __future__ import annotations

from m3gast3gg.core import unicode_tags as _tags

from ..base import BaseTransformer
from ..registry import register


def _encode(text: str, **_: object) -> str:
    return _tags.encode_tag_run(
        text, printable_only=True, start_sentinel=False, terminator=True,
    )


def _decode(text: str, **_: object) -> str:
    return _tags.decode_tag_run(
        text, require_start_sentinel=False, stop_on_terminator=True,
        printable_only=True,
    )


def _detect(text: str) -> bool:
    return any(_tags.TAG_BASE <= ord(c) <= _tags.TAG_END for c in text)


invisible_text_transformer = BaseTransformer(
    name="Invisible Text",
    category="concealment",
    priority=1,
    description="Hide printable ASCII as a Unicode Tag run (U+E0020..U+E007E).",
    func=_encode,
    reverse=_decode,
    detector=_detect,
)
register(invisible_text_transformer)
