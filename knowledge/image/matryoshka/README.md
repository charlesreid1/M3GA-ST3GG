# Matryoshka (SPECTER) recursive-nesting steganography

Payload in an image in an image in an image in an image. Each layer
is a full ST3GG-v3-headered LSB hide. Depth is bounded only by cover
capacity and the reader's patience. Depth-11 is tested in the
repo's SPECTER example.

## What the ST3GG implementation does

`matryoshka_core.encode_nested / decode_nested`. See
[[image-matryoshka]] and the walkthrough in `examples/specter/`.

## The recursion

At each depth `d`:

1. Take the payload from depth `d+1` (or the raw payload at the
   deepest level).
2. Embed it into cover image `d` via `img_core.encode` with a
   ST3GG-v3 header (magic + length + optional AES).
3. The output image `d` becomes the payload for depth `d-1`.

Each layer's magic bytes are password-derived, so a raw-bit scan at
one depth returns "no extraction" without knowing the password — a
payload-in-plain-sight defense in depth.

## Capacity budget

Every layer costs a header (roughly 16-64 bytes for magic + length)
and needs enough cover capacity to hold the inner image. Because the
inner image is itself a full carrier, the deeper layers are much
smaller than the outer layers — an outermost 4K PNG might carry a
1920×1080 image which carries a 512×512 image which carries a
128×128 image which carries the real payload.

Depth is bounded by:

- Outer cover capacity (fixed).
- Header overhead per layer (16-64 B).
- The innermost payload's minimum size to remain a valid PNG (about
  100 bytes for a 1×1 image).

Depth-11 in SPECTER: 11 nested images from 4K down to 8×8 pixels.

## Where it dies

- **Any lossy re-encode of the outermost image**: destroys the
  outermost LSB, which cascades. No layer survives.
- **Any transport that strips PNG chunks that the inner layers
  needed**: rare because each inner layer is a self-contained PNG.
- **Password mismatch on any layer**: the whole chain fails at that
  depth.

## Where it survives

- **Byte-identical PNG transports** (Slack upload
  [[sv-matryoshka-slack-upload]], HTTP raw, GitHub, email
  attachment). Depth-11 through Slack has been probed in the repo.

## The security argument

Password-derived magic per-layer means a scanner without the
password can't extract *any* layer. Even chi-square / RS / SPA on
the outermost image only tells you *something* is embedded; without
the password you can't drill deeper. It's steganography compounded
with cryptography compounded with steganography — a Russian doll of
plausible deniability.

## SPECTER example

`examples/specter/` walks through a depth-11 stack: an image of the
AND!XOR badge → image of a bender → image of a coffee cup → ... →
the final payload. Each stage is a real payload for the layer above.

## Detection

- Outer layer detection: normal LSB steganalysis on the outermost
  image (chi-square, RS, SPA).
- Cannot detect *depth* without the password — a shallow-hide and
  a depth-11 hide look identical at the outermost layer.

## Sources

- [[st3gg-v3-header]] — the per-layer header spec
- [[st3gg-field-guide]] — SPECTER walkthrough
