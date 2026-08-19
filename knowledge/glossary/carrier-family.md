# carrier_family

The ST3GG-record taxonomy of **what medium a technique embeds into**.
One of a small, fixed set.

## The six families

- **`image`** — PNG, JPEG, GIF, WebP, HEIC. Bit-plane, pixel-domain,
  coefficient-domain, and container-level hides.
- **`text`** — UTF-8 text (plain, markdown, HTML, source code).
  Character-level, whitespace, prose-shape hides.
- **`emoji`** — emoji sequences (technically Unicode, but treated
  as its own family because emoji have their own canonicalization,
  their own transport rules, and their own techniques —
  substitution, skintone, tag-sequences).
- **`audio`** — WAV, MP3, FLAC. Sample LSB, echo, phase, spectrogram.
- **`network`** — packet-level channels (headers, timing, payloads).
  Not a file at all.
- **`document`** — PDF, ZIP, SQLite. Container-format hides.
- **`universal`** — techniques that apply across families (crypto
  wrappers, key derivation, layer taxonomy itself).

## Usage in the KR

Every technique, survival, signature, and detector record carries a
`carrier_family` field. Bibliography records don't (they're
citations, not technique instances).

Filter by carrier family in `stegg_search_records`:

```python
stegg_search_records(category="technique", carrier_family="emoji")
# → text-emoji-substitution, emoji-skintone, emoji-tag-sequence
```

## Related

- [[layer]] — orthogonal axis for *where in the format stack* the
  payload lives.
- [[stealth-class]] — orthogonal axis for perceptibility.
