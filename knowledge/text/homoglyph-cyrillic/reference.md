# Cyrillic homoglyph — reference

## The twin table

The ST3GG implementation uses a curated ~20-pair alphabet of visually
identical Latin ↔ Cyrillic codepoints. The exact table is in
`text_core._CYRILLIC_TWINS`.

Lowercase pairs (bit-0 = Latin, bit-1 = Cyrillic):

| Latin | Cyrillic | Latin CP | Cyrillic CP |
|-------|----------|----------|-------------|
| a | а | U+0061 | U+0430 |
| c | с | U+0063 | U+0441 |
| e | е | U+0065 | U+0435 |
| i | і | U+0069 | U+0456 |
| j | ј | U+006A | U+0458 |
| o | о | U+006F | U+043E |
| p | р | U+0070 | U+0440 |
| s | ѕ | U+0073 | U+0455 |
| x | х | U+0078 | U+0445 |
| y | у | U+0079 | U+0443 |

Uppercase pairs:

| Latin | Cyrillic | Latin CP | Cyrillic CP |
|-------|----------|----------|-------------|
| A | А | U+0041 | U+0410 |
| B | В | U+0042 | U+0412 |
| C | С | U+0043 | U+0421 |
| E | Е | U+0045 | U+0415 |
| H | Н | U+0048 | U+041D |
| K | К | U+004B | U+041A |
| M | М | U+004D | U+041C |
| O | О | U+004F | U+041E |
| P | Р | U+0050 | U+0420 |
| T | Т | U+0054 | U+0422 |
| X | Х | U+0058 | U+0425 |
| Y | Y (U+04AE) | U+0059 | U+04AE — imperfect twin, not always used |

## Capacity

```
capacity_bytes = floor((count_of_Latin_letters_in_cover - 16) / 8)
```

- Only letters present in the twin table count as "Latin letters" —
  `b`, `d`, `f`, `g`, etc. don't have a good twin and are skipped.
- `-16` accounts for the 16-bit length prefix.

Worked example: a paragraph with 100 usable Latin letters →
`floor((100 - 16) / 8) = 10` payload bytes.

Covers with < 16 usable Latin letters raise `TextStegCapacityError`
before encoding starts. See [[cap-text-cyrillic-homoglyph]].

## Framing

```
[ 16-bit LE length prefix (as 16 carrier positions) ] [ payload bits, 1 per Latin carrier ]
```

- Length prefix comes first; consumes the first 16 usable Latin letters.
- Each subsequent usable Latin letter carries one payload bit.
- Non-twin characters (spaces, punctuation, letters without twins) pass
  through unchanged.

## UTF-8 byte cost

- Latin letters: 1 byte each in UTF-8.
- Cyrillic twins: 2 bytes each (U+0400 range).

So a payload byte adds ~8 bytes of UTF-8 overhead vs the pure-Latin
cover (8 twins × 1 extra byte each).

## Interaction with normalization

- **NFC (Canonical Composition)**: preserves the distinction. Safe.
- **NFKC (Compatibility Composition)**: Cyrillic homoglyphs are NOT in
  the compatibility mapping to Latin. NFKC preserves them.
  **BUT** — many implementations *treat* the pair as confusable in
  ways that mutate one to the other (e.g. the Unicode `NFKC_Casefold`
  process, some non-canonical normalizations in libraries). ST3GG's
  practical stance is "assume NFKC-adjacent processes may destroy the
  payload"; see [[myth-homoglyph-nfkc]] for the precise version.
- **Case folding**: preserves codepoint identity, both stay lowercase.

## Sources

- [[unicode-tr36-security]]
- [[cap-text-cyrillic-homoglyph]]
- [[text-cyrillic-homoglyph]]
