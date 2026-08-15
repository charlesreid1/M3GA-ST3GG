# The ST3GG v3 header

The wrapping format around every ST3GG-encoded payload. Combines
password-derived magic + length + optional compression + optional
AES-256-GCM into a self-describing container.

## The layout

```
+---------------------+-----------------------+------+-----+---------+---------+---------+
| MAGIC (8 bytes)     | FLAGS (1 byte)        | LEN (2 bytes) | [NONCE] | [PAYLOAD] | [TAG] |
+---------------------+-----------------------+------+-----+---------+---------+---------+
   HMAC-derived         bit 0 = compressed      little-        (present    (optionally  (present
   from password        bit 1 = encrypted       endian          if bit 1)    compressed) if bit 1)
```

- **MAGIC (8 bytes)**: `HMAC-SHA256(password, "st3gg-v3-magic")[:8]`.
  See [[crypto/password-derived-magic]].
- **FLAGS (1 byte)**: bit 0 = deflate-compressed, bit 1 = AES-GCM-
  encrypted. Other bits reserved.
- **LEN (2 bytes, LE)**: total payload length after any compression
  and encryption. Max payload 65535 bytes.
- **NONCE (12 bytes)** if encrypted: random per-message nonce.
- **PAYLOAD**: the actual data, possibly deflate-compressed, possibly
  AES-256-GCM-encrypted.
- **TAG (16 bytes)** if encrypted: GCM authentication tag.

Overhead for the plain case: 11 bytes (magic + flags + len).
Overhead for the encrypted-and-compressed case: 39 bytes (magic +
flags + len + nonce + tag).

## Encoding order

1. Serialize plaintext payload.
2. If deflate flag: `deflate.compress(payload)`.
3. If encrypt flag: `AES-256-GCM(key=derived, nonce=random,
   data=step2, aad=magic || flags || len)` → produces `ciphertext + tag`.
4. Prepend `magic || flags || len` (and nonce if step 3 ran).
5. Handoff to the steg embedder.

## Decoding order

1. Steg extractor pulls bytes out of the carrier.
2. Check magic byte match against `HMAC-SHA256(password,
   "st3gg-v3-magic")[:8]`. If mismatch → "no ST3GG payload."
3. Read flags, len, and (if encrypted) nonce.
4. Read `len` bytes of payload + (if encrypted) 16-byte tag.
5. GCM-verify with associated data = `magic || flags || len`. If
   invalid → wrong password or corrupted payload.
6. Deflate-decompress if flag set.
7. Return plaintext.

## Why v3

- **v1**: fixed magic ("ST3GG"), plaintext length prefix, no crypto.
- **v2**: added optional AES-256-CBC + IV, dropped fixed magic in
  favor of the first HMAC-derived-magic experiment.
- **v3** (current): HMAC-derived magic + AES-256-GCM (authenticated,
  simpler than CBC + HMAC) + optional deflate compression + AAD
  binding to the header itself.

The version bump is signaled by a byte inside the magic derivation:
the actual HMAC label is `"st3gg-v3-magic"`, so a v4 will use
`"st3gg-v4-magic"` and be automatically distinguishable.

## Header on/off decisions

- **Compression on**: default for text payloads (well-compressed).
  Default off for already-random data (encrypted, images).
- **Encryption on**: default when a password is given. Off in keyless
  mode.

## Sources

- [[st3gg-v3-header]] — the version spec entry in the bibliography
- [[st3gg-field-guide]] — ST3GG-specific v3 usage
