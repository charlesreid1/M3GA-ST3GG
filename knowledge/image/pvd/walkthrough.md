# PVD — end-to-end walkthrough

2 KB into a 1920×1080 PNG cover using `direction='horizontal'`,
`range_type='wu-tsai'`. Encode, decode, verify.

## Setup

```python
from PIL import Image
from stegg import img_core

payload = (b"PVD hides in adjacent-pixel diffs. Wu-Tsai 2003. " * 42)  # 2058 bytes
cover = Image.open("cover.png").convert("RGB")   # 1920x1080
```

## Pre-flight capacity

```python
cap_bytes = img_core.pvd_capacity_bytes(
    cover,
    direction="horizontal",
    range_type="wu-tsai",
)
# Blue-sky cover: ~350 KB
# Busy urban cover: ~600 KB
```

Comfortable for 2 KB. If it wasn't, try `range_type="wide"` to unlock
more bits per high-diff bucket, or `direction="vertical"` for a
different pair walk.

## Encode

```python
stego = img_core.pvd_encode(
    cover,
    payload,
    direction="horizontal",
    range_type="wu-tsai",
)
stego.save("stego.png")
```

What happens per pair-channel (~1.5M pair-channels for this cover):

1. Read `diff = p1[c] - p2[c]`.
2. Bucket lookup: `find_pvd_range(diff)`.
3. Read next `r.bits` payload bits (3 for smooth areas, up to 7
   for edges).
4. Compute new diff = `r.lower + embed_value` (same sign as
   original).
5. Distribute delta between the pair via ceil/floor halves.
6. Clamp both pixels to `[0, 255]` preserving the diff.
7. Write back.

Payload fits in the first ~5K pair-channels; the rest of the image
passes through untouched.

## Decode

```python
recovered = img_core.pvd_decode(
    Image.open("stego.png"),
    direction="horizontal",
    range_type="wu-tsai",
    max_payload=1_000_000,
)
assert recovered == payload
```

Decoder walks the same pair sequence, extracts `diff - r.lower` as
the bit chunk from each pair-channel, packs to bytes, reads the
first 4 bytes as length, returns exactly `len(payload)` bytes.

## Verify pair-channels touched

```python
import numpy as np
c_before = np.array(Image.open("cover.png").convert("RGB"), dtype=int)
c_after  = np.array(Image.open("stego.png"),                 dtype=int)
diff_mask = (c_before != c_after).any(axis=-1)
print("changed pixels:", diff_mask.sum())
# ~5K-10K changed pixels for a 2KB payload on a mid-complexity cover
```

Compared to raw LSB (which touches ~50% of all pixels for a 2KB
payload), PVD's footprint is 10-100× smaller AND concentrated at
edges — a huge stealth win against RS/SPA/chi-square on the LSB
plane.

## Test JPEG re-encode survival

```python
stego.save("stego.jpg", quality=75)
try:
    recovered_after = img_core.pvd_decode(Image.open("stego.jpg"), ...)
except ValueError:
    print("Payload died — expected. PVD is a pixel-domain technique.")
```

PVD dies to JPEG (and all lossy re-encodes) — see
[[myth-pvd-survives-jpeg]]. The pair-difference structure is
disrupted by re-quantization.

## Test byte-identical round trip

```python
# Serve via Slack upload, HTTP raw, GitHub — all preserve PNG IDAT
# byte-identical, so pvd_decode after the round trip returns payload
# unchanged.
```

## What would go wrong

| Change | Effect |
|--------|--------|
| Wrong `direction` at decode | Different pair sequence → payload garbled |
| Wrong `range_type` at decode | Different bucket boundaries → payload garbled |
| Image cropped or resized | Pair alignment destroyed → decode fails |
| JPEG re-encode | Pair differences lost → decode fails (see [[myth-pvd-survives-jpeg]]) |
| Blur / smoothing filter | High-diff pixels regressed → decode partially fails |
| Small payload + smooth cover | Fits comfortably in bucket-0 pairs; decode succeeds |
| Large payload + smooth cover | May exceed capacity; encode raises `ValueError` |

## The edge-adaptive stealth argument

PVD deliberately embeds MORE data in high-difference regions
(edges, texture) and LESS in low-difference regions (smooth areas).
The perceptual justification: human vision is less sensitive to
pixel modifications near edges than in smooth gradients. RS/SPA
statistical detectors have a harder time distinguishing PVD from
noise because the modifications concentrate where noise is naturally
higher.

The trade: PVD requires a range table AND a direction AND (ideally)
knowledge of whether the cover is edge-heavy or smooth to pick the
right bucket count.

## Sources

- [[image-pvd]]
- [[cap-image-pvd]]
- [[myth-pvd-survives-jpeg]]
