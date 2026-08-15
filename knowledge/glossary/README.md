# Glossary

Canonical definitions for terms used across the ST3GG knowledge base
and records. One term per file. When a record or another prose file
uses a term of art without expanding it, look here.

## Terms

- **[[canonical-layer]]** — the layer a transport treats as "the real
  message." The single principle behind [[transport/canonicalization]].
- **[[matrix-encoding]]** — the F5 primitive: hide k bits by flipping
  at most one of 2^k-1 carriers.
- **[[shrinkage]]** — the F5 edge case where a coefficient decrements
  to zero and must be re-embedded elsewhere.
- **[[chi-square-rate]]** — the specific value chi-square estimators
  report, and why "high chi-square rate" is not "positive detection."
- **[[stealth-class]]** — the ST3GG-record taxonomy for how
  perceptible a technique is (invisible / prose-like /
  visibly-perturbed).
- **[[carrier-family]]** — the ST3GG-record taxonomy of what medium
  a technique embeds into (image / text / emoji / audio / network /
  document).
- **[[layer]]** — the ST3GG-record taxonomy of *where in the format
  stack* the payload lives (bit / coefficient / character / container /
  semantic).
- **[[capacity-formula]]** — the closed-form byte-count expression
  each technique carries in its `technical_body`.
- **[[header-format]]** — the framing scheme each technique uses to
  frame the payload for the receiver.

## Convention

Each term file is a short reference: definition first, examples
second, cross-links to records third. Keep entries short — a
glossary is a lookup, not a book.

## Sources

- The individual entries link to their primary refs.
- The taxonomy files (`carrier-family`, `layer`, `stealth-class`)
  match the enums used in `records.py`.
