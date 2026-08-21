"""Morse code — ITU standard letters, digits, and common punctuation.

Encoded as ``.``/``-`` tokens separated by spaces; words separated by
``/``. Unknown characters pass through as ``?``.
"""

from __future__ import annotations

import re

from ..base import BaseTransformer
from ..registry import register


MORSE_TABLE: dict[str, str] = {
    "A": ".-",    "B": "-...",  "C": "-.-.",  "D": "-..",   "E": ".",
    "F": "..-.",  "G": "--.",   "H": "....",  "I": "..",    "J": ".---",
    "K": "-.-",   "L": ".-..",  "M": "--",    "N": "-.",    "O": "---",
    "P": ".--.",  "Q": "--.-",  "R": ".-.",   "S": "...",   "T": "-",
    "U": "..-",   "V": "...-",  "W": ".--",   "X": "-..-",  "Y": "-.--",
    "Z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-",
    "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----.",
    ".": ".-.-.-", ",": "--..--", "?": "..--..", "'": ".----.", "!": "-.-.--",
    "/": "-..-.",  "(": "-.--.",  ")": "-.--.-",  "&": ".-...", ":": "---...",
    ";": "-.-.-.", "=": "-...-", "+": ".-.-.",  "-": "-....-", "_": "..--.-",
    '"': ".-..-.", "$": "...-..-", "@": ".--.-.",
}

REVERSE_TABLE: dict[str, str] = {v: k for k, v in MORSE_TABLE.items()}


_MORSE_RE = re.compile(r"^[.\-\s/]+$")


def _encode(text: str, **_: object) -> str:
    words = []
    for word in text.split(" "):
        letters = []
        for ch in word.upper():
            token = MORSE_TABLE.get(ch)
            if token is not None:
                letters.append(token)
        if letters:
            words.append(" ".join(letters))
    return " / ".join(words)


def _decode(text: str, **_: object) -> str:
    words = text.strip().split("/")
    out_words = []
    for word in words:
        letters = word.strip().split()
        decoded = "".join(REVERSE_TABLE.get(tok, "?") for tok in letters if tok)
        out_words.append(decoded)
    return " ".join(out_words)


def _detect(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 3:
        return False
    if not _MORSE_RE.match(stripped):
        return False
    return "." in stripped or "-" in stripped


morse_transformer = BaseTransformer(
    name="Morse",
    category="encoding",
    priority=300,
    description="ITU Morse code — dots, dashes, / between words.",
    func=_encode,
    reverse=_decode,
    detector=_detect,
)
register(morse_transformer)
