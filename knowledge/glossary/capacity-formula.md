# capacity_formula

The closed-form expression each technique carries in its
`technical_body` for **how many payload bytes fit in a cover of a
given shape**.

## Examples

- **LSB**: `W * H * bits_per_channel * len(channels) / 8` bytes,
  minus header.
- **Zero-width**: `8 zero-width codepoints per payload byte + 2
  delimiters`.
- **Cyrillic homoglyph**: `floor((count_of_Latin_letters_in_cover -
  16) / 8)` bytes.
- **Capitalization**: `floor((word_count - 16) / 8)` bytes.
- **F5** (matrix encoding, param k):
  `|nonzero_AC_coefs| * k / (2^k - 1)` bits, minus shrinkage
  overhead.
- **DCT (ST3GG generic)**: ~1 bit per 64 pixels at `robustness=low`.
- **PVD**: `sum over adjacent pixel pairs of log2(range_width_i)`
  bits.

Each formula is a starting point for a `stegg_lookup_technique`
answer to "how much fits."

## The three inputs

Capacity formulas need three things:

1. **Cover shape**: image dimensions, text character count, audio
   duration, etc.
2. **Technique parameters**: bits per channel, robustness level,
   channel selection.
3. **Payload framing overhead**: header magic (see
   [[crypto/st3gg-v3-header]]) + length prefix + optional AES tag.

`stegg_lookup_technique` returns the formula and the technique's
default parameters; the caller supplies the cover shape.

## The `capacity_models.json` file

Formulas are ALSO stored as first-class records in
`capacity_models.json` (category `capacity_model`). This exists so
`stegg_capacity(technique, shape)` can answer WITHOUT invoking the
actual encoder. Each capacity_model record carries a
`shape_params[]` list, a formula string, and pointers to the
technique record. See [[cap-image-lsb]], [[cap-image-f5]],
[[cap-text-zero-width]] for examples.

## In the KR

- Field: `technical_body.capacity_formula` on every technique
  record.
- Category: `capacity_model` in `capacity_models.json`.
- Retrieval: `stegg_lookup_technique(name)` returns both.
