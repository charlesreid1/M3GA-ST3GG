# Text confusable-whitespace steganography

Two bits per space by picking among four whitespace codepoints that
render (nearly) identically. Higher capacity than trailing-whitespace
at the cost of narrower survival.

## What the ST3GG implementation does

`text_core.encode_confusable / text_core.decode_confusable`. See
[[text-confusable]].

Alphabet:

- `U+0020` SPACE → 00
- `U+00A0` NO-BREAK SPACE → 01
- `U+2009` THIN SPACE → 10
- `U+202F` NARROW NO-BREAK SPACE → 11

Framing: 16-bit LE length prefix, 2 bits per ASCII-space carrier
position. Capacity:
`floor((count_of_ascii_spaces_in_cover - 8) / 4)` bytes.

## Where it dies

- **NFKC normalization**: `U+00A0`, `U+2009`, `U+202F` all normalize
  to `U+0020` under NFKC compatibility mapping. See [[unicode-nfkc]].
- **Aggressive Unicode collapsers**: any pipeline that treats "all
  whitespace-y things as ASCII space" (many search boxes, some
  database TEXT columns, whitespace-normalizing tokenizers).
- **Markdown / HTML**: some renderers collapse consecutive whitespace
  regardless of Unicode identity.

## Where it survives

- Byte-preserving UTF-8 pipelines (files, HTTP, git commits).
- Rich-text UIs that preserve Unicode identity of whitespace.
- Slack paste ([[sv-confusable-slack-paste]]).

## Why "confusable" and not "whitespace"

"Whitespace" as a technique already means SNOW-style trailing space/tab
([[text/whitespace]]). Confusable-whitespace re-uses Unicode's
"confusables" concept (UTR #39) — codepoints that render alike but
are semantically distinct — to encode more bits per position.

## Detection

- Byte scan: any non-ASCII whitespace codepoint in text that's
  otherwise ASCII is a strong hit.
- `text_core.detect_unicode_steg` includes confusable-space detection.
- Visual (rendering-dependent): thin/narrow spaces may render slightly
  differently in monospace fonts.

## Sources

- [[unicode-tr36-security]] — UTS #39 confusables + security
  implications
- [[unicode-nfkc]] — NFKC compatibility mappings for whitespace
- [[st3gg-field-guide]] — ST3GG-specific framing
