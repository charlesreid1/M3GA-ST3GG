# Matryoshka — 15-second triage

"Is this image a matryoshka hide?"

## The impossible-to-see part

At the outermost layer, matryoshka looks IDENTICAL to a shallow LSB
hide:

- Same chi-square rate.
- Same RS / SPA fingerprint.
- Same bit-plane entropy.
- Same visible artifact profile.

**Without the password, you cannot distinguish depth-1 from depth-11.**
Every layer's magic is HMAC-derived; a wrong-password scan sees
random bytes at every level. This is the whole security argument.

## The visible-to-you part

If you HAVE the password (or an educated guess about it):

1. Run `matryoshka_core.decode_nested(image, config)` with the
   password.
2. If the return list has multiple entries, you're inside a nested
   stack — the number of entries is the depth reached before hitting
   either the innermost payload or `max_depth`.
3. If the return list has one entry that's a payload (not an
   image), you're at depth 1 — a normal ST3GG-v3 hide.

## Signal cheat sheet (without a password)

| Signal | Diagnosis |
|--------|-----------|
| Chi-square LOUD + PNG carrier | Some LSB hide is present. Could be depth 1 or depth 11 — can't tell |
| No STEG header at any tried password | Either not ST3GG-format, or wrong password. Depth is orthogonal |
| Decoded payload IS a PNG (byte-perfect image magic) | Almost certainly a matryoshka layer, not a real payload |
| Decoded payload is not an image | Either the innermost payload OR a non-image payload wrapped in `<len><name><body>` |

## Signal cheat sheet (with a password)

| Signal | Diagnosis |
|--------|-----------|
| `decode_nested` returns 1 entry (payload) | Depth 1 — normal ST3GG-v3 hide |
| `decode_nested` returns 3-5 entries, all `type='steg_header'` | Matryoshka, depth = length of list |
| `decode_nested` returns 11 entries + `max_depth_reached` | May be deeper than 11 — raise `config.max_depth` |
| One entry `type='smart_scan_*'` | STEG header failed at that layer; fallback smart scan recovered — indicates password mismatch OR non-ST3GG encoder at that level |

## Practical detection flow

1. **Try `decode_nested` with candidate passwords**. The CTF
   challenge description usually names the password.
2. **If nothing decodes with obvious passwords**, matryoshka isn't
   the technique (or the password is genuinely unknown). Fall back
   to standard LSB / DCT / chunk triage.
3. **If ANY layer decodes as a PNG**, keep going — the payload is
   at least one layer deeper.

## The is-this-a-PNG check

`matryoshka_core.is_image_data(data)` recognizes:

- **PNG** — `89 50 4E 47 0D 0A 1A 0A`
- **JPEG** — `FF D8 FF`
- **GIF** — `47 49 46 38`
- **BMP** — `42 4D`

Any of these at the head of a decoded payload triggers recursion. A
payload byte stream that happens to START with one of these magics
is a rare false-positive; happens with random binary data ~1 in 4 B.

## The file-wrap convention

The innermost payload may be wrapped as
`<length_byte><filename><body>` (via `extract_file_from_data`).
Filename length 3-100 chars, dot-separated extension from a fixed
list (see `VALID_FILE_EXTENSIONS` in `matryoshka_core`). If the
wrap format is detected, the CTF solution is often a filename +
raw bytes rather than raw text.

## Comparison to standard ST3GG-v3

A single `img_core.decode` call handles the depth-1 case; recursion
is only needed when the payload IS another image. Every matryoshka
detection reduces to a chain of `img_core.decode` calls.

## Sources

- [[image-matryoshka]]
- [[sv-matryoshka-slack-upload]]
- [[st3gg-field-guide]] — ST3GG-specific SPECTER walkthrough
