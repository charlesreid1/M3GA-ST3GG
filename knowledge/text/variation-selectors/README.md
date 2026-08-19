# Text variation-selector steganography

Payload as presence/absence of a Unicode Variation Selector (VS)
following each alphanumeric character in the cover. One bit per
carrier position; renders as nothing when the VS doesn't map to a
defined variant.

## What the ST3GG implementation does

`text_core.encode_variation / text_core.decode_variation`. See
[[text-variation]].

Alphabet:

- Cover character followed by `U+FE00` (VARIATION SELECTOR-1) → bit 1
- Cover character alone → bit 0

The full VS range is `U+FE00..U+FE0F` (VS-1..VS-16) plus
`U+E0100..U+E01EF` (VS-17..VS-256, "supplemental"). ST3GG's implementation
uses VS-1 as the presence flag; the other 255 are available for higher-bit
variants.

Framing: 16-bit LE length prefix, one bit per alphanumeric cover
position.

## Where it dies

- **Terminal mouse-copy**: canonical layer is the visible glyph stream;
  VS chars are formatting metadata that get dropped. See
  [[myth-vs-terminal]] and [[transport-terminal-stdout]].
- **NFC normalization**: some VS+base sequences are defined
  (`⚡︎`/`⚡️` emoji-vs-text presentation is the canonical example) and
  NFC will collapse them. Undefined VS+base sequences survive NFC.
- **Some code viewers**: `.git` diff viewers, GitHub blob view — the
  chars survive but render as a small blank space, revealing the hide.

## Where it survives

- Raw UTF-8 (files, HTTP, email attachment): byte-perfect round trip.
- Chat clients that preserve Unicode metadata.
- Slack paste on the `blocks[]` path
  ([[sv-variation-slack-paste]]).

## Emoji presentation VS (VS-15/VS-16)

Not steganographic on their own — VS-15 (`U+FE0E`, text presentation)
and VS-16 (`U+FE0F`, emoji presentation) are defined semantically for
character sequences like `☂` vs `☂️`. Do not use these as steg carriers;
they change rendering deterministically and are a giveaway. Prefer
`U+FE00..U+FE0D` and the supplemental `U+E0100..U+E01EF` range.

## Detection

- Byte scan: any codepoint in `U+FE00..U+FE0F` or `U+E0100..U+E01EF`.
- `text_core.detect_unicode_steg` includes VS detection.
- Rendering test: many VS+base sequences fall through to `.notdef`
  or invisible, but a defined VS applied to the wrong base can render
  visibly (e.g. VS-16 on a non-emoji character).

## Sources

- [[unicode-variation-selectors]] — Unicode Standard Ch. 23 on
  variation selectors
- [[unicode-tr36-security]] — VS abuse in security
- [[st3gg-field-guide]] — ST3GG-specific framing
