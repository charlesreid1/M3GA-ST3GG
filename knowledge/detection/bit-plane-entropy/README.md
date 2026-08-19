# Bit-plane entropy analysis

Break an image into 8 bit planes per channel and measure the
Shannon entropy of each plane. Payload (especially encrypted or
compressed payload) drives the LSB plane's entropy toward 8.0
bits/byte; clean image LSBs have entropy ~2-4 bits/byte.

## What ST3GG uses it for

`stegg_triage`'s statistical probe suite includes a bit-plane
entropy scan. See [[det-bit-plane-entropy]] and the field guide's
"Reading the signals" section on low-entropy vs high-entropy LSB
patterns.

## The idea

- **Clean image LSB plane** — encodes perceptual noise that's
  correlated with the image content. Entropy is 2-4 bits/byte.
- **Uncompressed ASCII payload embedded in LSB** — text has entropy
  ~4-5 bits/byte, and it comes across in the LSB plane as clearly-
  structured bytes with ASCII printable ranges.
- **Compressed or encrypted payload in LSB** — high entropy, ~7.9-8.0
  bits/byte. Statistically indistinguishable from noise, but the
  entropy itself is anomalous compared to a clean cover.

## The two diagnostic patterns

**Low LSB entropy (~2-4)**: signals uncompressed ASCII payload
directly written into pixels. Manual bit dump of the LSB plane
usually recovers the plaintext.

**High LSB entropy (~7.9-8.0)**: signals compressed or encrypted
payload. Extraction may still fail without the password, but the
presence of "too-random" LSB bits is a signal on its own.

Compare to the reference-clean baseline for the same image family
(cameras produce known-clean baseline; screenshots produce another).

## Where it doesn't fire

- **PVD / F5 / OutGuess**: bit-plane entropy is a spatial-LSB probe.
  DCT-domain methods don't uniformly perturb the pixel bit plane.
- **Very small payloads in a very large image**: 100 bytes in 4 MB
  of pixels won't shift entropy above noise.
- **Alpha=255 everywhere (fingerprint pattern)**: perfect uniform-
  bit LSB, entropy = 0. See [[myth-lsb-alpha-payload]].

## Multiple bit-planes flagged

When triage reports "bit planes 0 AND 1 flagged" (or "0, 1, 2"),
the payload was hidden at 2 bpc or 4 bpc. Recipe: manual raw-bit
dump of the low N bits per channel, sequential order first.

## Sources

- [[fridrich-2001-rs]] — RS-analysis paper, discusses bit-plane
  visual attack too
- [[st3gg-field-guide]] — ST3GG-specific bit-plane heuristics
