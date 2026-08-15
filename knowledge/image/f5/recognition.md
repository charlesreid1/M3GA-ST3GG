# F5 — 15-second triage

"Is this JPEG an F5 hide?"

## The F5 histogram signature

The single strongest tell: **DCT coefficient magnitude=0 count is higher
than a clean image of the same content would have**. Every shrinkage
event during F5 embedding decrements a ±1 coefficient to 0, so a
population of coefficients migrates from ±1 to 0 that no natural image
process produces.

Read the coefficient histogram of the suspect JPEG. A clean cover has:

```
±1 count : ~15-20% of nonzero coefs
0 count  : ~60-70% of all coefs (typical for natural photos)
```

An F5 stego has:

```
±1 count : ~14-17% (depressed)
0 count  : slightly elevated (+shrinkage_events)
```

Absolute-magnitude effect is small (dozens of coefs on a 1080p) but
statistically distinctive vs a same-content clean image. See
[[det-f5-signature]].

## Practical detection flow

1. **File-type check** — is it actually a JPEG? F5 signature on a PNG
   is a false positive (see [[sig-f5-hit-on-png]]).
2. **stegdetect / Aletheia** — run one of the F5-aware detectors. Both
   look for the shrinkage histogram, plus (in Aletheia's case) ML
   features across many coefficient bands.
3. **Chi-square** — F5 was designed to be quiet against chi-square.
   A LOUD chi-square hit + JPEG carrier is more likely jsteg than F5.
4. **Compare against a clean estimate** — if the challenge author gave
   you an "original" cover to compare against, subtract the coefficient
   histograms directly.

## Signal cheat sheet

| Signal pattern | Diagnosis |
|----------------|-----------|
| stegdetect reports "F5" + JPEG carrier | Real F5 candidate — run `stegg_f5_decode` with candidate passwords |
| stegdetect reports "F5" + PNG carrier | False positive; ignore ([[sig-f5-hit-on-png]]) |
| Chi-square LOUD + JPEG | Probably jsteg, not F5 |
| Chi-square quiet + Aletheia probability > 0.7 + JPEG | Likely F5 or an F5-family scheme (nsF5, HUGO, etc.) |
| DCT histogram has visible dip at ±1 vs paired clean cover | F5 signature confirmed |
| JPEG came through Slack / WhatsApp / Instagram | Likely destroyed — F5 doesn't survive re-encode ([[sv-f5-slack-upload]], [[myth-jpeg-steg-survives-recode]]) |

## When stegdetect flags F5 but decode returns nothing

The tool detected the shrinkage pattern but doesn't have the password.
Report `*INCONCLUSIVE*` with:

> stegdetect / Aletheia flagged F5-shrinkage signature on this JPEG.
> Coefficient histogram shows +NN excess zeros vs baseline. Payload
> present; password required to decode. Try `stegg_f5_decode
> password=<candidate>` with the challenge's stated password, or brute
> force from a wordlist if the challenge implies one.

Do NOT declare `*FOUND*` on signature alone.

## Sources

- [[westfeld-2001-f5]]
- [[det-f5-signature]]
- [[tool-aletheia]]
- [[tool-stegdetect]]
