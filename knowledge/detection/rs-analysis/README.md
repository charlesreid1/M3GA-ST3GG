# RS analysis (Fridrich, Goljan, Du 2001)

"Regular / Singular groups" — a spatial-domain LSB detector that
estimates the *rate* of embedding, not just its presence. More
sensitive than chi-square for pixel-domain LSB.

## What ST3GG uses it for

Included in `stegg_triage`'s statistical probe suite. See
[[det-rs-analysis]] and the field guide's "Reading the signals"
section on R>G>B rate patterns.

## The idea

Divide the image into groups of adjacent pixels (typically 4 pixels).
Define a discrimination function `f` (a smoothness metric — total
variation across the group).

For each group, apply a flipping function `F`:

- `F+1`: flip LSB up (0→1, 1→0 shift).
- `F-1`: flip LSB down (invert on odd values).
- `F0`: no change.

Classify each group as **Regular** (`f(F(group)) > f(group)` — flip
increased complexity), **Singular** (`f` decreased), or **Unusable**
(equal).

Under the null hypothesis (no steg), R and S counts should satisfy
`R_m ≈ R_{-m}` and `S_m ≈ S_{-m}` after applying `+m` and `-m` flip
masks. LSB embedding breaks the equality. The *asymmetry* between
`R_m` vs `R_{-m}` estimates the embedding rate.

## Why it beats chi-square

- **Rate estimation**: chi-square says "hit / not hit"; RS says "hit
  at rate 0.23 bpp."
- **Sensitivity**: RS fires at lower embedding rates than chi-square.
- **Works on spatial-domain LSB** where chi-square is aimed at DCT-
  domain LSB.

## Where it fires

- **[[image-lsb]]** (LSB replacement) — the primary target.
- **[[image-pvd]]** — fires weaker but present.

## Where it doesn't fire

- **LSB matching** — the flipping model doesn't apply cleanly.
- **F5 / OutGuess** — DCT-domain, RS is a pixel-domain attack.

## Signal patterns (from the field guide)

- **R>G>B decreasing rates**: hider embedded sequentially, top-down,
  one channel at a time. See signature record for the recipe.
- **R≈G≈B**: hider embedded interleaved or spread across channels.
- **Alpha=255 everywhere, RGB fires**: fingerprint pattern — hider
  used alpha as a "not-payload" marker. See
  [[myth-lsb-alpha-payload]].

## Sources

- [[fridrich-2001-rs]] — Fridrich, Goljan, Du 2001, "Reliable
  detection of LSB steganography in color and grayscale images"
- [[st3gg-field-guide]] — ST3GG-specific integration
