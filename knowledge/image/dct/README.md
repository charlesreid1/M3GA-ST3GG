# Image DCT-domain steganography (generic)

Payload written into the JPEG DCT coefficient stream, at the layer
above raw pixels and below the byte-serialized JPEG file. The layer
that survives lossy re-encoding (when the destination quantization
table matches the source).

## What the ST3GG implementation does

`img_core.dct_encode / img_core.dct_decode`. See [[image-dct]] and
[[cap-image-dct]].

Key parameters:

- **Block size**: 8 (fixed by the JPEG spec).
- **Robustness**: `low | medium | high`. Higher robustness embeds in
  more resistant coefficient positions (low-frequency mid-range ACs)
  at reduced capacity.
- **Capacity**: roughly 1 bit per 64 pixels for `low`, dropping to
  ~1 bit per 200-500 pixels for `high` depending on the cover.

Framing: ST3GG v3 header (magic + length + optional compress +
optional AES) written into the LSB of selected DCT coefficients.

## Where it dies

- **Any re-quantization with a different Q table**: JPEG at quality
  Q1 encodes with QT1; recompressing with QT2 (Slack, WhatsApp,
  Telegram photo) rounds the coefficients through QT2/QT1 and
  destroys the low-order bits. See [[myth-jpeg-steg-survives-recode]].
- **Chroma subsampling changes**: 4:4:4 → 4:2:0 recompression is
  destructive to chroma-plane DCT hides.
- **Cropping / rotation**: any spatial transform destroys the block
  alignment.

## Where it survives

- **Byte-identical JPEG delivery**: HTTP raw, GitHub upload, email
  attachment. See [[sv-dct-slack-upload]] (⚠ tuned only).
- **Same-Q re-encode**: if the destination pipeline uses the same
  quality setting *and* the same libjpeg build, coefficients can
  survive. Fragile; per-pipeline probing required.

## Relationship to F5 and jsteg

DCT is the *layer*; F5 and jsteg are specific *techniques* that
operate at that layer:

- **[[image-jsteg]]** — simplest: LSB replacement on nonzero AC
  coefficients. Detectable by chi-square.
- **[[image-f5]]** — matrix encoding + shrinkage handling, minimizes
  coefficient changes, chi-square-resistant.
- **[[image-outguess]]** — statistical-preserving via a second-pass
  histogram correction.

`img_core.dct_encode` is a *generic* DCT layer with configurable
robustness — the tuned-robustness variants are what showed ⚠ survival
on Slack upload in the 2026-07 probe.

## Detection

- Chi-square on DCT coefficient histogram
  ([[det-chi-square]] via `westfeld-pfitzmann-1999-chi2`).
- Calibration attack: re-JPEG at same Q and diff histograms.
- Blockiness attack: DCT-domain embedding subtly increases 8×8 block
  boundary artifacts.

## Sources

- [[itu-t81-jpeg]] — the JPEG spec (T.81)
- [[st3gg-field-guide]] — ST3GG-specific tuned-robustness framing
