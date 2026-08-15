# DCT — 15-second triage

"Is this image a DCT hide?"

## The two-second discriminator

**Magic bytes `DCTS`** in the coefficient-decoded bit stream at any
of the three strengths (10, 25, 50). Auto-detect runs all three;
first strength whose decode produces `DCTS` + a self-consistent
strength byte wins.

If your triage tool can call `img_core.dct_decode` on the file,
that IS the discriminator. Positive decode = confirmed DCT hide.

## Signal cheat sheet

| Signal | Diagnosis |
|--------|-----------|
| Chi-square LOUD on pixel LSBs | Probably LSB, not DCT — DCT modifies mid-frequency, LSBs are collateral |
| Coefficient histogram at position (0,1) has spikes at ~6.25 & ~18.75 units | Consistent with `robustness=medium` (strength 25) DCT embed |
| Coefficient histogram shows spikes at ~2.5 & ~7.5 | `robustness=low` (strength 10) |
| Coefficient histogram shows spikes at ~12.5 & ~37.5 | `robustness=high` (strength 50) |
| Visible banding on smooth areas + PNG carrier | Probably `robustness=high` DCT |
| PNG that went through JPEG Q75 and back | If it decodes, `robustness=medium` or `high` |
| PNG that died to any JPEG recode | Was `robustness=low`, or wasn't DCT at all |

## When decode returns nothing

Two cases:

1. **Not a DCT hide** — check LSB (`stegg_lsb_smart_scan`),
   check PNG chunks (`stegg_read_png_chunks`), check trailing
   bytes (`stegg_detect_trailing`).
2. **DCT hide with wrong assumptions** — was `block_size` non-
   default (32 instead of 8)? Was the image cropped or resized
   after encode? Both destroy the block grid.

## The block-alignment tell

A DCT hide requires 8-pixel aligned blocks from the top-left. If
the image dimensions aren't multiples of 8, the last row/column of
"blocks" is dropped — an attacker who cropped the image by 1-7
pixels destroys the hide without changing the visible content.

Recognition tell: image dimensions `1920×1080` (both /8) is a good
DCT target; `1919×1079` implies deliberate anti-DCT cropping.

## Comparison to F5

Both DCT-domain. Different beasts:

- **DCT (ST3GG)** — spatial-domain PNG, quantizes one coefficient
  per 8×8 block. One bit per block. Interop with browser Text Lab.
- **F5** — JPEG-domain, matrix encoding over all non-zero AC
  coefficients. Multi-bits-per-block via matrix encoding. Requires
  jpeglib.

If the file is a JPEG, F5-signature scan is a better first
detector than the ST3GG DCT header check.

## Practical detection flow

1. **File-type check** — PNG? JPEG? DCT-in-PNG is the ST3GG
   case; DCT-in-JPEG is more likely F5, jsteg, or OutGuess.
2. **Run `img_core.dct_decode(image)`** on the raw file. If it
   returns bytes, extract complete.
3. **If it fails**, run a coefficient histogram at position (0,1)
   for each 8×8 block. Look for the double-spike pattern.
4. **If still nothing**, DCT isn't the technique — pivot to LSB,
   chunks, or trailing.

## Sources

- [[image-dct]]
- [[sv-dct-slack-upload]] — the ⚠ tuned-only Slack survival cell
- [[st3gg-field-guide]] — ST3GG-specific triage
