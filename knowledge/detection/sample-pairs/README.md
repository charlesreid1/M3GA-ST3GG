# Sample-pairs analysis (Dumitrescu, Wu, Wang 2003)

An LSB-replacement detector based on adjacent-pixel-pair statistics.
Sensitive at low embedding rates; often the first probe to catch
sub-1% payloads.

## What ST3GG uses it for

Included in `stegg_triage`'s statistical probe suite. See
[[det-sample-pairs]] and the field guide's "Reading the signals"
section.

## The idea

Take pairs of adjacent pixels `(x, y)`. Partition into four sets
based on parity:

- P1: `x` even, `y` even
- P2: `x` even, `y` odd
- P3: `x` odd, `y` even
- P4: `x` odd, `y` odd

In real images, `|P2| ≈ |P3|` (the "even-odd" and "odd-even" counts
are roughly equal by symmetry). LSB replacement disturbs this
equality by moving pixel-pair identities between the four groups —
and the disturbance's magnitude estimates the embedding rate.

## Why SPA is sensitive

Where RS looks at *groups* of pixels and their flipped versions
(one operation per group), SPA looks at *pairs* and derives an
analytical rate estimate from a system of linear equations. Fewer
degrees of freedom, tighter noise floor, better performance at
sub-2% embedding.

## Where it fires

- **[[image-lsb]]** replacement (the target).
- **Non-naive traversal** — SPA notices even when the LSB traversal
  order is randomized (as long as replacement is used).

## Where it doesn't fire

- **LSB matching** — the ±1 arithmetic breaks the pair-partition
  count symmetry differently.
- **F5** — DCT-domain, out of scope.

## SPA + RS disagreement is a signal

When SPA and RS report noticeably different rates on the same image,
it's a diagnostic:

- **SPA > RS**: possibly LSB with a passphrase-randomized traversal.
  RS assumes sequential order.
- **RS > SPA**: possibly PVD or edge-adaptive LSB. SPA's pair
  assumption is weakest at edges.

## Sources

- [[dumitrescu-2003-spa]] — Dumitrescu, Wu, Wang 2003
- [[st3gg-field-guide]] — ST3GG-specific integration
