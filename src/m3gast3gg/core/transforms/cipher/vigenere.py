"""Vigenère cipher — polyalphabetic Caesar with a repeating key.

Broken by Kasiski (1863) and Friedman (1922) for keys short relative to the
ciphertext. Not encryption for anything modern; useful for CTFs, jailbreak
obfuscation chains, and universal-decode candidates when a key is supplied.
"""

from __future__ import annotations

from ..base import BaseTransformer, ConfigurableOption
from ..registry import register


def _apply(text: str, key: str, decrypt: bool) -> str:
    if not key:
        raise ValueError("vigenere: key must be non-empty")
    key = "".join(c for c in key if c.isalpha())
    if not key:
        raise ValueError("vigenere: key must contain at least one letter")
    key = key.upper()
    out = []
    ki = 0
    for c in text:
        code = ord(c)
        if 0x41 <= code <= 0x5A:
            shift = ord(key[ki % len(key)]) - 0x41
            if decrypt:
                shift = -shift
            out.append(chr((code - 0x41 + shift) % 26 + 0x41))
            ki += 1
        elif 0x61 <= code <= 0x7A:
            shift = ord(key[ki % len(key)]) - 0x41
            if decrypt:
                shift = -shift
            out.append(chr((code - 0x61 + shift) % 26 + 0x61))
            ki += 1
        else:
            out.append(c)
    return "".join(out)


def _encode(text: str, key: str = "SECRET", **_: object) -> str:
    return _apply(text, key, decrypt=False)


def _decode(text: str, key: str = "SECRET", **_: object) -> str:
    return _apply(text, key, decrypt=True)


vigenere_transformer = BaseTransformer(
    name="Vigenere",
    category="cipher",
    priority=60,
    description="Polyalphabetic Caesar with a repeating alphabetic key.",
    func=_encode,
    reverse=_decode,
    detector=None,
    configurable_options=[
        ConfigurableOption(
            id="key", label="Key (letters only)",
            type="text", default="SECRET",
        ),
    ],
)
register(vigenere_transformer)
