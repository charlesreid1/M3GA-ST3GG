# Emoji skintone-modifier steganography

Two bits per emoji via skin-tone modifier selection. Subtler than
🔴/🔵 substitution — a run of thumbs-ups with varied skin tones reads
as a real message, not obvious steg.

## What the ST3GG implementation does

`text_core.encode_skintone / text_core.decode_skintone`. See
[[emoji-skintone]].

Alphabet: the four Fitzpatrick skin-tone modifiers:

- U+1F3FB (light) → 00
- U+1F3FC (medium-light) → 01
- U+1F3FD (medium) → 10
- U+1F3FE (medium-dark) → 11

(U+1F3FF, dark, is left out to give a clean 2-bit alphabet.)

Framing: no length prefix — payload as an appended block of
skin-toned human emoji after the cover. Capacity: 4 emoji per
payload byte.

## Where it dies

- **Slack paste**: modifier bits ride inside `blocks[]`; consumers
  reading `.text` get `:colon_form:` with modifiers lost. See
  [[emoji-skintone]] technical body.
- **Text-only descriptors**: accessibility software that transcribes
  emoji to "person with light skin tone" preserves the modifier
  identity but breaks the byte-level round trip.

## Where it survives

- Byte-level UTF-8 pipelines that preserve emoji ZWJ sequences.
- iMessage, Discord, WhatsApp (all preserve).
- Slack `blocks[]` if the consumer walks the tree correctly.

## The application to jailbreaks

Skin-tone modifiers can ride ANY human-emoji base (thumbs-ups,
waves, family emoji, hand signs) so the stego blends into normal
emoji use. Combined with tag-sequence steg (see
[[emoji/tag-sequences]]), a single "😊👍" pair carries multi-byte
payloads.

## Detection

- Statistical: real messages use a narrow set of skin tones per user
  (people default to one). A mix of 4 within one message is unusual.
- Byte scan for the modifier codepoints.

## Sources

- [[unicode-emoji-tag-sequences]] — emoji + modifier grammar
- [[st3gg-field-guide]] — ST3GG-specific framing
