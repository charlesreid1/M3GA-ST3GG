# AES-GCM before embedding

Encrypt the payload with AES-256-GCM before running the steg encoder.
The ST3GG-recommended sequence for any hide that must survive
discovery.

## Why encrypt before embed

Two orthogonal properties:

- **Steganography** hides the *fact* that a message exists.
- **Cryptography** protects the *content* if the message is found.

Encrypt-then-embed gives you both. If the steg is detected (chi-
square fires, someone dumps the LSB plane), the adversary sees random
bytes without the key — the payload is protected even after
discovery.

## What ST3GG uses

- **`crypto.encrypt_gcm` / `crypto.decrypt_gcm`** — AES-256-GCM
  wrapper. Nonce is random 12 bytes; tag is 16 bytes; authenticated
  associated data (AAD) is optional.
- **`stegg_encode_manual` / `stegg_text_encode`** with the
  `password` option auto-invoke AES-GCM before writing the payload
  to the carrier.

## The ST3GG v3 header interaction

See [[crypto/st3gg-v3-header]]. The v3 header includes:

1. Magic bytes derived from HMAC-SHA256(password, "st3gg-v3-magic").
2. 16-bit length prefix (of encrypted payload).
3. Optional deflate compression flag.
4. Optional AES-256-GCM flag.
5. If AES: 12-byte nonce + 16-byte tag + ciphertext.

The magic bytes double as a password-check without leaking the
password.

## Why NOT encrypt

- **The encrypted payload has high entropy** — ~7.9-8.0 bits/byte
  in the LSB plane. That's a statistical signal chi-square /
  bit-plane-entropy detectors WILL pick up. See
  [[myth-encryption-hides-steg]].
- If the priority is *undetectability* rather than *confidentiality*,
  use a *cover-shape-matching* embedding (matrix encoding, F5) with
  a low-entropy inner payload. Encryption is confidentiality, not
  concealment.

## The layered defense

Best-practice ordering for a sensitive hide:

1. **Compress** the plaintext (deflate). Reduces size, whitens
   distribution.
2. **Encrypt** with AES-256-GCM + random nonce.
3. **Embed** with a chi-square-resistant technique (F5, matrix
   encoding, matched-cover) if undetectability matters, or LSB if
   simplicity + speed matter more.
4. **Ship** through a byte-identical transport if possible.

## Sources

- [[st3gg-v3-header]] — the v3 header format
- [[st3gg-field-guide]] — ST3GG-specific crypto integration
- NIST SP 800-38D — AES-GCM spec
