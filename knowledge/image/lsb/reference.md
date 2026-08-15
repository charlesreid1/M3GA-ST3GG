# Image LSB reference

Numeric spec for the ST3GG v3 LSB pipeline. Every quantity is either a
capacity number, a framing byte, or a strategy definition.

## Capacity

```
capacity_bytes = floor(W * H * len(channels) * bits_per_channel / 8) - header_overhead
```

- `W`, `H` — image width, height in pixels
- `len(channels)` — 1 (R, G, B, or A) through 4 (RGBA)
- `bits_per_channel` — 1 through 8; higher bits reduce stealth
- `header_overhead` — 48 bytes for the ST3GG v3 envelope, plus 4 bytes
  length prefix, plus 16 bytes AES-GCM tag if encrypted

Worked example: 1920×1080 RGB @ 1 bpc → `1920 * 1080 * 3 * 1 / 8 = 777,600`
raw payload bits worth of space, minus the ~50 bytes of header. See
[[cap-image-lsb]].

## Header — ST3GG v3

```
[ magic 32B ] [ length 4B LE ] [ flags 1B ] [ payload ... ] [ AES-GCM tag 16B if encrypted ]
```

- **magic** — HMAC-SHA256 of `"ST3GG-MAGIC-V3"` keyed on the (optional)
  password. Absent password → known-constant magic.
- **length** — 32-bit little-endian; payload size in bytes, post-compression.
- **flags** — 1 = compressed (deflate), 2 = encrypted (AES-256-GCM), 3 = both.
- **payload** — the actual bytes.
- **tag** — 16-byte AES-GCM authentication tag (present only if encrypted).

See [[st3gg-v3-header]] for the authoritative spec.

## Channel selectors

| Selector | Bits/pixel @ 1 bpc |
|----------|---------------------|
| R, G, B, A | 1 |
| RG, RB, GB | 2 |
| RGB       | 3 |
| RGBA      | 4 |

## Traversal strategies

| Strategy | Order | Best for |
|----------|-------|----------|
| `sequential` | linear index 0..N | max capacity, easiest to detect (leaves a top-of-image gradient — see [[sig-decreasing-rgb]]) |
| `interleaved` | round-robin across channels of each pixel | balanced statistical footprint ([[sig-equal-rgb]]) |
| `spread` | fixed stride | disperses statistical hits |
| `randomized` | seeded PRNG permutation | strongest stealth; requires seed for decode |

## Stealth vs capacity table (1920×1080 RGB carrier)

| bpc | Capacity  | RS/SPA rate | Visible?          |
|-----|-----------|-------------|-------------------|
| 1   | 777 KB    | ~1-5%       | Never             |
| 2   | 1.55 MB   | ~10-20%     | Under scrutiny    |
| 4   | 3.11 MB   | ~35-50%     | Faint banding     |
| 8   | 6.22 MB   | 50% max     | Full replacement  |

## Sources

- [[st3gg-v3-header]]
- [[westfeld-pfitzmann-1999-chi2]]
- [[fridrich-2001-rs]]
- [[cap-image-lsb]]
