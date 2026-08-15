# Text CJK / fullwidth-punctuation homoglyph steganography

Payload as a bit-per-punctuation-mark swap between ASCII punctuation and
its CJK-fullwidth twin. Sibling of [[text/homoglyph-cyrillic]]: same
one-bit-per-carrier shape, different alphabet.

## What the ST3GG implementation does

`text_core.encode_cjk_homoglyph / text_core.decode_cjk_homoglyph`. See
[[text-cjk-homoglyph]] and [[cap-text-cjk-homoglyph]].

Alphabet (bit 0 → ASCII, bit 1 → fullwidth):

- `,` (U+002C) ↔ `，` (U+FF0C)
- `.` (U+002E) ↔ `．` (U+FF0E)
- `;` (U+003B) ↔ `；` (U+FF1B)
- `:` (U+003A) ↔ `：` (U+FF1A)
- `!` (U+0021) ↔ `！` (U+FF01)
- `?` (U+003F) ↔ `？` (U+FF1F)
- `(` (U+0028) ↔ `（` (U+FF08)
- `)` (U+0029) ↔ `）` (U+FF09)

Framing: 16-bit LE length prefix + payload bits, one bit per ASCII
punctuation carrier. Capacity is
`floor((count_of_ascii_punct_in_cover - 16) / 8)` bytes.

## When to reach for it vs Cyrillic homoglyph

Pick CJK-fullwidth over Cyrillic when the cover is punctuation-heavy
(dialogue, lists, code comments, log lines) rather than letter-heavy.
The two techniques are otherwise interchangeable — same framing, same
capacity formula shape, same failure mode.

## Where it dies

- **NFKC normalization**: fullwidth punctuation maps to ASCII under NFKC.
  A single NFKC pass destroys the payload. See [[myth-homoglyph-nfkc]].
- **Font substitution**: fullwidth glyphs render wider than ASCII on
  Latin-only fonts — the stego *looks* wider than the plain cover in
  monospace UIs, which is a giveaway to a reader who knows what to look
  for.
- **Aggressive markdown/latex processors**: some renderers replace
  fullwidth punctuation with ASCII for consistency.

## Where it survives

- Plain UTF-8 pipelines: chat, code, HTTP raw, git commits.
- Slack paste ([[sv-cjk-slack-paste]]), Slack snippet
  ([[sv-cjk-slack-snippet]]) — see [[transport-slack-paste]].
- Rich-text UIs that don't NFKC input (which is most).

## Detection

- Byte-level: `text_core.detect_unicode_steg` picks up the
  fullwidth-punct pattern as one of its detectors.
- Visual: monospaced-font rendering shows fullwidth punct as noticeably
  wider than ASCII punct in the same run. A run of `）（，．` sitting in
  otherwise Latin prose is the tell.
- Statistical: chi-square-style test on `(count_ascii_punct,
  count_fullwidth_punct)` ratio against a plain-language baseline.

## Sources

- [[unicode-tr36-security]] — UTS #39 confusables + NFKC guidance
- [[unicode-nfkc]] — NFKC normalization spec (compatibility mappings)
- [[st3gg-field-guide]] — ST3GG-specific framing
