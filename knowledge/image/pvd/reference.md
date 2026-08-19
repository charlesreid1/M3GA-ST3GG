# PVD — reference

Exact numeric spec of ST3GG's `img_core.pvd_encode / pvd_decode`.
Bit-identical to the browser Text Lab PVD tool (`index.html`) for
`wu-tsai`, `wide`, and `narrow` range tables.

## Wire format

```
+-------------------+---------------+
| LENGTH (BE u32)   | PAYLOAD BYTES |
| 4 bytes           | length bytes  |
+-------------------+---------------+
```

Header total = 4 bytes. No magic — recovery relies on the range
table + direction being known out-of-band. Any subsequent decode
consumer must know the range_type used at encode time (auto-detect
across the three tables is a plausible next step).

## Range tables

Adjacent-pixel differences bucketed by width. Each bucket sets how
many payload bits fit in that pair-position.

### `wu-tsai` (default, Wu & Tsai 2003)

| Bucket range | Width | Bits per pair-channel |
|--------------|-------|-----------------------|
| 0-7          | 8     | 3                     |
| 8-15         | 8     | 3                     |
| 16-31        | 16    | 4                     |
| 32-63        | 32    | 5                     |
| 64-127       | 64    | 6                     |
| 128-255      | 128   | 7                     |

### `wide` (coarser buckets → more bits at edges)

| Bucket range | Width | Bits per pair-channel |
|--------------|-------|-----------------------|
| 0-15         | 16    | 4                     |
| 16-47        | 32    | 5                     |
| 48-111       | 64    | 6                     |
| 112-255      | 144   | 7                     |

### `narrow` (finer buckets at low end)

| Bucket range | Width | Bits per pair-channel |
|--------------|-------|-----------------------|
| 0-3          | 4     | 2                     |
| 4-7          | 4     | 2                     |
| 8-15         | 8     | 3                     |
| 16-31        | 16    | 4                     |
| 32-63        | 32    | 5                     |
| 64-127       | 64    | 6                     |
| 128-255      | 128   | 7                     |

The trade: `wide` embeds more per pair (higher capacity) at the cost
of larger pixel perturbations in high-difference regions. `narrow`
minimizes low-end perturbation (better for smooth areas) at reduced
capacity.

## Directions

- `horizontal` (default) — walk pairs `(col, col+1)` in row-major.
  Each row contributes `⌊W/2⌋` pairs, `⌊H⌋` rows.
- `vertical` — walk pairs `(row, row+1)` in column-major.
- `both` — horizontal pass then vertical. **NOTE**: `both` has a
  known correctness issue — horizontal embed mutates pixels that
  the vertical pass then re-reads. `pvd_capacity_bits` reports
  `max(horizontal, vertical)`, not their sum. Kept only for
  cross-compatibility with existing JS artifacts; new hides should
  pick `horizontal` or `vertical`.

## Capacity formula

```
capacity_bits(image, direction, range_type) =
    sum over pair-channels of bits_per_bucket(|p1[c] - p2[c]|)
```

Where each pair `(idx1, idx2)` contributes 3 channel-bits (R, G, B),
and each channel-bit is `range.bits` for the bucket its diff falls
in.

Usable bytes: `max(0, capacity_bits // 8 - 4)` — subtract the 4-byte
length header.

Approximate capacity on a natural 1920×1080 image with `wu-tsai`
horizontal:

- Blue sky / smooth cover: mostly bucket 0-7 → ~3 bits/pair-channel.
  1920×1080 / 2 * 3 channels * 3 bits ≈ 3.1 M bits ≈ 385 KB.
- Busy urban cover: mix of buckets → up to ~5 bits/pair-channel.
  Same math ≈ 640 KB.

Real payloads use a small fraction of capacity; PVD's capacity
scales with cover *complexity*.

## Encode step

For each pair `(p1, p2)` and channel `c`:

1. `diff = p1[c] - p2[c]`
2. Look up bucket `r = find_pvd_range(diff)`.
3. Read next `r.bits` payload bits → `embed_value` (0..2^r.bits - 1).
4. Compute target `new_diff = r.lower + embed_value` (signed to
   match `diff`'s sign).
5. Split delta `= signed_new_diff - diff` between the two pixels via
   ceil/floor halves (ceil to `p1`, floor to `p2` for positive
   delta, mirrored for negative).
6. Clamp to `[0, 255]` while preserving the diff.
7. Write back.

## Decode step

Same walk. For each pair-channel:

1. `diff = |p1[c] - p2[c]|`
2. Look up bucket `r`.
3. `embed_value = diff - r.lower`.
4. Unpack `r.bits` bits from `embed_value`, append to bit stream.

Read first 32 bits as length, then that many bytes of payload.

## Sources

- [[image-pvd]] — the technique record
- Wu & Tsai 2003 — original PVD paper (referenced via
  [[anderson-petitcolas-1998-survey]])
- [[cap-image-pvd]] — capacity formula record
