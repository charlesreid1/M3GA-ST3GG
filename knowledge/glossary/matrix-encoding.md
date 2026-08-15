# matrix encoding

The F5 primitive. Hide a k-bit codeword by flipping at most one of
2^k - 1 carrier coefficients. Trades capacity for stealth.

## The idea

- k = number of payload bits per group
- n = 2^k - 1 = number of carriers per group

For each n-carrier group and each k-bit codeword:

1. Compute `syndrome = XOR of the k-bit binary index of each carrier
   whose bit contributes to the codeword` (essentially a Hamming-
   style syndrome).
2. If `syndrome == desired_k_bit_codeword`: no change needed.
3. Otherwise: flip exactly ONE carrier's bit — the carrier whose
   index equals `syndrome XOR desired`.

Result: k bits embedded per group of n = 2^k-1 carriers, with at
most one change per group.

## Why it's chi-square-resistant

Random LSB replacement changes ~n/2 carriers per n-carrier group.
Matrix encoding changes 0 or 1 per group. Fewer changes = smaller
statistical footprint = chi-square barely fires.

## Trade-off: capacity

Capacity ratio: k / (2^k - 1) bits per carrier.

- k=1, n=1: 1 bit / 1 carrier = 1.0 (same as LSB)
- k=2, n=3: 2 bits / 3 carriers ≈ 0.67
- k=3, n=7: 3 bits / 7 carriers ≈ 0.43
- k=4, n=15: 4 bits / 15 carriers ≈ 0.27

F5 typically uses k=1..5 based on payload size vs cover capacity.

## In the KR

See [[image-f5]] for the technique record. The `technical_body`
carries a formula for effective capacity given cover coefficient
count.

## Related terms

- [[shrinkage]] — the F5 edge case when the flip pushes a coefficient
  to zero.
- [[carrier-family]] / [[layer]] — matrix encoding is a coefficient-
  layer image technique.

## Sources

- [[westfeld-2001-f5]] — the F5 paper introducing matrix encoding
  for stego.
