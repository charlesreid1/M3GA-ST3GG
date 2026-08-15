# Image LSB — 15-second triage

"Is this PNG hiding LSB payload?" — from the first `stegg_triage` output.

## Read the top of the triage report

```
carrier: PNG (RGB, 1920x1080)
chi_square: {R: 0.02, G: 0.03, B: 0.87}       ← blue is loud
rs_analysis: {R: 0.01, G: 0.01, B: 0.14}      ← consistent
sample_pairs: {R: 0.02, G: 0.02, B: 0.15}     ← consistent
bit_plane_entropy: {B[0]: 7.98, B[1]: 4.2}    ← LSB flat-noise, plane above normal
```

## Signal → verdict cheat sheet

| Signal pattern | Diagnosis | Reference |
|----------------|-----------|-----------|
| R > G > B in chi/RS/SPA | Sequential LSB embed starting at top; probably 1 bpc RGB | [[sig-decreasing-rgb]] |
| R ≈ G ≈ B, all elevated | Interleaved or spread traversal | [[sig-equal-rgb]] |
| One channel (usually B) loud, others quiet | Single-channel embed (blue is the ST3GG default) | (this file) |
| bit_0 AND bit_1 both loud | 2 bpc embed | [[sig-multiple-bit-planes]] |
| bit_0 low entropy (~2-4) | Uncompressed ASCII payload | [[sig-low-plane-entropy-ascii]] |
| bit_0 high entropy (~7.9-8.0) | Encrypted / compressed payload | [[sig-high-plane-entropy-encrypted]] |
| Alpha low bit all 1s | NOT payload; opaque source | [[sig-alpha-all-ones]], [[myth-lsb-alpha-payload]] |
| SPA loud, RS quiet | LSB matching or non-naive traversal | [[sig-spa-rs-mismatch]] |
| Chi loud, RS quiet, no plane pattern | False positive on a smooth carrier | (advisory only) |

## Next step by diagnosis

- **Sequential**: `stegg_decode_manual channels='R' bits_per_channel=1 strategy='sequential'`
- **Interleaved**: `stegg_decode_manual channels='RGB' bits_per_channel=1 strategy='interleaved'`
- **Single-channel blue**: `stegg_decode_manual channels='B' bits_per_channel=1 strategy='randomized'` (try seeds 0, 1, 42, and any obvious number from the challenge)
- **2 bpc**: same as above with `bits_per_channel=2`
- **No ST3GG header** (extractor bounces despite screaming signals):
  raw-bit dump per the [[sig-decreasing-rgb]] / [[sig-equal-rgb]] Python
  snippets. The decoder needs a magic header; a signals-diagnosed
  technique + raw dump is a real `*INCONCLUSIVE*` answer with a
  next-step recipe.

## Common false positives

- **Smooth flat backgrounds** (screenshots, UI shots): chi-square false-fires.
  Corroborate with RS/SPA before declaring a hit.
- **Photographic noise** in uniform regions: bit-plane entropy runs
  near-maximum on natural photos too. Compare against the plane ABOVE
  the suspect — if bit_1 also looks like noise, the whole channel is
  natural noise, not payload.
- **F5 detector hit on a PNG**: [[sig-f5-hit-on-png]] — F5 is a JPEG
  scheme; a hit on a PNG is almost always a byte-scanner false positive.

## When the signals point at LSB but extraction fails

Report `*INCONCLUSIVE*` with the specific technique + recipe:

> Signals scream LSB, blue channel, 1 bpc, sequential-from-top
> (chi=0.87 on B, entropy=2.3 on B[0], banding visible in top third of
> image). The ST3GG-header extractors bounced — payload wasn't hidden
> with vanilla ST3GG. A raw-bit dump of B sequential 1bpc would finish
> the job. I don't have that as a tool. Recipe:
> ```python
> from PIL import Image
> raw = Image.open('in.png').convert('RGB').tobytes()
> bits = [(raw[i+2] >> 0) & 1 for i in range(0, len(raw), 3)]
> print(bytes(int(''.join(map(str, bits[i:i+8])), 2) for i in range(0, len(bits)-7, 8))[:256])
> ```

Honest gap-report; don't manufacture a fake decode.

## Sources

- [[st3gg-field-guide]]
- All `sig-*` records in `signatures.json`
