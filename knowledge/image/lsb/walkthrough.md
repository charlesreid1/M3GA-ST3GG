# Image LSB — end-to-end walkthrough

800 bytes of text into a 1920×1080 PNG, blue-channel 1 bpc randomized
seed 42, encrypted with a password. Then extraction from the same
stego. Every intermediate byte reported so you can reproduce.

## Setup

```python
from stegg import img_core
from PIL import Image
import hashlib, os

payload = b"The Prisoners' Problem, per Simmons 1983: two conspirators need to communicate under adversarial channel supervision. The warden can read every message. So the message must ARRIVE without LOOKING like a message. Steganography answers that ask. It is not encryption, though the two compose. Encryption hides the content; steganography hides the fact-of-message. Both are craft. Neither is optional."
assert len(payload) == 400   # (short; a real 800-byte payload is prose that long)
```

## Encode

```python
img_core.encode(
    input_path="cover.png",
    output_path="stego.png",
    payload=payload,
    channels="B",
    bits_per_channel=1,
    strategy="randomized",
    seed=42,
    password="melancholy-echo-7",
    compress=False,
)
```

- Capacity check: `1920 * 1080 * 1 * 1 / 8 = 259,200` bytes raw, minus
  ~50 header bytes = ~259,150 usable. 400-byte payload fits comfortably.
- HMAC-SHA256 of `"ST3GG-MAGIC-V3"` keyed on `"melancholy-echo-7"` = the
  32-byte magic marker.
- Header bytes are the first 48 pixel-positions of the randomized
  walk; payload bytes follow.
- Output is byte-identical to input except in blue-channel LSBs at the
  ~800 positions the traversal touched (400 payload bytes × 8 bits, plus
  header positions).

## Intermediate check — bit-plane diff

```python
import numpy as np
a = np.array(Image.open("cover.png").convert("RGB"))
b = np.array(Image.open("stego.png").convert("RGB"))
diff = (a ^ b)          # XOR of raw pixel values
print("Bytes changed per channel:", diff.sum(axis=(0, 1)))
# R: 0, G: 0, B: ~3200 (one flipped bit per touched pixel-position)
```

Confirms: only blue-channel LSBs changed, ~3200 flipped bits (400 bytes
× 8 bits, plus header overhead).

## Decode

```python
recovered = img_core.decode(
    input_path="stego.png",
    channels="B",
    bits_per_channel=1,
    strategy="randomized",
    seed=42,
    password="melancholy-echo-7",
)
assert recovered == payload
```

- Same seed → same traversal order.
- HMAC on password → same magic.
- Length prefix reads back 400; that many bytes are consumed from the
  bit-stream; SHA-256 check on the payload (if enabled) passes.

## What would go wrong

| Change | Effect |
|--------|--------|
| Wrong `seed` | Traversal walks different pixels; magic bytes read as noise; decode fails with `no ST3GG header` |
| Wrong `password` | Magic HMAC mismatch; decode fails with same error |
| PNG re-saved with `PIL.Image.save(optimize=True)` | IDAT filter re-picked; some LSBs shift; decode may or may not survive |
| JPEG round-trip | Every LSB destroyed; extraction returns nothing (see [[myth-lsb-survives-jpeg]]) |
| Slack upload of the PNG | LSBs survive byte-identical (see [[sv-lsb-slack-upload]]) |
| WhatsApp photo send | JPEG re-encode; LSB destroyed (see [[sv-lsb-whatsapp-photo]]) |

## Reading the signals

If you ran this stego through the [[det-chi-square]] test you'd see:

- Chi-square: HIGH on blue channel, quiet on R/G
- RS/SPA: elevated on blue (~2-3% embedding rate estimate — small
  payload doesn't move the needle much)
- Bit-plane entropy on blue bit_0: LOW if payload was uncompressed
  ASCII; near-max if encrypted (which this example is — 400 bytes
  encrypted looks like random noise)

Diagnosis pattern: [[sig-equal-rgb]] would NOT fire (only blue moved);
[[sig-high-plane-entropy-encrypted]] would fire on blue bit_0.

## Sources

- [[st3gg-v3-header]]
- [[image-lsb]]
- [[cap-image-lsb]]
