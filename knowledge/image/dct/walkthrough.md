# DCT — end-to-end walkthrough

500 bytes into a 1920×1080 PNG at `robustness="medium"`. Encode,
recompress through JPEG Q75, verify survival.

## Setup

```python
from PIL import Image
from stegg import img_core

payload = b"DCT stego: mid-freq embed at position (0,1). " * 11  # ~495 bytes
cover = Image.open("cover.png").convert("RGBA")   # 1920x1080
```

## Pre-flight capacity

```python
cap = img_core.dct_capacity(cover)
# {'dimensions': (1920, 1080), 'block_size': 8, 'blocks': (240, 135),
#  'capacity_bits': 32400, 'header_bytes': 9, 'usable_bytes': 4041,
#  'human': '3.9 KB'}
```

Comfortable — 500 bytes needs 4000 bits + 72 header bits = 4072 bits,
we have 32400.

## Encode

```python
stego = img_core.dct_encode(
    cover,
    payload,
    robustness="medium",     # strength = 25
    output_path="stego.png",
)
```

What happens per block (240 × 135 = 32400 blocks total):

1. Compute the 2D DCT-II of the luminance block.
2. Read `coeff = dct_block[0, 1]`.
3. Quantize: `q = floor(coeff / 25)`.
4. Take next payload bit → write `(q + 0.75)*25` (bit=1) or
   `(q + 0.25)*25` (bit=0).
5. IDCT back, rescale RGB channels by the per-pixel luminance
   ratio.

Bits consumed: 4072 (header 72 + payload 4000). Remaining 28328
blocks pass through untouched (they carry noise-level DCT
coefficients, not payload).

## Verify by decode

```python
recovered = img_core.dct_decode(Image.open("stego.png"))
assert recovered == payload
```

Decoder auto-detects strength (tries 10, 25, 50), finds the `DCTS`
magic, reads the length prefix, returns exactly `len(payload)`
bytes.

## Test JPEG re-encode survival

The whole reason to use DCT over LSB — does the payload survive
JPEG recompression?

```python
stego.save("stego.jpg", quality=75)              # go through JPEG Q75
recovered_after = img_core.dct_decode(Image.open("stego.jpg"))
```

At `robustness="medium"` (strength=25) through JPEG Q75:

- **`medium` payload usually survives** if the destination Q table
  closely matches the source. This is the tuned-only ⚠ case in
  [[sv-dct-slack-upload]].
- **`low` payload usually dies** — the 10-step quantization is
  finer than JPEG's own DCT quantization at Q75.
- **`high` payload usually survives** — 50-step quantization is
  coarser than most JPEG recodes.

Empirical: `medium` on Slack upload survives ~50-70% of the time
depending on cover; per-cover pre-flight recommended.

## What would go wrong

| Change | Effect |
|--------|--------|
| Wrong `robustness` at decode | Auto-detect walks all three; usually recovers |
| Missing / truncated payload | Header length prefix mismatches → `ValueError("no DCT steganography header found")` |
| Cover recompressed at very low quality (Q<40) | Coefficient quantization strong enough to destroy the ±0.5 quant offsets → decode fails |
| Cover cropped or resized | Block alignment destroyed → decode fails |
| Chroma-only re-encode (HEIC) | Luminance may survive; test per codec |

## The tuned-robustness = medium argument

`medium` (strength 25) is the sweet spot for Slack and most
consumer messengers:

- `low` (10) is quieter but dies to Slack's JPEG recode.
- `high` (50) survives everything but banding is visible on
  smooth areas of the cover.
- `medium` (25) survives Slack often enough that ST3GG's
  "tuned only" ⚠ cell corresponds to picking `medium` with a
  cover pre-flight test.

## Read the artifact as detection

The strength-25 quantization creates small periodic patterns in
each 8×8 block's mid-frequency band. Under a coefficient histogram,
DCT-encoded images show:

- Small "spikes" at quantized offsets (0.25 × 25 = 6.25 and
  0.75 × 25 = 18.75 above each quantum boundary).
- Slight energy shift from DC to (0,1) that a per-block DCT sweep
  can pick up.

See [[image/dct/recognition]].

## Sources

- [[image-dct]]
- [[cap-image-dct]]
- [[sv-dct-slack-upload]]
