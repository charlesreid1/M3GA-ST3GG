# Emoji tag-sequence steganography (black-flag payload)

A single visible base emoji (🏴) followed by invisible Unicode tag-block
chars encoding an ASCII payload, terminated by a CANCEL TAG. Legitimate
Unicode use is emoji subdivision flags (England, Scotland, Wales); the
steg use hides arbitrary ASCII behind one visible glyph.

## What the ST3GG implementation does

Composed via `text_core.encode_invisible_ink` with a black-flag base.
See [[emoji-tag-sequence]] and [[text-invisible-ink]].

Payload structure:

```
🏴 (U+1F3F4) + [U+E00xx ASCII-shadow bytes] + U+E007F CANCEL TAG
```

Every ASCII byte in the payload becomes one tag codepoint
(`byte + 0xE0000`). The base emoji renders; the tag chars render as
nothing.

## Legitimate vs steg use

Unicode 8.0 (2015) defined tag sequences on a black-flag base for
subdivision flags:

- 🏴󠁧󠁢󠁥󠁮󠁧󠁿 = flag of England (`🏴` + `gbeng` in tag codepoints + cancel)
- 🏴󠁧󠁢󠁳󠁣󠁴󠁿 = flag of Scotland
- 🏴󠁧󠁢󠁷󠁬󠁳󠁿 = flag of Wales

Steg use rides the same grammar: any ASCII payload becomes a valid
tag sequence syntactically, but the receiver never renders as a
subdivision flag — the base + arbitrary tag chars + cancel is
"unknown tag sequence" territory, which renders as just the base.

## Where it dies

- **Slack paste** ❌ — Slack canonicalizes emoji to `:colon_form:`;
  tag chars are dropped. See [[myth-emoji-tag-survives-paste]] and
  [[sv-emoji-tag-slack-paste]].
- **LLM sanitizers post-2024** filter tag blocks. See
  [[greenberg-2024-tag-injection]].
- **Terminal mouse-copy** drops tag chars on the visible-glyph path.

## Where it survives

- Slack snippet ([[sv-emoji-tag-slack-snippet]]) — raw bytes bypass
  the canonicalization.
- HTTP raw, GitHub, email attachment: byte-identical.
- Chat clients that preserve full Unicode.

## The prompt injection story

Same as [[text/invisible-ink]] — tag-block characters read as their
ASCII shadow in LLM tokenizers. A payload behind a black-flag emoji
becomes an "invisible instruction" in a chat message. The 2024–2026
wave of mitigations targets this family specifically.

## Detection

- Byte scan for `U+1F3F4` followed by any codepoint in
  `U+E0020..U+E007F`.
- `text_core.detect_unicode_steg` catches emoji-tag payloads.

## Sources

- [[unicode-tag-block]] — tag block spec
- [[unicode-emoji-tag-sequences]] — emoji + tag grammar
- [[greenberg-2024-tag-injection]] — the attack lineage
- [[st3gg-field-guide]] — ST3GG-specific framing
