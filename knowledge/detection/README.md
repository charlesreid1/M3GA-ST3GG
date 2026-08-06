# Detection — reading the signals

When the extractor bounces, the signals are still evidence. This
topic collects the detectors ST3GG runs and the pattern-diagnosis
field guide that translates their output into a technique name.

## Detectors

- **[[det-chi-square]]** — classic first-generation LSB detector.
  False-fires on smooth carriers.
- **[[det-rs]]** — RS analysis. Smoothness-based, estimates
  embedding rate rather than yes/no.
- **[[det-spa]]** — sample-pair analysis. Different failure modes
  than RS; disagreement between the two is itself a signal.
- **[[det-bit-plane-entropy]]** — per-plane Shannon entropy plus
  the visual attack (render each plane as an image).
- **[[det-f5-signature]]** — byte-scanner for F5's header.
- **[[det-pvd-histogram]]** — step anomalies at PVD range
  boundaries.

## Reading the signals

The field guide's signature catalog is now typed records:

- **[[sig-decreasing-rgb]]** — SPA/RS falls off R > G > B →
  sequential embedding, 1 bpc, starting at top of image.
- **[[sig-equal-rgb]]** — equal across channels → interleaved /
  spread. Magnitude discriminates 1 vs 2 bpc.
- **[[sig-multiple-bit-planes]]** — bit_0 AND bit_1 both flagged
  → 2 bpc.
- **[[sig-low-plane-entropy-ascii]]** — suspicious plane at entropy
  2-4 → uncompressed ASCII payload.
- **[[sig-high-plane-entropy-encrypted]]** — plane entropy ~7.9-8.0
  → compressed or encrypted. Cannot recover without the key.
- **[[sig-alpha-all-ones]]** — every alpha LSB = 1 → NOT a payload,
  fingerprint / opaque-source. See [[myth-lsb-alpha-payload]].
- **[[sig-spa-rs-mismatch]]** — SPA screaming but RS quiet (or
  vice versa) → not naive LSB replacement.
- **[[sig-f5-hit-on-png]]** — F5 signature on a PNG → almost always
  false positive.
- **[[sig-direct-pixel-overwrite]]** — SPA/RS screaming + low
  entropy + visible banding → payload IS the pixel bytes, not LSB.

Every signature carries a `next_action` and, for the strongest two,
a runnable Python snippet.
