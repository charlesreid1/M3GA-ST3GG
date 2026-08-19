# F5 — end-to-end walkthrough

500 bytes into a Q75 1920×1080 JPEG at `k=3`. Measure shrinkage,
extract, verify.

## Setup

```python
from stegg import img_core
payload = b"F5, Westfeld 2001, IH conference." * 15   # ~495 bytes
```

## Pre-flight capacity

```python
cap = img_core.f5_capacity("cover.jpg", k=3)
# example output: {"nonzero_ac_coefs": 512_400, "capacity_bits": 219600, "capacity_bytes": 27450}
```

Comfortable — 500 bytes needs 4000 bits, we have room for 27 KB.

## Encode

```python
img_core.f5_encode(
    input_path="cover.jpg",
    output_path="stego.jpg",
    payload=payload,
    k=3,
    password="matrix-encoding-4",
)
```

What happens under the hood (from `f5_core`):

1. Load cover.jpg via a DCT-preserving JPEG reader.
2. Walk quantized AC coefficients in scan order.
3. For each block of 7 non-zero ACs:
   - Compute the weighted XOR-sum of LSBs → `S`.
   - Take next 3 payload bits → `m`.
   - Target `p = S XOR m`. If `p == 0`, block is done — no flip.
     Otherwise flip LSB of the p-th coefficient.
4. If a flip decremented a ±1 to 0: record shrinkage, re-embed at the
   next block.
5. Write out with the modified coefficients.

Typical run stats:

```
input_coefs: 512400 non-zero ACs
blocks_used: 1360   (500 * 8 / 3 = 1333 base, plus shrinkage)
shrinkage_events: 27  (~2% on this cover)
output_coefs: 512373  (27 coefficients decremented to zero)
```

## Verify with the histogram

```python
import numpy as np
from stegg.f5_core import extract_coef_histogram
h_in = extract_coef_histogram("cover.jpg")
h_out = extract_coef_histogram("stego.jpg")
# h_in[0] and h_out[0] differ by ~27 (the shrinkage events)
# h_in[±1] and h_out[±1] each drop by ~14 (half the shrinkage each)
```

This is the F5 shrinkage signature. See [[det-f5-signature]].

## Decode

```python
recovered = img_core.f5_decode(
    input_path="stego.jpg",
    k=3,
    password="matrix-encoding-4",
)
assert recovered == payload
```

Decoder walks the same coefficient sequence, computes each block's
weighted-XOR sum, and concatenates the k-bit values. Length prefix in
the ST3GG header says when to stop.

## What would go wrong

| Change | Effect |
|--------|--------|
| Wrong `password` | Magic mismatch → decode fails |
| Re-encode at Q=85 with different Q table | Coefficients re-quantize; the LSB pattern changes at unpredictable positions; extraction likely fails (see [[sv-f5-slack-upload]]) |
| Same-Q re-encode with same Q table | Payload usually survives; robustness case, not a guarantee |
| Chroma subsampling change | Every coefficient position renumbered; decode fails |

## Read the shrinkage as a detection signal

An analyst opens `stego.jpg` in a DCT-histogram viewer. The count at
magnitude 0 is `h_out[0] = h_in[0] + 27` — an unusual excess of zeros
that no clean natural image produces. That signature is exactly what
`stegdetect` and Aletheia key on. See [[image/f5/recognition]].

## Sources

- [[westfeld-2001-f5]]
- [[image-f5]]
- [[cap-image-f5]]
