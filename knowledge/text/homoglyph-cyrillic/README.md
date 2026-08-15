# Cyrillic homoglyph steganography

Payload bits encoded as Latin-vs-Cyrillic character choice inside a
cover that's ostensibly all-Latin prose. Cyrillic and Latin share ~20
visually-identical codepoints; that shared alphabet becomes a covert
channel.

The technique the whole "IDN homograph" phishing family is built on,
turned into a steg tool.

## What the ST3GG implementation does

`text_core.encode_cyrillic_homoglyph / text_core.decode_cyrillic_homoglyph`.
See [[text-cyrillic-homoglyph]] and [[cap-text-cyrillic-homoglyph]].

The alphabet — 20-ish Latin ↔ Cyrillic twin pairs. A few examples:

| Latin | Cyrillic | Codepoint diff |
|-------|----------|-----------------|
| a | а | U+0061 vs U+0430 |
| e | е | U+0065 vs U+0435 |
| o | о | U+006F vs U+043E |
| p | р | U+0070 vs U+0440 |
| c | с | U+0063 vs U+0441 |
| y | у | U+0079 vs U+0443 |
| x | х | U+0078 vs U+0445 |
| H | Н | U+0048 vs U+041D |
| A | А | U+0041 vs U+0410 |

Framing: 16-bit LE length prefix + payload bits, 1 bit per Latin
carrier position (Latin = 0, Cyrillic = 1).

## The four questions

- **What is this?** → this README.
- **How do the numbers work?** → [[text/homoglyph-cyrillic/reference]] —
  the full 20-pair alphabet, capacity formula, framing.
- **What does an end-to-end run look like?** → [[text/homoglyph-cyrillic/walkthrough]] —
  a 10-byte payload into a paragraph, before/after character-by-character
  diff.
- **Is *this text* a homoglyph hide?** → [[text/homoglyph-cyrillic/recognition]] —
  15-second triage: how a homoglyph cover looks in a code-point renderer,
  how it fails NFKC.

## Where it dies

- **NFKC normalization**: DIES. Cyrillic `а` (U+0430) normalizes to
  Latin `a` (U+0061). Any pipeline that applies NFKC to input
  (search boxes, some form validators, some DB columns, aggressive
  input sanitizers) destroys the payload. See
  [[myth-homoglyph-nfkc]].
- **Case-only normalization**: some tools lowercase then strip
  non-ASCII. Depends on the tool.
- **Font substitution to a Cyrillic-only font**: the visual identity
  breaks (though the codepoints are still readable, so decode still
  works).

## Where it survives

- **NFC** (Canonical): preserves the distinction.
- **Any UTF-8-preserving pipeline that doesn't NFKC**: chat clients,
  Slack paste ([[sv-cyrillic-slack-paste]]), Slack snippet
  ([[sv-cyrillic-slack-snippet]]), email, GitHub upload, HTTP raw.
- **Copy/paste between rich-text UIs**: usually preserved.

## Detection

- **[[det-bit-plane-entropy]]** doesn't apply.
- `text_core.detect_cyrillic_homoglyph_steg` — scans for the specific
  Cyrillic codepoints in the twinning list appearing amid otherwise-Latin
  content. High-precision because natural English text has ~zero
  incidence of these Cyrillic codepoints.

## The stealth vs death tradeoff

Zero-width ([[text-zero-width]]) is **invisible everywhere** but
**visible in any hex viewer**. Homoglyph is **invisible in hex** (looks
like normal UTF-8 bytes) but **visible in a codepoint-aware renderer**
and **dies to NFKC**.

Pick homoglyph when the cover has to survive as *readable prose* under
casual inspection.

## Sources

- [[unicode-tr36-security]] — the Unicode Consortium's security
  primer, includes the confusable-character discussion
- [[st3gg-field-guide]]
- [[cap-text-cyrillic-homoglyph]]
