# Cyrillic homoglyph — 15-second triage

"Does this text hide a Cyrillic-homoglyph payload?"

## The signal is codepoint identity, not glyph shape

To the eye: the text looks like normal English prose. To a codepoint
inspector: a subset of the letters have Cyrillic codepoints instead of
Latin.

## Hex-viewer inspection

Latin letters are 1 byte in UTF-8 (`00`-`7F`). Cyrillic letters are 2
bytes (`D0 80` through `D1 8F`). A hex dump of a homoglyph-stego shows:

```
54 68 65 20 63 61 74     ← "The cat" — pure Latin
20 D1 81 61 74 20        ← " с at " — space, Cyrillic с (D1 81), Latin at, space
```

Interleaved 1-byte / 2-byte UTF-8 in what looks like plain English is
the signature.

## Codepoint distribution check

```python
import unicodedata
suspect = "..."   # paste text
counts = {}
for ch in suspect:
    if 0x0400 <= ord(ch) <= 0x04FF:      # Cyrillic block
        counts[ch] = counts.get(ch, 0) + 1
print(counts)
# Expected in a homoglyph stego: {'а': N, 'е': N, 'о': N, ...}
```

Cyrillic-block characters appearing in text that reads as English is the
tell. Natural English has ~zero incidence of Cyrillic codepoints.

## `stegg_text_steg_message` output

`detect_cyrillic_homoglyph_steg` fires on:

- Cyrillic-block codepoints that match the specific twin-table (a/а,
  e/е, o/о, p/р, c/с, ...).
- Density: even one twin-table codepoint in a mostly-Latin string is
  suspicious. Natural bilingual text rarely uses just those specific
  10-20 codepoints.

## Signal cheat sheet

| Signal | Diagnosis |
|--------|-----------|
| Suspect text has Cyrillic codepoints from twin-table amid Latin | Almost certainly Cyrillic homoglyph steg — try `stegg_text_decode(method='cyrillic_homoglyph', ...)` |
| Suspect text has Cyrillic codepoints NOT from twin-table (e.g. Cyrillic б, г, ж) | Not this technique. May be legitimate multilingual text. |
| Suspect text has fullwidth punctuation (， ． ； ：) amid ASCII | [[text-cjk-homoglyph]] instead, run its decoder |
| No Cyrillic codepoints found | Not homoglyph. Try zero-width, variation, or invisible-ink detectors. |

## When to expect a false alarm

- **Legitimate bilingual text** (Russian-English code-switching): if the
  Cyrillic block usage is diverse (not just the twin-table subset),
  it's not steg.
- **Domain names in IDN homograph attacks**: same alphabet used for
  phishing (`gооgle.com` with Cyrillic `о`s). Not a steg payload but a
  detection-worthy signal in its own context.

## When cyrillic-homoglyph decoder fires but returns garbage

Possibilities:

- Length prefix mis-aligned (cover has more or fewer usable Latins than
  the encoder counted — check the twin table).
- Custom bit mapping (bit-1 = Latin, bit-0 = Cyrillic).
- Post-encoding transform applied (XOR, rotation).

Report `*INCONCLUSIVE*` with the twin count and their positions; hand
over a manual decode snippet:

```python
suspect = "..."
TWINS = {'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c',
         'у': 'y', 'х': 'x', 'ѕ': 's', 'і': 'i', 'ј': 'j'}
bits = []
for ch in suspect:
    if ch in TWINS: bits.append(1)
    elif ch in TWINS.values(): bits.append(0)
length = int("".join(map(str, bits[:16]))[::-1], 2)   # 16-bit LE
payload = bytes(int("".join(map(str, bits[16+i*8:16+i*8+8])), 2)
                for i in range(length))
print(payload)
```

## Related techniques

- [[text-cjk-homoglyph]] — punctuation twin, same story with fullwidth
  characters.
- [[text-zero-width]] — invisible in hex too, dies to different
  transports.
- [[text-invisible-ink]] — U+E0000 tag block, higher capacity, dies to
  Slack paste.

## Sources

- [[text-cyrillic-homoglyph]]
- [[unicode-tr36-security]]
- [[st3gg-field-guide]]
