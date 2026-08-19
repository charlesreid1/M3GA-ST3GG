# Cyrillic homoglyph — end-to-end walkthrough

Hide `"HI"` (2 bytes) inside a short prose cover. Show the exact
codepoint substitutions.

## Setup

```python
from stegg import text_core
cover = "The cat picks the north path at dusk and the horizon reddens."
payload = b"HI"
```

Cover has these usable Latin letters (mapped positions):

```
T[H]e c[a]t p[i]cks the north p[a]th at dusk and the h[o]riz[o]n r[e]ddens.
```

Count of twinnable letters: let's count — `H`, `e`, `c`, `a`, `p`,
`i`, `c`, `k`, `s`, `t`, `h`, `e`, `n`, `o`, `r`, `t`, `h`, `p`, `a`,
`t`, `h`, `a`, `t`, `d`, `u`, `s`, `k`, `a`, `n`, `d`, `t`, `h`, `e`,
`h`, `o`, `r`, `i`, `z`, `o`, `n`, `r`, `e`, `d`, `d`, `e`, `n`, `s`
→ filter to twins (`a`, `c`, `e`, `H`, `i`, `k`, `o`, `p`, `s`, `t`,
`x`, `y`, and their uppercase equivalents where present in the table).
Non-twinnable letters like `b`, `d`, `f`, `g`, `l`, `m`, `n`, `r`, `u`,
`v`, `w`, `z` are skipped.

Count works out to ~32 usable Latin letters — plenty for the 16-bit
prefix + 16 payload bits (2 bytes).

## Encode

```python
stego = text_core.encode_cyrillic_homoglyph(cover, payload)
```

Under the hood:

1. Payload → bits: `HI` = `0x48 0x49` → `01001000 01001001`.
2. Length prefix → bits: `0x0002` little-endian → `01000000 00000000` (bits).
3. Full bit-stream (34 bits total: 16 prefix + 16 payload + 2 padding):
   `0100000000000000 0100100001001001`.
4. Walk the cover; at each usable Latin letter, take the next bit:
   - bit 0 → keep the Latin letter.
   - bit 1 → substitute with its Cyrillic twin.
5. Non-twinnable letters pass through.

## Diff

Compare character-by-character (visible identical, codepoints differ):

```
cover:  T H e   c a t   p i c k s ...
        U0054 U0048 U0065 U0020 U0063 U0061 U0074 U0020 U0070 U0069 U0063 U006B U0073 ...

stego:  T H e   с a t   р i с k s ...
        U0054 U0048 U0065 U0020 U0441 U0061 U0074 U0020 U0440 U0069 U0441 U006B U0073 ...
```

The `c` at position 4 becomes Cyrillic `с` (U+0441), and so on for
every bit-1 position. To a human reading the paragraph: unchanged.

## Decode

```python
recovered = text_core.decode_cyrillic_homoglyph(stego)
assert recovered == b"HI"
```

Parser walks the stego, at each usable Latin/Cyrillic-twin position
records bit-1 for Cyrillic and bit-0 for Latin, reads the 16-bit
length prefix, then extracts that many bytes of payload.

## What would go wrong

| Change | Effect |
|--------|--------|
| Cover too short (< 16 usable Latins) | `TextStegCapacityError` on encode |
| Cover passes through NFKC | May die (see [[myth-homoglyph-nfkc]]) |
| Cover passes through `text.casefold()` in Python | Latin/Cyrillic case-fold to lowercase; codepoints preserved; payload survives |
| Cover displayed in a Cyrillic-only-font terminal | Cyrillic twins may render slightly differently; payload survives (decode reads codepoints) |
| Cover pasted into a search box that applies NFKC | Payload dies |
| Cover pasted into Slack message body | Survives ([[sv-cyrillic-slack-paste]]) |
| Cover sent as Slack snippet | Survives ([[sv-cyrillic-slack-snippet]]) |

## Reading the signals

`stegg_text_steg_message(stego)` fires `detect_cyrillic_homoglyph_steg`
because it sees Cyrillic codepoints from the twin table amid otherwise-
Latin content. Detector reports the twin count and location distribution.

## Sources

- [[text-cyrillic-homoglyph]]
- [[cap-text-cyrillic-homoglyph]]
- [[unicode-tr36-security]]
