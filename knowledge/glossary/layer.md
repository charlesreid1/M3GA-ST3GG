# layer

The ST3GG-record taxonomy for **where in the format stack a payload
lives**. Orthogonal to [[carrier-family]] and [[stealth-class]].

## The five layers

- **`bit`** — payload is in raw bit(s) of the format's atomic unit.
  Pixel LSB for images, PCM sample LSB for audio, palette-entry LSB
  for GIF. Dies to any lossy re-encode that touches the bit plane.
- **`coefficient`** — payload is in a transform-domain value. JPEG
  DCT coefficients (F5, jsteg, OutGuess). Survives more re-encodes
  than `bit` when the transform is preserved (same Q table).
- **`character`** — payload is in the choice of Unicode codepoint(s).
  Zero-width, homoglyph, variation selectors, combining marks.
  Survives byte-preserving pipelines; dies to NFKC (see
  [[myth-homoglyph-nfkc]]).
- **`container`** — payload is in the format's container structure,
  outside the render path. PNG chunks (tEXt, iTXt, private), JPEG
  APPn segments, ZIP archive comment, PDF post-EOF, trailing bytes.
  Dies to format re-serializers.
- **`semantic`** — payload is in the *meaning* of the visible content.
  Capitalization pattern, word choice, whitespace pattern, timing
  channels. Survives whatever preserves the semantic content;
  paradoxically often dies to auto-formatters.

## Comparison to canonical_layer

`layer` is where a TECHNIQUE hides. [[canonical-layer]] is what a
TRANSPORT preserves. Survival = (technique.layer ≥
transport.canonical_layer).

## Usage in the KR

Every technique, signature, and myth record carries a `layer` field.
Filter with `stegg_search_records(layer=<layer>)`.

## Related

- [[carrier-family]] — orthogonal axis (medium).
- [[stealth-class]] — orthogonal axis (perceptibility).
