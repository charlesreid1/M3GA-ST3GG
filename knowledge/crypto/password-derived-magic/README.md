# Password-derived magic bytes

ST3GG's clever trick: the "magic bytes" that mark a payload as
ST3GG-format are derived from HMAC-SHA256 of the password (or of a
fixed string for keyless mode). A scanner without the password
can't distinguish an encrypted payload from random noise — the
magic doesn't leak the password.

## Why this matters

Every stego tool needs a way for the receiver to recognize "yes,
this stream contains my payload" versus "no, this is unrelated
data." The obvious solution is a fixed magic string ("STEGO", "F5-",
"steghide-v1"). But that fixed magic is *itself* a detection
signal — a scanner looks for the magic and immediately knows the
tool used.

Password-derived magic solves this:

```
MAGIC = HMAC-SHA256(password, "st3gg-v3-magic")[:8]
```

- **Same password** → same 8-byte magic → payload recovered.
- **Different password** → different magic → scanner sees random
  bytes, no signal.

The trade-off: nobody can validate a payload without knowing the
password. That's fine — the hider and receiver share the password by
some out-of-band means, and everyone else sees random-looking bytes.

## What ST3GG does

`crypto.derive_magic(password)` and `crypto.derive_magic_keyless()`.
The v3 header (see [[crypto/st3gg-v3-header]]) uses the derived magic
as the first 8 bytes.

## Keyless mode

For payloads that don't need password protection (CTF challenges,
public demos), ST3GG uses a fixed HMAC input:

```
MAGIC = HMAC-SHA256("", "st3gg-v3-keyless")[:8]
```

Keyless payloads are recoverable by anyone who knows they're
ST3GG-format; the magic still doesn't leak sender identity or any
per-payload secret.

## Comparison to steghide / F5 / OutGuess

- **steghide**: fixed "SteG" magic + AES256-encrypted metadata.
  Detectable by signature scan even without the password.
- **F5**: passphrase-permuted embedding order, but no magic bytes —
  presence detected by chi-square / F5-signature scanner.
- **OutGuess**: passphrase-derived embedding but fixed structure;
  presence detected by calibration.
- **ST3GG v3**: derived magic; no fixed pattern to signature-scan.

## The invariant

Password-derived magic protects *the fact of the tool's use*, not
just *the payload contents*. A scanner that looks for "ST3GG" magic
finds nothing — they'd have to guess the password to even confirm
ST3GG was used.

## Sources

- [[st3gg-v3-header]] — the v3 header spec
- [[st3gg-field-guide]] — ST3GG-specific derivation
