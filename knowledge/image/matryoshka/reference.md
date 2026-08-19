# Matryoshka — reference

Exact numeric spec of ST3GG's `matryoshka_core.encode_nested /
decode_nested`.

## Config defaults (`MatryoshkaConfig`)

| Field                 | Default | Meaning                                       |
|-----------------------|---------|-----------------------------------------------|
| `channels`            | `"RGBA"`| Channel preset (any of R/G/B/A/RG/RB/GB/RGB/RGBA) |
| `bits`                | `2`     | Bits per channel (1-8)                        |
| `password`            | `None`  | Encrypts innermost payload only               |
| `max_depth`           | `11`    | Recursion cap (also the decode termination)   |
| `per_layer_encrypt`   | `False` | If True, encrypt at every layer (not just innermost) |
| `smart_scan_hook`     | `None`  | Optional decode fallback when STEG header not found |

Every layer is a full `img_core.encode / decode` invocation with the
same config. There is no matryoshka-specific header; each layer is
independently a valid ST3GG-v3 hide.

## Header per layer

Each layer uses [[crypto/st3gg-v3-header]] (via `img_core.encode`):

```
+---------+-------+-----+---------+---------+---------+
| MAGIC   | FLAGS | LEN | [NONCE] | PAYLOAD | [TAG]   |
| 8 B     | 1 B   | 2 B | 12 B    | LEN B   | 16 B    |
+---------+-------+-----+---------+---------+---------+
```

Magic is `HMAC-SHA256(password, "st3gg-v3-magic")[:8]`. A scanner
without the password sees random bytes at every layer; the recursion
tree is invisible without a valid password.

## Capacity per layer

```
raw_capacity_bits = W * H * len(channels) * bits
usable_bytes      = max(0, raw_capacity_bits // 8 - HEADER_SIZE)
```

`HEADER_SIZE` from `img_core` is 32 bytes (v3 header worst case;
`crypto.encrypt` overhead is included in payload bytes).

Examples at default `RGBA / 2 bpc`:

| Layer image size | Raw capacity   | Usable bytes    |
|------------------|----------------|-----------------|
| 4096 × 2160      | ~8.85 MB       | ~8.85 MB        |
| 1920 × 1080      | ~2.07 MB       | ~2.07 MB        |
| 1024 × 1024      | ~1.05 MB       | ~1.05 MB        |
| 512 × 512        | 268 KB         | 268 KB          |
| 256 × 256        | 67 KB          | 67 KB           |
| 128 × 128        | 16.7 KB        | 16.7 KB         |
| 64 × 64          | 4.1 KB         | 4.1 KB          |
| 32 × 32          | ~1 KB          | ~1 KB           |
| 16 × 16          | 256 B          | 224 B           |

The innermost payload lives in the smallest image. Working
outward, each carrier holds the PNG-serialization of the encoded
image from the layer below. PNG serialization is roughly 1-2 bytes
per pixel for smooth images, so a 512×512 inner PNG is ~50-200 KB
serialized — fitting comfortably in a 1024×1024 carrier.

## Encode step (per layer i)

Layer numbering: layer 1 is INNERMOST, layer N is OUTERMOST.

For each layer `i` in `[1..N]`:

1. Capacity check: `data_size <= capacity_for(carrier_i)`.
2. Encrypt (layer 1 only, or every layer if `per_layer_encrypt`):
   `data = crypto.encrypt(current_data, password)` — AES-GCM inside
   the v3 header.
3. Embed: `encoded_img_i = img_core.encode(carrier_i, data, steg_cfg)`.
4. If not final layer: serialize `encoded_img_i` to PNG bytes; those
   become `current_data` for layer `i+1`.
5. If final: `encoded_img_N` is the shipped artifact.

## Decode step

`decode_nested(outermost_image)` is a while-loop:

1. Try `img_core.decode(current_image, password)` → data bytes.
2. If data starts with an image magic (PNG, JPEG, GIF, BMP —
   `is_image_data()`): decode as an image, recurse with the inner
   image.
3. Else: extract payload (checking for the
   `<len><name><body>` file-wrap convention via
   `extract_file_from_data`) and return.
4. Recursion cap: `max_depth` layers deep.

## The password vs magic invariant

Because magic is HMAC-derived from password:

- **Correct password every layer**: recursion succeeds.
- **Wrong password at layer N**: HMAC mismatch → `img_core.decode`
  fails → `decode_nested` returns partial result up to layer N-1.
- **Different passwords per layer**: not supported by the primary
  config (single `password` field). Would require calling
  `decode_nested` once per layer with a different config each time.

## Depth cap

`max_depth=11` is both the SPECTER-tested depth and a hard cap. To
go deeper, raise `MatryoshkaConfig.max_depth` — no code change
needed, just a runtime check.

## Sources

- [[image-matryoshka]] — the technique record
- [[st3gg-v3-header]] — the per-layer wrapping format
- [[crypto/aes-gcm-before-embed]] — the innermost-encryption story
