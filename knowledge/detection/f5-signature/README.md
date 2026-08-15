# F5 signature detection

Detects [[image-f5]]-embedded JPEGs by looking for the artifacts F5's
matrix encoding + shrinkage handling leave in the DCT coefficient
histogram. Reference implementation is Provos's `stegdetect`.

## The idea

F5 embeds by decrementing selected DCT coefficients toward zero
(matrix encoding + shrinkage). The result is a slight but
characteristic distortion in the DCT histogram — specifically, a
depression around the values `±1, ±2` that grows with embedding
rate.

Compare the observed histogram to a "calibrated" reference (re-JPEG
at same Q, or a model built from clean covers of the same content
class). Substantial deviation → F5 signature.

## What ST3GG uses it for

`stegg_triage`'s image-family probe suite includes an F5-signature
estimator. Fires on F5-embedded JPEGs; false-positives on some
low-quality-JPEG covers where the DCT histogram is naturally
depressed.

## Where it fires

- **[[image-f5]]** — the target.
- Occasionally on OutGuess when the second-pass histogram correction
  didn't complete.

## Where it false-fires

- **Very low quality JPEGs** (Q<30): quantization already flattens
  the histogram; the F5 signature looks similar.
- **PNGs**: no DCT histogram to analyze. `stegdetect` may still run
  but produces meaningless output. See the "F5-on-PNG false
  positive" signature record.

## Tool references

- **`stegdetect`** (Niels Provos): the reference implementation.
  Also detects jsteg, jphide, invisible-secrets. See [[stegdetect]].
- **Aletheia** (Daniel Lerch): modern ML-based JPEG stego detector;
  includes F5 sensitivity.

## Sources

- [[westfeld-2001-f5]] — F5 paper (describes the signature)
- [[fridrich-2001-rs]] — general steganalysis framework
- [[stegdetect]] — reference detector
- [[st3gg-field-guide]] — ST3GG-specific triage integration
