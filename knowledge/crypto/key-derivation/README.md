# Key derivation

ST3GG needs two derived values from the password: the "magic" that
marks payloads and the AES-256-GCM key that encrypts them. HMAC-
SHA256 (with a domain-separator) provides both.

## The two derivations

```
MAGIC = HMAC-SHA256(password, "st3gg-v3-magic")[:8]
KEY   = HMAC-SHA256(password, "st3gg-v3-key")[:32]
```

Two separate labels ("st3gg-v3-magic" vs "st3gg-v3-key") keep the
values independent: knowing the magic doesn't reveal the key, and
vice versa.

## Why HMAC-SHA256, not scrypt / bcrypt / argon2

- ST3GG's threat model is **not** offline password cracking. The
  password is out-of-band-shared between sender and receiver.
- The magic bytes and key are derived once per encode/decode, not
  once per attempted-password-guess-in-a-loop.
- If the payload is discovered and someone wants to brute-force the
  password, the attack is bounded by the AES-256-GCM authentication
  tag failure — every wrong password guess fails at GCM auth,
  requiring a full trial decryption. That's slow enough for casual
  attackers; not slow enough for a determined offline crack.

**If your threat model includes offline brute-force with a weak
password**: derive a memory-hard KDF value from the password first
(argon2id) and use *that* as the HMAC key input. Not the default in
ST3GG.

## Domain separation

Both derivations use `HMAC-SHA256(password, label)`. The label
domain-separates them so no single output leaks the others.

Additional labels that could exist (not currently used):
- `"st3gg-v3-nonce"` — derived AES-GCM nonce (would defeat
  random-nonce practice; ST3GG uses a random 12-byte nonce
  per payload instead).
- `"st3gg-v3-permutation-seed"` — for randomized-traversal LSB.
  ST3GG currently uses an explicit `seed` parameter rather than
  password-deriving it.

## The keyless case

For no-password mode, HMAC uses an empty key:

```
MAGIC_keyless = HMAC-SHA256("", "st3gg-v3-keyless")[:8]
```

Same domain-separation guarantee; no confidentiality.

## Sources

- RFC 2104 — HMAC
- NIST FIPS 198-1 — HMAC standard
- [[st3gg-v3-header]] — the v3 header spec
- [[st3gg-field-guide]] — ST3GG-specific derivation
