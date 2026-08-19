# chi-square rate

The specific value a chi-square estimator returns. Ranges 0.0 (no
detection) to 1.0 (maximum detection).

## What it estimates

For LSB replacement (see [[detection/chi-square]]), chi-square
estimates the **fraction of the LSB plane that has been overwritten
by payload**. A chi-square rate of 0.5 means "roughly half the image's
LSB plane is embedded payload."

## Why "rate" ≠ "detection"

- **Rate ~ 0.0**: no embedding, OR a very small payload that's
  statistically indistinguishable from noise.
- **Rate ~ 0.1 - 0.3**: possible small payload, possible
  false-fire on a very smooth cover.
- **Rate ~ 0.5**: strong signal, likely embedded.
- **Rate ~ 0.8+**: confident detection.

But: **a chi-square rate of 1.0 does not mean "definitely embedded."**
False fires happen on:

- Very smooth carriers (gradients, alpha=255 masks — see
  [[myth-lsb-alpha-payload]]).
- Palettized images with unusual palette distributions.
- Images that were already re-processed by a lossy step that
  equalized the histogram.

## In the KR

`stegg_triage`'s output reports chi-square rate as a number in the
range [0, 1]. Read it as "signal strength," not as "probability of
detection." Cross-check with [[detection/rs-analysis]] and
[[detection/sample-pairs]] before declaring `*FOUND*`.

## Related terms

- [[stealth-class]] — a technique's rating for how easily it evades
  chi-square (and other detectors).

## Sources

- [[westfeld-pfitzmann-1999-chi2]] — the chi-square attack paper
- [[st3gg-field-guide]] — ST3GG interpretation
