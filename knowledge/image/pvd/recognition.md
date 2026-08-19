# PVD — 15-second triage

"Is this image a PVD hide?"

## The pair-difference histogram tell

**Compare the pair-difference histogram of the suspect image to a
same-content clean cover** (if available), or to the expected
distribution for a natural photo.

Clean natural photos have a pair-difference distribution that's a
long-tailed exponential-ish curve centered near 0 (most adjacent
pixels are similar). PVD stego shows range-boundary anomalies:

- **Bucket-boundary clustering**: `wu-tsai` buckets end at 7, 15, 31,
  63, 127, 255. PVD stego shows small-but-detectable clumping at
  the low boundary of each bucket (because `new_diff = r.lower +
  embed_value`, and `embed_value` starts at 0).
- **Rare-value gaps**: some diff values that clean images produce
  naturally get "filled in" by PVD's remapping.

Not obvious to the eye without a reference cover; obvious to a
targeted PVD detector.

## Signal cheat sheet

| Signal pattern | Diagnosis |
|----------------|-----------|
| Chi-square LOUD on LSBs | Probably LSB, not PVD — PVD touches pair diffs, not LSB planes uniformly |
| RS/SPA fires WEAKER on this image than on a comparable LSB-embedded one | Consistent with PVD (edge-concentrated modifications) |
| Pair-difference histogram has small spikes at bucket boundaries | PVD-family signature |
| Image was JPEG-recompressed | Not PVD anymore — pair differences destroyed ([[myth-pvd-survives-jpeg]]) |
| PNG byte-identical from a byte-identical transport | PVD is a viable hypothesis |

## Practical detection flow

1. **File-type check** — PVD is a pixel-domain technique; only PNG-
   family carriers with byte-identical transport preserve it.
2. **Try `img_core.pvd_decode`** with `direction="horizontal"` and
   `range_type="wu-tsai"` (defaults). If it returns bytes, extract
   complete.
3. **If that fails**, try `direction="vertical"`, then
   `range_type="wide"` and `range_type="narrow"`. That's 6
   combinations; brute-force is cheap.
4. **If all six fail**, PVD isn't the technique — pivot to LSB
   (`stegg_lsb_smart_scan`) or DCT (`img_core.dct_decode`).

## Comparison to LSB (statistical stealth)

At an equal payload-size budget:

- **Raw LSB** touches ~50% of pixels for a "full-capacity" hide.
  RS/SPA fire.
- **PVD** touches ~5-10% of pixels, concentrated at edges. RS/SPA
  fire weaker; targeted PVD histogram attack is what actually
  catches it.

Statistical stealth ranking on a natural cover:

1. F5 matrix encoding (quietest — see [[image/f5]])
2. PVD
3. Raw LSB (loudest — see [[image/lsb]])

## When decode succeeds

Confident PVD hit: report `*FOUND*` with the recovered bytes, the
`direction` + `range_type` combination that worked, and (if the
challenge cover is available) the pair-difference histogram
comparison as evidence.

## Sources

- [[image-pvd]]
- [[anderson-petitcolas-1998-survey]]
- [[myth-pvd-survives-jpeg]]
- [[st3gg-field-guide]] — ST3GG-specific triage
