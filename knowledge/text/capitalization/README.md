# Text word-initial capitalization steganography

Payload as the choice of upper/lower case on each word's initial
letter. The "looks like prose" method — no unusual codepoints,
no NFKC risk, but every word must start with a letter.

## What the ST3GG implementation does

`text_core.encode_capitalization / text_core.decode_capitalization`.
See [[text-capitalization]].

Alphabet:

- Word-initial letter uppercase → bit 1
- Word-initial letter lowercase → bit 0

Framing: 16-bit LE length prefix, 1 bit per word. Capacity:
`floor((word_count - 16) / 8)` bytes.

## Where it dies

- **Auto-capitalizers**: iOS Notes, iMessage, and many chat clients
  auto-capitalize the first word of each sentence — this rewrites
  the first bit of every sentence. Detectable and often unrecoverable.
- **Sentence-boundary capitalizers**: writing tools like Grammarly
  "correct" sentence-initial capitalization.
- **Title-case renderers**: some CMS pipelines force title-case on
  headings.

## Where it survives

- Plain-text UTF-8 pipelines that don't touch case: files, HTTP raw,
  git commits, code comments.
- Chat clients with autocorrect disabled.
- Slack paste ([[sv-capitalization-slack-paste]]) — as long as the
  user pasted without auto-cap.

## Why "prose-like"

The stego IS the cover with case swaps. No visual gap, no strange
characters, no font substitution. To an unsuspecting reader it's
just "someone whose Shift key sticks." The cost: capacity is
1 bit per WORD, so the cover must be roughly 8× the payload size
in words — a 100-byte payload needs an 800-word cover.

## Python-only in this fork

The browser Text Lab in `index.html` does not include
capitalization; it's Python-only. Round-tripping through the browser
requires switching to a technique the browser exposes (zero-width,
homoglyph-cyrillic).

## Detection

- Chi-square-style test: real prose has a known cap-ratio (about 5%
  of words start with a capital, mostly at sentence starts and proper
  nouns). Stego at 1 bit/word will push the ratio toward 50%.
- Compare word-initial capitalization distribution to a plain-prose
  baseline.

## Sources

- [[st3gg-field-guide]] — ST3GG-specific framing
