# Image steganography

Payload hidden inside an image carrier. Where the payload lives
depends on the carrier's *layer*:

- **[[layer-bit]]** — LSB in raw pixel bytes. Cheapest to encode,
  first thing every statistical detector attacks. See
  [[image-lsb]] (canonical ST3GG v3), [[image-pvd]] (pixel-value
  differencing), [[image-matryoshka]] (recursive nesting), and
  [[image-gif-palette-lsb]].
- **[[layer-coefficient]]** — quantized DCT coefficients on JPEG.
  Survives JPEG re-quantization *if the destination Q matches*.
  [[image-f5]], [[image-jsteg]], [[image-dct]].
- **[[layer-container]]** — the file structure itself. PNG chunks,
  trailing bytes, polyglots. Trivially detectable but easy to add:
  [[image-png-text-chunk]], [[image-png-private-chunk]],
  [[image-trailing-bytes]], [[image-polyglot]],
  [[image-gif-comment]], [[image-apng-fdat]].

## Which one to reach for

- **Bit-perfect delivery** (HTTP raw, GitHub, email attachment,
  Slack file upload for PNG): [[image-lsb]] wins on capacity, sits
  invisibly under any pixel inspection at 1 bpc.
- **JPEG must round-trip through recompression**: DCT layer.
  [[image-dct]] with `robustness=medium` or `high`; pre-flight with
  `dct_capacity`. [[image-f5]] is the reference matrix-encoding
  scheme but dies on requantization outside its source Q table.
- **Slack upload, want image metadata to survive**:
  [[image-png-private-chunk]] (Slack strips *named* text chunks but
  passes 4-char private chunks — see [[myth-slack-preserves-metadata]]).
- **Puzzle / CTF theatrics** where obviousness is fine:
  [[image-trailing-bytes]] or [[image-polyglot]].

## Detection

Statistical: [[det-chi-square]], [[det-rs]], [[det-spa]],
[[det-bit-plane-entropy]]. Structural: `stegg_read_png_chunks`,
`stegg_detect_trailing`, `stegg_carve`.

For pattern-diagnosis when the extractor bounces but the signals are
loud, see [[sig-decreasing-rgb]], [[sig-equal-rgb]],
[[sig-multiple-bit-planes]], [[sig-low-plane-entropy-ascii]],
[[sig-high-plane-entropy-encrypted]], [[sig-alpha-all-ones]],
[[sig-direct-pixel-overwrite]].

## Transport survival

See [[transport/README]] for the general principle. Slack-specific
verdicts: [[sv-lsb-slack-upload]] (survives), [[sv-f5-slack-upload]]
(dies), [[sv-png-textchunk-slack-upload]] (stripped),
[[sv-png-private-chunk-slack-upload]] (survives),
[[sv-dct-slack-upload]] (tuned only).
