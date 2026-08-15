# Text zero-width — reference

## Codepoints and bit mapping

| Codepoint | Name | UTF-8 bytes | Role |
|-----------|------|--------------|------|
| U+200B | ZERO WIDTH SPACE | `E2 80 8B` | bit 0 |
| U+200C | ZERO WIDTH NON-JOINER | `E2 80 8C` | bit 1 |
| U+200D | ZERO WIDTH JOINER | `E2 80 8D` | start/end delimiter |

Every codepoint is 3 bytes in UTF-8 (BMP range that requires 3-byte
encoding).

## Framing

```
[ cover text ] U+200D [ payload bits: ZWSP=0 / ZWNJ=1, 8 per byte ] U+200D
```

- 1 delimiter codepoint × 2 (start, end) = 2 codepoints framing overhead.
- 8 payload codepoints per payload byte.
- Total UTF-8 byte overhead = `(2 + 8 * len(payload)) * 3` bytes.

Worked example: 32-byte payload → `(2 + 256) * 3 = 774` bytes of
zero-width UTF-8 appended to the cover.

## Capacity

Unbounded — the technique extends the cover rather than replacing
characters inside it. See [[cap-text-zero-width]].

`stegg_text_capacity` returns `-1` (or effectively "unbounded") for
zero-width, distinguishing it from length-prefixed methods like
[[text-cyrillic-homoglyph]].

## Why 3-codepoint framing

The ZWJ delimiter is chosen because:

1. Legitimate ZWJ usage exists (emoji sequences, Indic script joiners)
   → won't fire naive "any ZWJ = payload" alarms.
2. It's distinct from the ZWSP/ZWNJ bit alphabet, so the parser can
   unambiguously find the payload boundaries.
3. Isolated ZWJ codepoints render as nothing in virtually all rendering
   engines.

## Byte-level detection heuristic

`text_core.detect_unicode_steg` scans for runs of ZWSP/ZWNJ with length
≥ 4. Natural text never has 4+ consecutive zero-width codepoints; that
threshold gives near-zero false positives on English/emoji-rich text.

Runs of exactly the same zero-width codepoint (e.g. 16 ZWSPs in a row)
are a stronger signal — payload of "all-zero bytes" — but they're rare
in natural language.

## Interaction with normalization

- **NFC (Canonical Composition)**: preserves zero-width codepoints. Safe.
- **NFKC (Compatibility Composition)**: preserves zero-width codepoints
  too. Safe. See [[myth-zero-width-invisible-everywhere]] and note
  that homoglyph techniques *do* die to NFKC (see
  [[myth-homoglyph-nfkc]]).
- **NFKD (Compatibility Decomposition)**: preserves zero-width chars.

Zero-width is stronger than homoglyph against Unicode normalization.
Its weaknesses are elsewhere (terminal filtering, input sanitizers).

## Sources

- [[rfc-3629-utf8]]
- [[unicode-tr36-security]]
- [[cap-text-zero-width]]
