# shrinkage

An F5 edge case. When [[matrix-encoding]] says "flip carrier at
position i," and that flip would push the coefficient value to zero,
the coefficient becomes indistinguishable from natural
JPEG-quantized zero coefficients — and F5's decoder skips zero
coefficients. The bit is lost.

## The fix (F5's shrinkage handling)

1. Notice: the flip would take a coefficient from ±1 to 0.
2. "Shrink": actually perform the decrement (the coefficient is now
   0). Do NOT count this position toward the current payload group.
3. Move to the next position and re-embed the same bit there.

Effective capacity is reduced by roughly 5-10% because some positions
"consume" a change without carrying a payload bit.

## Why nsF5 exists

Fridrich, Pevný, and Kodovský's nsF5 (2007) eliminates shrinkage by
using wet-paper codes instead of the decrement-and-retry cycle.
Same statistical benefit, less capacity loss, no shrinkage-signature
detectable trace.

## In the KR

- [[image-f5]] `technical_body.shrinkage_handling` = "decrement toward
  zero + re-embed"
- [[cap-image-f5]] cites ~5-10% shrinkage overhead as the standard
  ballpark. Not measured on ST3GG's specific implementation — see
  [[known-unknowns.md]] for the outstanding measurement.
- [[detection/f5-signature]] — the shrinkage artifact is what
  F5-signature scanners look for.

## Sources

- [[westfeld-2001-f5]]
