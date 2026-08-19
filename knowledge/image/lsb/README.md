# Image LSB steganography

Least-significant-bit substitution on raw pixel bytes. The canonical hide,
and the one every statistical detector attacks first.

Payload lives in the low bit(s) of one or more color channels of an
uncompressed image (PNG, BMP). Perturbations are within one integer
value per byte — imperceptible to the eye, statistically loud to the
right probe.

## What the ST3GG implementation does

`img_core.encode / img_core.decode` under the hood. See
[[image-lsb]] (technique record) and [[cap-image-lsb]] (capacity
formula) for the numbers.

Configurable axes:

- **channels** — `R | G | B | A | RG | RB | GB | RGB | RGBA`. Blue is
  the stealth default because BT.601 luminance weights blue at 0.11 vs
  0.30 red and 0.59 green — small perturbations in blue are the hardest
  for the eye to see. (Note in [[known-unknowns]]: the direct
  extrapolation from luminance weight to LSB detectability is not a
  controlled psychophysical result — it's a defensible heuristic.)
- **bits_per_channel** — 1 to 8. Prefer 1 or 2 for stealth; higher bits
  raise chi-square rate super-linearly and start banding visibly.
- **strategy** — `sequential | interleaved | spread | randomized`.
  Sequential fills channel-by-channel; interleaved rotates R/G/B/R/G/B;
  spread walks with a stride; randomized uses a seeded PRNG.
- **ST3GG v3 header** — password-derived HMAC-SHA256 magic, 16-bit
  length prefix, optional deflate, optional AES-256-GCM. See
  [[st3gg-v3-header]].

## The four questions

- **What is this?** → this README.
- **How do the numbers work?** → [[image/lsb/reference]] — bits-per-carrier,
  capacity formula, header layout, per-strategy traversal order.
- **What does an end-to-end run look like?** → [[image/lsb/walkthrough]] —
  the same 800-byte payload encoded, saved, decoded, verified byte-for-byte.
- **Is *this file* an example?** → [[image/lsb/recognition]] — the
  15-second triage: what a suspect PNG looks like at chi-square / RS /
  bit-plane entropy.

## Where it dies

- **JPEG re-encode / WhatsApp photo / Instagram**: the inverse-DCT
  rounding trip destroys pixel LSBs. See [[myth-lsb-survives-jpeg]] and
  [[myth-jpeg-steg-survives-recode]].
- **Deep bit-plane flattening** (some legit image-editing tools' "reduce
  noise" filter): rare in the wild but real.

## Where it survives

- **Any bit-preserving transport**: `slack_upload`, `http_raw`, `github_upload`,
  `email_attachment`, `telegram_file`. See [[sv-lsb-slack-upload]] for the
  reference measurement (6 channel/bit/strategy variants byte-identical
  through Slack's CDN).

## Detection

- **[[det-chi-square]]** — the original LSB detector (Westfeld &
  Pfitzmann 1999). Loud on jsteg-style straight LSB replacement.
- **[[det-rs]]** — RS-analysis (Fridrich et al. 2001). Smoothness-based;
  estimates the embedding rate.
- **[[det-spa]]** — sample-pair analysis (Dumitrescu et al. 2003).
  Different attack surface from RS; the two disagreeing on a carrier is
  itself a signal ([[sig-spa-rs-mismatch]]).
- **[[det-bit-plane-entropy]]** — visual + statistical bit-plane
  analysis; low entropy on a suspect plane = uncompressed ASCII payload,
  high entropy = encrypted / compressed.

## Sources

- [[st3gg-v3-header]] — the exact header format
- [[westfeld-pfitzmann-1999-chi2]] — chi-square attack
- [[fridrich-2001-rs]] — RS analysis
- [[kessler-primer]] — background primer
