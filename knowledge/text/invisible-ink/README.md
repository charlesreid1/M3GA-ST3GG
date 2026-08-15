# Text invisible-ink (Unicode tag block) steganography

Payload as ASCII characters mapped one-to-one into the Unicode
Tags block (U+E0000..U+E007F), then rendered as nothing by every
font. The technique behind the 2024–2026 prompt-injection wave.

## What the ST3GG implementation does

`text_core.encode_invisible_ink / text_core.decode_invisible_ink`. See
[[text-invisible-ink]].

Alphabet:

- `U+E0000` (LANGUAGE TAG) → start marker
- `U+E0020..U+E007E` → ASCII-shadow bytes 0x20..0x7E, offset by
  `U+E0020 - 0x20 = U+E0000`. Each printable ASCII char has a
  one-to-one shadow codepoint.
- `U+E007F` (CANCEL TAG) → end marker

Framing: `[START] [ASCII-shadow payload] [CANCEL]`. Payload IS ASCII —
`b"hello"` becomes `U+E0068 U+E0065 U+E006C U+E006C U+E006F`. The
receiver subtracts `U+E0000` from each codepoint and gets plain ASCII
back. No length prefix; the CANCEL TAG is the terminator.

## Why the tag block

The Unicode Tags block was originally spec'd (1999) to carry
language-selection metadata as invisible companion characters to
regular text. Almost no font provides glyphs for the tag block; every
tag codepoint renders as literal nothing (or as `.notdef` in the
strictest fallback). Encoders exploit that: your payload is *present*
in the byte stream, transparent in every viewer.

## Where it dies

- **Slack paste**: `.text` view drops tag chars; `blocks[]` view may
  keep them depending on the client. See
  [[sv-invisible-ink-slack-paste]].
- **LLM sanitizers (post-2024)**: many vendors added explicit
  tag-block strippers after Greenberg's 2024 attack. See
  [[myth-unicode-tag-passes-sanitizers]] and
  [[greenberg-2024-tag-injection]].
- **Some fonts render `.notdef` box glyphs** for tag codepoints
  instead of nothing — the payload becomes visible as a run of
  tofu boxes.
- **Terminal mouse-copy**: strips them out on the visible-glyph path.

## Where it survives

- Byte-level UTF-8 pipelines: file save, HTTP raw, git commits.
- Slack snippet ([[sv-invisible-ink-slack-snippet]]).
- Copy/paste into most rich-text UIs (Discord, chat clients) that
  don't specifically sanitize the tag block.

## The 2024 prompt-injection story

Riley Goodside and Joseph Thacker demonstrated in 2024 that GPT-4,
Claude, and Gemini all read tag-block characters as their ASCII shadow
during tokenization, meaning an "invisible" tag-block string was a
first-class instruction in the model's input. Vendors have shipped
mitigations through 2025-2026; effectiveness varies.
See [[greenberg-2024-tag-injection]].

## Detection

- Byte scan: any codepoint in `U+E0000..U+E007F` is a hit.
- `text_core.detect_unicode_steg` picks these up.
- Visual: font-dependent. Modern macOS Safari renders as nothing;
  older Firefox on Linux renders `.notdef` boxes.

## Sources

- [[unicode-tag-block]] — original spec (deprecated for language
  selection, revived for emoji subdivision flags)
- [[greenberg-2024-tag-injection]] — the 2024 attack writeups
- [[st3gg-field-guide]] — ST3GG-specific framing
