# Matryoshka — end-to-end walkthrough

A depth-4 matryoshka: hide a 100-byte payload in a 128×128 → 256×256
→ 512×512 → 1024×1024 stack. Encode, decode, verify.

## Setup

```python
from PIL import Image
from stegg import matryoshka_core

payload = b"Layer 1 payload — innermost, AES-GCM-wrapped. " * 2  # 92 bytes

# Innermost first (layer 1) → outermost last (layer 4).
carriers = [
    (Image.open("cover_inner_128.png").convert("RGBA"),   "inner.png"),
    (Image.open("cover_mid1_256.png").convert("RGBA"),    "mid1.png"),
    (Image.open("cover_mid2_512.png").convert("RGBA"),    "mid2.png"),
    (Image.open("cover_outer_1024.png").convert("RGBA"),  "outer.png"),
]

config = matryoshka_core.MatryoshkaConfig(
    channels="RGBA",
    bits=2,
    password="matryoshka-demo",
    max_depth=11,
)
```

## Pre-flight capacity walkthrough

```python
_, reports = matryoshka_core.encode_nested(
    payload, carriers, config=config, dry_run=True,
)
for r in reports:
    print(f"Layer {r.layer} ({r.carrier_name}): "
          f"payload {r.payload_size} B / capacity {r.capacity} B — "
          f"{'fits' if r.fits else 'OVERFLOW'}")
```

Sample output on random natural covers:

```
Layer 1 (inner.png)  : payload 92 B     / capacity 16644 B    — fits
Layer 2 (mid1.png)   : payload 17000 B  / capacity 66628 B    — fits
Layer 3 (mid2.png)   : payload 68000 B  / capacity 266308 B   — fits
Layer 4 (outer.png)  : payload 270000 B / capacity 1064996 B  — fits
```

Payload roughly doubles each layer (a serialized encoded PNG is
larger than the pre-encode payload). Capacity roughly quadruples
per layer (2× dimensions each direction). Comfortable.

## Encode

```python
final, reports = matryoshka_core.encode_nested(
    payload, carriers, config=config,
)
final.save("stego_outer.png", format="PNG")
```

What happens per layer:

1. **Layer 1 (inner)**: `data = crypto.encrypt(payload, password)`
   (AES-GCM in v3 header). Embed via `img_core.encode` into the
   128×128 carrier. Serialize the encoded PNG.
2. **Layer 2**: `current_data` is now the ~17 KB PNG from layer 1.
   Embed into the 256×256 carrier at 2 bpc RGBA. Serialize.
3. **Layer 3**: `current_data` is the ~68 KB PNG from layer 2. Embed
   into 512×512. Serialize.
4. **Layer 4 (outer)**: `current_data` is the ~270 KB PNG from
   layer 3. Embed into 1024×1024. Do NOT serialize — return the
   PIL image and save as the final artifact.

Total ship size: whatever the 1024×1024 PNG serializes to (~800 KB -
1.5 MB depending on cover content).

## Decode

```python
layers = matryoshka_core.decode_nested(
    Image.open("stego_outer.png"),
    config=config,
)
for l in layers:
    print(f"Depth {l.depth}: type={l.type} preview={l.preview[:60]}")

# The final layer's payload:
final_payload = layers[-1].raw_data
assert final_payload == payload
```

What happens per layer:

1. `img_core.decode(outer_1024, password)` returns the serialized
   PNG bytes of layer 3.
2. Detect image magic → load the PNG → recurse.
3. `img_core.decode(512_from_layer3, password)` returns layer 2's
   serialized PNG.
4. ... and so on until layer 1.
5. Layer 1's decode returns the AES-GCM-encrypted payload; the
   v3-header layer of `img_core.decode` does the GCM verify + decrypt
   automatically.

Recursion cap: `max_depth=11`. If a legitimate payload byte happens
to start with a PNG magic byte, `is_image_data()` catches
false-positives with a fuller sniff.

## Verify with the SPECTER example

The repo's SPECTER example (see `examples/` in-tree if present, or
the field guide's SPECTER walkthrough) ships a depth-11 stack: a
4K image containing a 3K image containing a 2K image ... down to
a 1×1-pixel innermost image holding the flag. Every layer uses a
different password derived from the previous layer's payload.

The single-password case (this walkthrough) is the simplest;
per-layer-password chains are the SPECTER escalation.

## What would go wrong

| Change | Effect |
|--------|--------|
| Wrong password at any layer | HMAC mismatch → that layer's decode fails → recursion stops at depth-1 |
| Cover recompressed (any layer) | Outer LSB destroyed → outer decode fails → recursion never starts |
| PNG chunks stripped by transport | Doesn't matter — matryoshka uses IDAT LSB, not chunks |
| Outer cover cropped | LSB alignment destroyed → outer decode fails |
| Outer served through Slack upload | ✅ Survives — PNG IDAT byte-identical (see [[sv-matryoshka-slack-upload]]) |
| Any layer served through JPEG recode | ❌ All layers below that point are unreachable |
| Layer capacity insufficient | `encode_nested` raises `ValueError` up front — dry-run to catch |

## The security compound

At depth N with a single password:

- Attacker without password sees random bytes at the outermost layer.
- Chi-square / RS / SPA on the outermost image only tells them
  *something* is embedded. Depth is invisible.
- Even given a single wrong-password guess, no partial decode
  succeeds (GCM auth fails on the outer layer).

At depth N with per-layer passwords (SPECTER style):

- Each layer requires its own password.
- Layer N-1's payload can *contain* layer N's password (out-of-band
  hint chain).
- An attacker who compromises one password only unlocks one layer,
  not the whole stack.

## Sources

- [[image-matryoshka]]
- [[st3gg-v3-header]]
- [[sv-matryoshka-slack-upload]]
- [[crypto/aes-gcm-before-embed]]
