"""Bacon biliteral cipher — 5-bit A/B per letter.

Francis Bacon's original biliteral (24-letter alphabet: I=J, U=V). Each
plaintext letter becomes a 5-character AAAAB / AAABA / ... pattern; the
letter case, font, or whitespace can then carry the pattern in a stego
wrap. Here we emit the raw pattern (no cover), which is the useful
building block for a cipher → concealment pipeline.

Whitespace preserved between words (as `" "` on decode); unknown chars
dropped on encode.
"""

from __future__ import annotations

from ..base import BaseTransformer
from ..registry import register


_ALPHABET = "ABCDEFGHIKLMNOPQRSTUWXYZ"  # 24 letters, I=J, U=V


def _letter_to_pattern(letter: str) -> str:
    upper = letter.upper()
    if upper == "J":
        upper = "I"
    elif upper == "V":
        upper = "U"
    idx = _ALPHABET.index(upper)
    return format(idx, "05b").replace("0", "A").replace("1", "B")


_PATTERN_TO_LETTER = {
    format(i, "05b").replace("0", "A").replace("1", "B"): _ALPHABET[i]
    for i in range(24)
}


def _encode(text: str, **_: object) -> str:
    words = text.split(" ")
    out_words = []
    for word in words:
        letters = []
        for ch in word:
            if ch.isalpha():
                letters.append(_letter_to_pattern(ch))
        if letters:
            out_words.append(" ".join(letters))
    return " / ".join(out_words)


def _decode(text: str, **_: object) -> str:
    words = text.strip().split("/")
    out_words = []
    for word in words:
        letters = []
        for tok in word.strip().split():
            if len(tok) == 5 and tok in _PATTERN_TO_LETTER:
                letters.append(_PATTERN_TO_LETTER[tok])
        out_words.append("".join(letters))
    return " ".join(out_words)


bacon_transformer = BaseTransformer(
    name="Bacon",
    category="cipher",
    priority=60,
    description="Bacon biliteral cipher — 5-bit A/B per letter (24-letter alphabet, I=J, U=V).",
    func=_encode,
    reverse=_decode,
    detector=None,
)
register(bacon_transformer)
