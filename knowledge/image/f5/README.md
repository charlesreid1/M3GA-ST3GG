# F5 — matrix-encoded JPEG steg

Westfeld 2001. The reference JPEG steg technique for two decades. Every
subsequent JPEG scheme (nsF5, HUGO, UNIWARD) exists in reaction to F5.

The key idea: instead of flipping one coefficient per payload bit
(jsteg-style), use *matrix encoding* to hide k bits by flipping at most
one of `2^k - 1` coefficients. Fewer changes per bit → less statistical
disturbance.

## What the ST3GG implementation does

`img_core.f5_encode / img_core.f5_decode` (delegates to `f5_core`). See
[[image-f5]] and [[cap-image-f5]] for numbers.

Core operations:

1. Load JPEG, walk quantized DCT coefficients.
2. For each block of `2^k - 1` non-zero AC coefficients, compute their
   LSB parities. XOR with the next k payload bits gives a target
   position; flip that one coefficient's LSB.
3. **Shrinkage**: if a coefficient's LSB flip decrements its magnitude
   from ±1 to 0, that bit is lost — re-embed at the next block.
4. Write out the modified JPEG.

## The four questions

- **What is this?** → this README.
- **How does the matrix encoding work?** → [[image/f5/reference]] —
  parameter `k`, per-block encoding math, shrinkage handling, capacity
  formula.
- **What does an F5 encode look like end-to-end?** → [[image/f5/walkthrough]] —
  a 500-byte payload through a Q75 JPEG with k=3.
- **Is *this JPEG* an F5 example?** → [[image/f5/recognition]] — the
  F5 signature scan, chi-square profile, and how F5's histogram-preserving
  behavior distinguishes it from jsteg.

## Where it dies

- **Any JPEG re-encode with a different Q table** — F5's coefficient
  positions get re-quantized to different values. See
  [[myth-jpeg-steg-survives-recode]] and [[sv-f5-slack-upload]] (Slack
  destroys F5 payloads).
- **Chi-square-plus** era detectors — F5's shrinkage causes a specific
  histogram signature that stegdetect and Aletheia recognize.

## Where it survives

- **Bit-preserving JPEG transports**: `http_raw`, `github_upload`,
  `telegram_file`, `email_attachment` (as JPEG bytes, no re-encode).
- **Same-Q re-encode**: if you know the destination Q table exactly and
  the encoder is deterministic, F5 payloads can survive one round-trip.
  Not a robust property to lean on.

## Detection

- **[[det-f5-signature]]** — signature scan for the F5-shrinkage
  histogram pattern.
- **[[tool-aletheia]]** — modern ML-based detector; state-of-the-art
  since ~2019.
- Chi-square + RS attacks against LSB in coefficient space; F5 is
  significantly quieter than jsteg here (that's the whole point).

## Sources

- [[westfeld-2001-f5]] — the original paper (Westfeld, IH 2001)
- [[itu-t81-jpeg]] — JPEG standard (needed for the coefficient math)
- [[tool-stegdetect]] — includes F5 signature scan
- [[tool-aletheia]] — modern ML detector
