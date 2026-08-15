# header_format

Every technique frames its payload for the receiver. The `header_format`
field in a technique's `technical_body` describes that framing.

## Common shapes

- **16-bit LE length prefix**: the first 16 bits of the payload
  encode the payload byte count (little-endian). Receiver reads the
  prefix, then that many bytes of payload. Used by zero-width,
  cyrillic-homoglyph, whitespace, and most text techniques.
- **Delimiter-based**: start marker (e.g. U+E0000) + payload +
  cancel/end marker. Used by invisible-ink, emoji-tag-sequence.
- **ST3GG v3 header**: password-derived magic + flags + length +
  optional nonce + payload + optional GCM tag. See
  [[crypto/st3gg-v3-header]]. Used by image LSB, matryoshka.
- **Format-native**: the payload IS a full valid format instance
  (a PNG chunk, a JPEG APPn segment, a ZIP entry). Framing is the
  format's own grammar.
- **None**: raw appended bytes with no framing. The receiver reads
  everything after some anchor. Used by braille (appended after
  cover text), post-EOF PDF bytes.

## The trade-off

- **Length prefix** wastes overhead but survives truncation better —
  the receiver knows exactly how many bytes to read.
- **Delimiter-based** wastes fewer bytes but breaks if the delimiter
  appears in the payload (which is why invisible-ink uses U+E007F
  cancel-tag as its end marker — that specific codepoint won't
  appear in valid ASCII-shadow payload bytes).
- **Format-native** is free (leverages existing spec) but ties the
  technique to a specific container.

## Why the KR records this

A `stegg_lookup_technique(name)` answer that omits header format is
incomplete — a solver can't extract without knowing the framing.
Similarly, `stegg_explain_pipeline` chains techniques by knowing each
layer's framing so it can correctly wrap payload for the next layer.

## Related

- [[capacity-formula]] — capacity depends on header overhead.
- [[crypto/st3gg-v3-header]] — the ST3GG-canonical wrapping format.
