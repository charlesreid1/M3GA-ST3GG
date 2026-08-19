# Text zero-width — 15-second triage

"Does this text hide zero-width payload?"

## Look at the bytes, not the render

The cover renders identically before and after a zero-width hide. There
is no visual signature. **Every triage decision comes from raw bytes.**

## In a hex viewer

Look for the byte triplets:

- `E2 80 8B` — U+200B ZWSP (bit 0)
- `E2 80 8C` — U+200C ZWNJ (bit 1)
- `E2 80 8D` — U+200D ZWJ (start/end delimiter)

Runs of ≥ 4 of these in a row are unnatural. `text_core.detect_unicode_steg`
uses that threshold.

## In a Python REPL

```python
import re
suspect = "..."          # paste the text
zw_run = re.search(r"[​‌‍]{4,}", suspect)
if zw_run:
    print(f"zero-width run at position {zw_run.start()}, length {len(zw_run.group())}")
```

Or run `stegg_text_steg_message` and read the detector output.

## Rendering-based tells

Not reliable — the whole point is invisibility. But in some contexts:

- **Selecting the "invisible" region with a mouse** in a rich-text UI
  may show the highlighted rectangle extending past the visible glyphs.
- **Text-to-speech / screen readers** may pause or pronounce the codepoints
  ("zero width space") if they don't strip them.
- **Character count in a form**: a text box that shows character count
  will over-report vs the visible glyph count.

## Common patterns by author

- **Payload at the end of the cover, wrapped in ZWJ delimiters**: the
  ST3GG default. Look for a ZWJ near the very end of the string,
  preceded by a run of ZWSP/ZWNJ.
- **Payload embedded mid-cover**: less common; some tools do it for
  extra stealth. Delimiter still marks the boundaries.
- **Payload with no delimiter, just concatenated ZWSP/ZWNJ**: a naive
  scheme; parser should still work but is fragile to any surrounding
  character being modified.

## Diagnosis flow

1. Run `stegg_text_steg_message` with the text.
2. If it flags `zero_width` with a codepoint run: try
   `stegg_text_decode(method='zero_width', ...)`.
3. If decode succeeds, report `*FOUND*` with the recovered payload.
4. If decode fails (e.g. the encoding isn't ZWSP=0 / ZWNJ=1 but reversed),
   try the reversed mapping manually.

## What zero-width is NOT

- Not the same as [[text-invisible-ink]] (that uses the U+E0000 tag
  block, one byte per codepoint, no bit-mapping).
- Not the same as [[text-variation]] (VS-selectors piggyback bits onto
  alphanumeric characters, not standalone codepoints).
- Not the same as ZWJ *emoji sequences* (family emoji, occupation
  modifiers) — those are legitimate uses of ZWJ, and a ZWJ inside a
  short emoji cluster is not a payload signal.

## When zero-width detection fires but decode returns garbage

Possibilities:
- The scheme uses a different bit-mapping (ZWSP=1 / ZWNJ=0).
- The scheme skipped the ZWJ delimiter (raw bit-run concatenated to
  cover).
- The scheme applied a transform (XOR, ROT, RC4) after bit-mapping.

Report `*INCONCLUSIVE*` naming the technique and the raw codepoint run
length; hand the user a manual decode snippet.

## Sources

- [[text-zero-width]]
- [[unicode-tr36-security]]
- [[st3gg-field-guide]]
