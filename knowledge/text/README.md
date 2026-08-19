# Text steganography

Payload hidden inside text. Every text-steg technique operates at
[[layer-character]] (Unicode codepoints) or [[layer-semantic]] (which
words start with a capital, whitespace patterns interpreted as bits).
The universal carrier is [[fmt-utf8-text]].

## Techniques by stealth class

- **Invisible** — renders as nothing in almost every UI:
  [[text-zero-width]], [[text-invisible-ink]] (Unicode tag block),
  [[text-variation]], [[text-combining]], [[text-hangul]],
  [[text-confusable]].
- **Prose-like** — visually blends into normal writing:
  [[text-cyrillic-homoglyph]], [[text-cjk-homoglyph]],
  [[text-capitalization]].
- **Visibly perturbed** — payload is a visible block or shape:
  [[text-braille]], [[text-emoji-substitution]], [[text-mathbold]],
  [[text-directional]].

## Which one to reach for

- **Wants invisible** → [[text-zero-width]]. Renders as nothing,
  survives most copy/paste, dies to Unicode normalization and to
  terminal glyph filtering (see [[transport-terminal-stdout]]).
- **Wants plausible prose** → [[text-cyrillic-homoglyph]] or
  [[text-cjk-homoglyph]]. Both die to NFKC — see
  [[myth-homoglyph-nfkc]].
- **Whitespace-only carrier** → [[text-whitespace]] (SNOW-style) or
  [[text-confusable]] (2 bits per space).
- **Must survive Slack paste** → 13 of 15 text techniques survive;
  the two that don't are [[text-whitespace]] and
  [[text-invisible-ink]], both recoded on paste. Use
  [[transport-slack-snippet]] for those.

## Length-prefixed vs delimited

Methods with a 16-bit length prefix ([[text-cyrillic-homoglyph]],
[[text-cjk-homoglyph]], [[text-whitespace]], [[text-variation]],
[[text-combining]], [[text-confusable]], [[text-hangul]],
[[text-mathbold]], [[text-capitalization]]) bounce on short covers
— run `stegg_text_capacity` first. Methods without a prefix
([[text-zero-width]], [[text-invisible-ink]], [[text-braille]],
[[text-emoji-substitution]], [[emoji-skintone]]) either delimit or
extend the cover with an appended block; no capacity ceiling.

## Detection

`stegg_text_steg` / `stegg_text_steg_message` runs the full detector
suite. See myths [[myth-homoglyph-nfkc]] and
[[myth-zero-width-invisible-everywhere]] for the common misreads.
