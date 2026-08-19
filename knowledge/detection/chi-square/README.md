# Chi-square attack (Westfeld & Pfitzmann 1999)

The first statistical attack against LSB-family steganography.
Detects the "same-parity pairs equalization" that LSB replacement
creates in pixel value or DCT coefficient histograms.

## What ST3GG uses it for

`stegg_triage`'s statistical probe suite includes a chi-square
estimator. See [[det-chi-square]] and the field guide's "Reading the
signals" section.

## The idea

Consider pixel values (or DCT coefficients) grouped into adjacent
pairs: `(0,1)`, `(2,3)`, `(4,5)`, ...

- **Real images**: adjacent pixel-values are NOT equally common —
  brightness distributions are smooth curves, so `count(2) ≠ count(3)`
  in general.
- **After LSB replacement**: for every pair `(2k, 2k+1)`, LSB flipping
  moves values between the two — the counts equalize (they become
  the same after enough embedding).

Chi-square measures the goodness-of-fit of the pair-values-are-equal
hypothesis against the observed counts. Real images: low chi-square
(the equal-counts hypothesis fits badly). LSB-embedded images: high
chi-square (equal counts fit well).

## Where it fires

- **jsteg** (LSB over DCT coefficients) — the reference target.
  See [[image-jsteg]].
- **Pixel-domain LSB replacement** (see [[image-lsb]]) — fires
  when the payload is large enough to equalize the histogram pairs.

## Where it doesn't fire

- **F5** ([[image-f5]]) — matrix encoding minimizes coefficient
  changes; chi-square barely notices.
- **OutGuess** ([[image-outguess]]) — designed to defeat chi-square
  specifically. See [[myth-chi-square-outguess]].
- **PVD** ([[image-pvd]]) — bit modifications concentrate at edges,
  not uniformly across the histogram.
- **LSB matching** (aka LSB±1) — adds/subtracts 1 rather than
  replacing LSB. No pair-equalization → no chi-square hit.

## False positives

- **Smooth carriers**: gradients, blurred images, alpha=255-everywhere
  masks. The paired-histogram equal-counts hypothesis fits naturally
  well on smooth data.
- **Palette images** with LSB modified. Chi-square on palettized
  pixels doesn't behave the same way.

## Sources

- [[westfeld-pfitzmann-1999-chi2]] — Westfeld & Pfitzmann 1999,
  "Attacks on Steganographic Systems"
- [[stegdetect]] — reference detector implementing chi-square
- [[st3gg-field-guide]] — ST3GG-specific integration
