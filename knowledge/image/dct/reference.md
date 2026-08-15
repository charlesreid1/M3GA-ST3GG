# DCT — reference

Exact numeric spec of ST3GG's `img_core.dct_encode / dct_decode`.
Interop-compatible with the browser Text Lab's DCT tool
(`index.html`).

## Wire format

```
+----------+----------+-------------------+---------------+
| MAGIC    | STRENGTH | LENGTH (BE u32)   | PAYLOAD BYTES |
| 4 bytes  | 1 byte   | 4 bytes           | length bytes  |
| "DCTS"   | 10/25/50 |                   |               |
+----------+----------+-------------------+---------------+
```

Header total = 9 bytes. Payload follows immediately. No trailer,
no CRC — the length prefix bounds the payload exactly.

## Robustness table

`robustness` is the parameter the user passes; internally it maps
to a quantization step used per block.

| Robustness | Quant step | Bit visibility  | Recompression survival             |
|-----------:|-----------:|-----------------|-------------------------------------|
| `low`      | 10         | Barely visible  | Fragile — dies to most JPEG recodes |
| `medium`   | 25         | Faint textures  | Survives moderate Q-preserving recode |
| `high`     | 50         | Visible banding | Robust across common social-media recodes |

Trade the bit-visibility for round-trip robustness. `medium` is the
default; `high` is what the DCT tuned-only Slack cell corresponds to
in [[sv-dct-slack-upload]].

## Embedding position

Position `(cy, cx) = (0, 1)` in the 8×8 DCT of luminance. First
horizontal-frequency AC coefficient — perceptually low-impact,
recompression-tolerant. Matches `DCT_EMBED_POSITIONS[0]` in the JS
DCT tool for browser round-trip compatibility.

## Capacity formula

```
capacity_bits = floor(W / block_size) * floor(H / block_size)
usable_bytes  = max(0, capacity_bits // 8 - 9)     # 9 = header bytes
```

Where `block_size = 8` is the default (fixed to match browser tool).

Examples at `block_size=8`:

| Cover dimensions | Bits available | Header | Usable bytes |
|------------------|----------------|--------|--------------|
| 512 × 512        | 4096           | 72 b   | 503          |
| 1920 × 1080      | 32400          | 72 b   | 4041         |
| 3840 × 2160      | 129600         | 72 b   | 16191        |

Each 8×8 block carries exactly ONE bit — regardless of robustness
setting. The robustness controls how big a coefficient perturbation
each bit costs, not how much fits.

## Encode pseudo-code

For each 8×8 block of the RGBA-cover's luminance (Rec.601, matching
JS coefficients 0.299/0.587/0.114):

1. Compute the block's 2D DCT-II. Orthonormal basis; DC coefficient
   at (0,0) scaled by 1/√n.
2. Read `coeff = dct_block[0, 1]`.
3. Quantize `q = floor(coeff / strength)`.
4. Read next payload bit `b`.
5. Write back `dct_block[0, 1] = (q + (0.75 if b else 0.25)) * strength`.
6. IDCT back to spatial, clip to `[0, 255]`.
7. Rescale RGB channels by the per-pixel luminance ratio (new / old),
   round to `uint8`.

## Decode

Auto-detects strength (tries 10/25/50 in order), searching for the
`DCTS` magic byte pattern in the recovered bit stream. When the
magic matches AND the strength byte matches the strength attempted,
extraction proceeds; length prefix bounds output.

## Header header vs ST3GG v3 header

`DCTS` header is **NOT** the ST3GG v3 header. DCT stego uses its
own 9-byte header; the v3 header (magic + flags + LEN + optional
AES) is only used by LSB / matryoshka. No password protection
here — DCT is a pure hide, no crypto layer.

Wrapping: encrypt separately with `crypto.encrypt_gcm(...)` before
passing to `dct_encode` if payload confidentiality matters.

## Sources

- [[image-dct]] — the technique record
- [[cap-image-dct]] — capacity formula record
- [[itu-t81-jpeg]] — reference for DCT coefficient conventions
- [[st3gg-field-guide]] — ST3GG-specific integration
