# Text Hangul-filler steganography

Payload as a mix of `U+3164` HANGUL FILLER and plain space. Distinct
codepoint from ASCII space, so parsers that tokenize on `U+0020` see
a token boundary where the receiver sees payload structure.

## What the ST3GG implementation does

`text_core.encode_hangul / text_core.decode_hangul`. See
[[text-hangul]].

Alphabet:

- `U+3164` HANGUL FILLER → bit 1
- `U+0020` SPACE → bit 0

Framing: 16-bit LE length prefix, 1 bit per position. Capacity: 8
codepoints per payload byte + prefix.

## Why Hangul filler

`U+3164` is defined as a *placeholder* in Hangul contexts — it renders
as a blank Hangul syllable slot in most fonts (visually a small blank
that reads as a space) but is semantically a Hangul character, not
whitespace. A tokenizer splitting on `\s+` doesn't treat U+3164 as a
separator; a human reader in a Latin-only UI doesn't distinguish it
from a space.

## Where it dies

- **NFKC normalization**: HANGUL FILLER normalizes to nothing (its
  compatibility decomposition is empty). NFKC destroys the payload.
- **Font substitution**: on fonts without a Hangul filler glyph, some
  systems render `.notdef` (visible tofu) instead of a blank slot.
- **Aggressive whitespace-normalizing renderers**: any pipeline that
  treats "blank slot" as a space may collapse consecutive fillers.

## Where it survives

- Raw UTF-8 (files, HTTP, git).
- Chat clients that preserve Unicode.
- Slack paste ([[sv-hangul-slack-paste]]) — CJK-comfortable.

## Detection

- Byte scan: any `U+3164` in a non-Korean text context.
- `text_core.detect_unicode_steg` includes Hangul-filler detection.
- Visual: in some monospace fonts, filler renders as a slightly wider
  gap than a regular space.

## Sources

- [[unicode-nfkc]] — Hangul syllable normalization + filler semantics
- [[st3gg-field-guide]] — ST3GG-specific framing
