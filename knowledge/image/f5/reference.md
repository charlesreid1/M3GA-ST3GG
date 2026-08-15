# F5 — reference

Numeric spec + matrix-encoding math.

## The parameter k

`k` is the matrix-encoding rate. For a given `k`:

- Each block of `2^k - 1` non-zero AC coefficients hides `k` bits.
- At most one coefficient is flipped per block (best case: zero flips).
- Larger `k` → fewer changes per bit → less statistical disturbance,
  but also less capacity.

| k | Block size (coefs) | Bits per block | Capacity ratio | Avg flips per k bits |
|---|---------------------|-----------------|----------------|-----------------------|
| 1 | 1                   | 1               | 1.00           | 0.5                   |
| 2 | 3                   | 2               | 0.67           | 0.75                  |
| 3 | 7                   | 3               | 0.43           | 0.875                 |
| 4 | 15                  | 4               | 0.27           | 0.94                  |

Default `k=3` is the common Westfeld-implementation choice.

## Capacity formula

```
capacity_bits = |nonzero_AC_coefs| * k / (2^k - 1)
```

`|nonzero_AC_coefs|` is Q-table dependent. Q75 1920×1080 typical:
~500,000 non-zero ACs. At `k=3`: `500000 * 3/7 ≈ 214,000` bits ≈ 26 KB
before shrinkage.

Shrinkage overhead is typically 5-10% on natural covers (see
[[known-unknowns]] — this range is textbook, not first-party measured).

## The matrix encoding step

For a block of coefs `c_1, ..., c_(2^k - 1)`:

1. Extract LSBs: `s_i = LSB(c_i)`.
2. Compute check code: `S = s_1 ⊕ (2 * s_2) ⊕ ... ⊕ ((2^k - 1) * s_(2^k - 1))`
   (each `s_i` weighted by its index in a XOR-sum).
3. Take next `k` payload bits as `m`.
4. Target position: `p = S ⊕ m`.
5. If `p == 0`, no flip needed — the block already encodes `m`.
6. Else flip LSB of `c_p`.

Decode inverts: read LSBs, compute `S`, that's the k bits hidden in the
block.

## Shrinkage handling

Some coefficients are ±1. Flipping ±1's LSB decrements magnitude to 0.
Zero-magnitude coefs are outside F5's usable set (F5 hides only in
non-zero ACs). Consequence: the flip "shrinks" the coefficient out of
the usable pool. The block's encoded value is lost.

Recovery: after the shrinkage, re-embed the same k bits into the next
block. Adds an average of one extra block per shrinkage event.

Detection consequence: shrinkage produces a characteristic dip in the
histogram at magnitude 0 (an *excess* of zeros beyond what a clean JPEG
would have). This is the signal [[det-f5-signature]] looks for.

## Header

F5 canonically uses a password-derived RC4 stream + a length prefix.
The ST3GG implementation replaces RC4 with the [[st3gg-v3-header]]
envelope (magic + length + optional AES-GCM). Not interoperable with
reference F5 tools.

## Sources

- [[westfeld-2001-f5]] — Section 3 has the matrix-encoding derivation
- [[itu-t81-jpeg]] — DCT coefficient definitions
- [[cap-image-f5]] — capacity formula record
