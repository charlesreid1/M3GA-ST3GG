# The F5 → nsF5 → HUGO → S-UNIWARD academic lineage

Twenty years of JPEG steganography research, each generation
designed to defeat the prior generation's canonical attack.

## The arc

### F5 (Westfeld 2001)

**Innovation**: matrix encoding — hide a k-bit codeword by flipping
at most one of `2^k - 1` DCT coefficients. Minimizes changes for a
given payload size.

**Defeats**: chi-square (Westfeld-Pfitzmann 1999). Chi-square works
by noticing pair-equalization in histograms; matrix encoding barely
disturbs any pair.

**Weak against**: F5-signature scan (Fridrich et al.), which
specifically targets F5's shrinkage-handling artifacts (see
[[image/f5]] technical body).

### nsF5 (Fridrich, Pevný, Kodovský 2007)

**Innovation**: no-shrinkage F5 — replaces the decrement-toward-
zero + re-embed cycle with a wet paper code approach. Eliminates
the shrinkage artifact that F5-signature scan detects.

**Defeats**: F5-signature scan. nsF5 doesn't produce the same DCT-
histogram depression.

**Weak against**: calibration-based blockiness attacks (Fridrich
2004), which compare the observed DCT stats to a re-JPEG-at-same-Q
reference.

### HUGO (Pevný, Filler, Bas 2010)

**Innovation**: cost-function-driven adaptive embedding. Instead of
"pick coefficients uniformly," HUGO computes a per-coefficient
distortion cost (based on how much statistical damage a flip would
do) and preferentially embeds in low-cost coefficients.

**Defeats**: calibration attacks. HUGO's cost function is
calibrated against the very statistics the calibration attack uses.

**Weak against**: SRM (Spatial Rich Models, Fridrich 2012), which
uses a large feature space combined with ML classifiers.

### S-UNIWARD (Holub & Fridrich 2013)

**Innovation**: universal wavelet-relative distortion — cost function
based on multi-scale wavelet decomposition. More robust than HUGO
against SRM-style feature extractors.

**Defeats**: SRM-based detectors of its time.

**Current state**: modern ML-based detectors (Aletheia, deep
convolutional networks from the Alaska2 era) can achieve high
accuracy on S-UNIWARD-embedded images at moderate embedding rates.
The arms race continues.

## The pattern

Each generation:

1. Uses more information about the cover to guide embedding.
2. Defeats the specific attack against the prior generation.
3. Is defeated by a *broader* attack (bigger feature space, more
   training data, deeper models).

The frontier has moved from *hand-crafted statistical properties* to
*learned representations*. A 2025-era steganalysis system trained on
millions of covers can distinguish S-UNIWARD-encoded from clean at
rates that no 2010-era research would have believed.

## The ST3GG connection

`img_core.f5_encode` implements classical F5 (matrix encoding +
shrinkage handling). ST3GG does not implement nsF5, HUGO, or
S-UNIWARD. For CTF-grade JPEG steg, classical F5 is enough; for
academic-grade undetectability, reach for the S-UNIWARD reference
implementations in the Aletheia toolkit.

## Sources

- [[westfeld-2001-f5]] — F5 paper
- Fridrich et al. 2007 — nsF5 paper
- Pevný, Filler, Bas 2010 — HUGO paper
- Holub & Fridrich 2013 — S-UNIWARD paper
- [[alaska2-competition]] — modern ML-based detection benchmark
