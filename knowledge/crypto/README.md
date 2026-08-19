# Crypto layer

Payloads are usually encrypted BEFORE embedding, so cracking the
carrier reveals ciphertext rather than plaintext. ST3GG's built-in
crypto flow is:

1. **Password-derived magic bytes** — HMAC-SHA256 of a fixed label
   under the user's password. The magic that follows in the payload
   header can only be produced by someone with the password;
   detectors that don't know it see uniform noise. See
   [[st3gg-v3-header]].
2. **AES-256-GCM** for payload encryption with authenticated tags.
3. **Deflate/zstd compression** before encryption to reduce entropy
   tells (though ciphertext is already max-entropy, so this is
   mostly for size).
4. **Length prefix** so decode knows when to stop.

## Why the extractor bounces on non-ST3GG hides

Both `stegg_lsb_smart_scan` and `stegg_decode_manual` require the
`ST3GG` magic header. If someone hid a payload with vanilla `stegg`
using our header, they'll extract. If they used any OTHER LSB tool,
wrote raw bytes to pixels, or used a homebrew scheme, both tools
return "no extraction" even when the statistical evidence is
overwhelming. This is a *feature* — it means we won't hallucinate
payloads out of random noise — but it means the field guide's
signal-diagnosis section (see [[detection/README]]) is the only way
to close cases the extractor can't finish.

## Alternatives / roadmap

- **Key derivation** — currently direct-from-password HMAC; PBKDF2
  / scrypt / argon2 are options for slower brute force resistance.
- **Password-less magic** — a fixed magic for public CTFs where the
  goal is to advertise the hide, not conceal it.

The ST3GG v3 header is authoritative for anything encoded with this
fork; see [[st3gg-v3-header]] and the `crypto.py` module.
