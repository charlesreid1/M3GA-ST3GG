# Text combining-mark (CGJ) steganography

Payload as presence/absence of `U+034F COMBINING GRAPHEME JOINER`
after each alphabetic character. Same one-bit-per-carrier shape as
[[text/variation-selectors]], different codepoint family.

## What the ST3GG implementation does

`text_core.encode_combining / text_core.decode_combining`. See
[[text-combining]].

Alphabet:

- Alphabetic cover char followed by `U+034F` (CGJ) → bit 1
- Alphabetic cover char alone → bit 0

Framing: 16-bit LE length prefix, one bit per alphabetic cover
position.

## Why CGJ specifically

CGJ (U+034F) is defined by Unicode to have **no visual effect** in any
rendering context — it exists to block canonical reordering of adjacent
combining marks. That "no visual effect" spec is what makes it an
ideal invisible steg carrier.

## Where it dies

- **NFC normalization**: CGJ can be dropped by NFC when it sits between
  two non-combining characters (the "canonical reordering" purpose
  becomes moot). Testing per-platform is essential.
- **NFKC normalization**: same as NFC plus more collapse cases.
- **Line-length-aware editors**: some text editors count CGJ as
  zero-width and preserve it; some silently strip it as "invisible
  garbage." Check the target.
- **Combining-mark stackers**: fonts that stack visible diacritics may
  render `a̋̋̋` (multiple stacked marks) as a growing tower of glyphs
  even though CGJ itself is defined as invisible.

## Where it survives

- Raw UTF-8 pipelines (file save, HTTP, git).
- Chat clients that preserve Unicode.
- Slack paste ([[sv-combining-slack-paste]]).

## Related: other combining marks

CGJ is the "safe invisible" combining mark, but there are others:

- `U+0361` COMBINING DOUBLE INVERTED BREVE — visible arc, not usable
  as invisible steg.
- `U+0489` COMBINING CYRILLIC MILLIONS SIGN — visible.
- `U+FE20..U+FE2F` COMBINING HALF MARKS — visible.

Only CGJ combines invisibility with a defined-no-visual-effect spec.
Combining marks with rendering behavior are covered by
`text_core.encode_combining` as an alphabet expansion for
higher-bpc variants — see [[text-combining]].

## Detection

- Byte scan: `U+034F` sequences.
- `text_core.detect_unicode_steg` includes CGJ detection.

## Sources

- [[unicode-nfkc]] — NFC/NFKC normalization, CGJ semantics
- [[st3gg-field-guide]] — ST3GG-specific framing
