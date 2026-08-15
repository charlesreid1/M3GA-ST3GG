# jsteg — LSB over nonzero DCT AC coefficients

The simplest JPEG steganography. LSB replacement on nonzero AC
coefficients. Derek Upham, 1993 — the granddad of JPEG-domain hiding.

## What the ST3GG implementation does

`img_core.jsteg_encode / img_core.jsteg_decode`. See [[image-jsteg]].

Algorithm:

1. Read the JPEG's quantized DCT coefficients (post-DCT, pre-Huffman).
2. Iterate through nonzero AC coefficients (skip DC, skip zeros).
3. For each carrier coefficient, replace its LSB with a payload bit.
4. Re-serialize the JPEG.

Framing: 16-bit length prefix, then raw payload bits. Capacity:
1 bit per nonzero AC coefficient (typically 5-15% of total
coefficients in a natural image).

## Why it's detectable

jsteg replaces LSBs on values without regard to statistical
distribution. The result: adjacent DCT coefficient values 2*k* and
2*k*+1 become equally populated (because bits flip in one
direction as often as the other). Real JPEGs have a strongly
non-uniform DCT distribution — [Westfeld & Pfitzmann 1999][chi2]
noticed this asymmetry and built the chi-square attack around it.
Chi-square on a jsteg-encoded JPEG returns very high values;
chi-square on a clean JPEG returns near-zero.

[chi2]: knowledge/records/bibliography.json — see westfeld-pfitzmann-1999-chi2

## Where it dies

- **Any JPEG re-encode** with a different Q table. See
  [[myth-jpeg-steg-survives-recode]].
- **Chi-square attack** rings loud on jsteg output; treat as
  puzzle-adjacent rather than stealth-grade.

## Where it survives

- Byte-identical JPEG delivery (HTTP raw, GitHub, email attachment).

## History and relatives

- **jsteg** (1993, Derek Upham): the original — this record.
- **jphide / jphs** (1998, Allan Latham) — jsteg's successor with a
  passphrase-selected embedding order. Not shipped in `img_core`.
- **[[image-f5]]** (Westfeld 2001) — matrix encoding replaces jsteg's
  brute LSB with chi-square-resistant hiding.
- **[[image-outguess]]** (Provos 2001) — statistical-preserving
  jsteg-alternative.

## Detection

- **Chi-square** ([[det-chi-square]]) is the primary attack. Reference
  detector: `stegdetect` ([[stegdetect]]).
- Any DCT-histogram flatness estimator flags jsteg output.

## Sources

- [[itu-t81-jpeg]] — JPEG spec
- [[westfeld-pfitzmann-1999-chi2]] — the chi-square attack
- [[st3gg-field-guide]] — ST3GG-specific framing
