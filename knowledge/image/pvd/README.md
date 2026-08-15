# Image PVD — Pixel Value Differencing

Payload bits embedded in the *difference* between adjacent pixel
pairs. Adaptive capacity: smooth areas carry fewer bits, edges carry
more. Better statistical stealth than raw LSB against RS/SPA.

## What the ST3GG implementation does

`img_core.pvd_encode / img_core.pvd_decode`. See [[image-pvd]] and
[[cap-image-pvd]].

Algorithm (Wu-Tsai 2003 variant, ST3GG default):

1. Walk pixel pairs `(p_i, p_i+1)` in scan order.
2. Compute difference `d = p_i+1 - p_i`.
3. Look up `d`'s range in a fixed range-table
   (e.g. `[0..7, 8..15, 16..31, 32..63, 64..127, 128..255]`).
4. Number of bits to embed = `log2(range_width)`. Wider range = more
   bits.
5. Modify the pair to encode payload bits while keeping the new `d'`
   in the same range.

Direction: horizontal (default) or vertical. Range type:
Wu-Tsai (default) or Chang-Tseng.

## Why it beats LSB statistically

LSB replacement produces a uniform, detectable bias in the LSB plane
(chi-square, RS, SPA all fire on it). PVD encodes bits into
inter-pixel *differences*, so the LSB plane is not disturbed
uniformly — the changes are concentrated in edges where they're
perceptually hidden and statistically noisier. RS analysis and SPA
both underperform on PVD compared to LSB.

Trade-off: capacity varies with cover content. A smooth image (blue
sky) barely fits anything; a busy image (edges, texture) fits more.

## Where it dies

- **Any lossy re-encode**: PVD is a pixel-domain technique like LSB.
  JPEG re-encoding, HEIC transcode, WebP-lossy destroy the pair-
  difference structure. See [[myth-pvd-survives-jpeg]].
- **Downscaling / upscaling**: pixel resampling rewrites adjacency.
- **Blur / smoothing filters**: destroy the fine differences.

## Where it survives

- Byte-identical PNG delivery (Slack upload, GitHub, HTTP raw).
- Any transport where the PNG IDAT survives unchanged.

## Detection

- Histogram of pixel-pair differences: PVD flattens the range-boundary
  distribution. A trained detector notices the artifacts.
- Chi-square on the LSB plane: fires weaker than on LSB but still
  fires with enough embedding.
- RS analysis: less sensitive to PVD than to LSB but not blind.

## Sources

- [[anderson-petitcolas-1998-survey]] — Anderson & Petitcolas survey
  covering the PVD family
- Wu & Tsai 2003 (referenced via [[st3gg-field-guide]]) — original
  PVD paper
- [[st3gg-field-guide]] — ST3GG-specific framing
