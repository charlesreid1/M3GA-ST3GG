# Reading the signals — pattern diagnosis when extraction fails

The `stegg_lsb_smart_scan` and `stegg_decode_manual` tools require a
`ST3GG` magic header. When the hider used a different scheme (raw
bytes, another tool, homebrew), those extractors return "no
extraction" even when payload is plainly present. Pattern diagnosis
is what you do next.

## What ST3GG uses it for

The signature catalog is `signatures.json` — 9 typed records, each
with `pattern`, `probable_technique`, `next_action`, `strength`,
and often a `python_snippet` you can paste into a REPL.

## The 9 signature patterns

1. **R>G>B decreasing rates** — sequential embed from top, one
   channel at a time. Recipe: manual raw-bit dump R, sequential,
   1 bpc.
2. **R≈G≈B rates** — interleaved or spread. Recipe: RGB
   channels, interleaved, sequential.
3. **Multiple bit-planes flagged** — 2 bpc or 4 bpc. Recipe: dump
   low 2 (or 4) bits per channel.
4. **Low LSB entropy (~2-4)** — uncompressed ASCII payload
   directly written. Recipe: dump LSB plane, decode as ASCII.
5. **High LSB entropy (~7.9-8.0)** — compressed / encrypted payload.
   Extraction requires the key; presence itself is a signal.
6. **Alpha=255 everywhere, RGB fires** — fingerprint pattern; alpha
   is the "not-payload" marker. Real payload is in RGB. See
   [[myth-lsb-alpha-payload]].
7. **SPA/RS disagreement** — LSB matching OR non-naive traversal.
   Recipe: try LSB±1 extraction, or brute-force traversal orders.
8. **F5 on PNG** — false positive. F5 signature scan on a PNG
   returns garbage. Ignore.
9. **SPA + RS + low entropy + banding** — direct pixel overwrite
   (not LSB modification). Recipe: dump the affected pixel
   region raw.

## Why this exists as its own topic

The field guide (Layer 4) makes this a first-class response mode:
when the extractors bounce but the signals point at a technique,
NAME the technique, hand over the recipe (channels + bits +
strategy), and be honest that the ST3GG toolchain needs a raw-bit
extractor to finish. "I diagnosed the technique but can't recover
the bytes" is a real answer — better than a hand-wave.

## Tooling gap

ST3GG's current extractors are ST3GG-header-aware only. A raw-bit
extractor that takes `channels + bits + strategy` and emits raw
bytes (no header) would close the loop on every one of these
signatures. Documented in [[known-unknowns.md]] as a gap.

## Sources

- [[fridrich-2001-rs]] — RS analysis (signature 1, 2, 6)
- [[dumitrescu-2003-spa]] — SPA (signature 7)
- [[westfeld-pfitzmann-1999-chi2]] — chi-square (signature 4, 5)
- [[st3gg-field-guide]] — ST3GG-specific pattern-diagnosis
