# CTF pattern: matryoshka decode

A payload nested through N successive LSB embeds — image in image in
image in image. Each layer is a ST3GG-format hide (or another
LSB-family scheme); the innermost layer holds the flag.

## The pattern

See [[image/matryoshka]] for the technique record ([[image-matryoshka]]).

## Solving

1. Decode the outer image's LSB. If it's ST3GG-format, extract
   with `stegg_lsb_smart_scan` or `stegg_decode_manual` with the
   password.
2. The extracted "payload" is itself a PNG. Save it and re-run
   step 1 on it.
3. Continue until an extraction returns non-PNG bytes (the flag or
   a leaf file).

Depth in the wild: ST3GG's SPECTER example runs depth 11. Real CTFs
typically use depth 3-5 — enough to slow the solver, not so much that
running the encoder becomes impractical.

## The password variance

Different challenges make different choices:

- **Same password every layer**: solver enters once, tool auto-
  descends.
- **Different password every layer** with the *previous layer's
  payload as a hint*: each extraction reveals the next password.
- **Different passwords with an external hint** (e.g. embedded in the
  cover image metadata, or in the CTF challenge description).

## The record

See [[ctf-matryoshka-image]] for the CTF-genre record.

## Solving discipline

Because each recursion is a full LSB extract, the solver's tool
must be scripting-friendly — running `stegg_lsb_smart_scan` 10 times
manually is not fun. Automate the loop.

## Sources

- [[st3gg-v3-header]] — the per-layer wrapping format
- [[st3gg-field-guide]] — SPECTER walkthrough (`examples/specter/`)
