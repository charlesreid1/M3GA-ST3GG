# OutGuess — statistical-preserving JPEG steganography

Niels Provos, 2001. Two-pass JPEG steg: first pass hides the
payload; second pass corrects the DCT coefficient histogram back to
its original distribution. Designed specifically to defeat the
chi-square attack that killed jsteg.

## Not in ST3GG's img_core

OutGuess is a *reference* record — the reference technique from the
2001-era JPEG-steg literature — but ST3GG's `img_core` does not ship
its own OutGuess implementation. Interop is via the external
`outguess` binary; see [[tool-outguess]] and [[image-outguess]].

## Algorithm sketch

1. **Embed pass**: iterate nonzero DCT coefficients in a passphrase-
   derived pseudorandom order, LSB-replace with payload bits (roughly
   jsteg's mechanic but permuted).
2. **Correction pass**: for each pair `(2k, 2k+1)` in the DCT
   histogram, count how many changes were made and swap other
   coefficients to restore the pair's original occupancy count.

The second pass is the innovation — after it runs, chi-square on the
output cannot distinguish the DCT distribution from the cover's.

## Where it dies

- **Chi-square is out; calibration is in.** Fridrich et al.'s 2002
  calibration attack — re-JPEG at same Q, diff DCT histograms, compare
  blockiness signature — reliably distinguishes OutGuess output from
  clean covers. See [[det-chi-square]] context and [[myth-chi-square-outguess]].
- **Same-Q recompression bounds capacity**: the second pass uses
  neighboring coefficients to correct the histogram, so effective
  capacity is roughly half of jsteg's.

## Where it survives

- Byte-identical JPEG transports (same as any DCT-layer method).
- Chi-square-only detectors bounce off cleanly. Any 2001-era
  steganalysis tool will report "clean."

## The academic lineage

OutGuess (2001) → **F5** (Westfeld 2001, [[image-f5]]) → **nsF5**
(Fridrich 2007, no-shrinkage F5) → **HUGO** (Pevný et al. 2010,
Highly Undetectable steGO) → **S-UNIWARD** (Holub & Fridrich 2013,
current SOTA for JPEG steganography). Each generation defeats the
prior generation's canonical attack. OutGuess is the first
statistical-preserving link in the chain.

## Interop

The `outguess` binary is preserved by a few Linux distros; the
canonical repo has been mirrored to GitHub. Not compatible with F5,
jsteg, or steghide — see [[myth-steghide-reads-outguess]].

## Sources

- [[provos-2001-outguess]] — the original paper
- [[westfeld-pfitzmann-1999-chi2]] — the attack OutGuess defeats
- [[st3gg-field-guide]] — ST3GG-specific framing
