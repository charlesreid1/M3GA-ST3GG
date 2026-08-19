# Text braille-block steganography

Payload as a run of Braille codepoints appended after the cover. Every
payload byte maps 1:1 into a Braille Patterns codepoint (`U+2800`
+ byte). Overt but bulletproof.

## What the ST3GG implementation does

`text_core.encode_braille / text_core.decode_braille`. See
[[text-braille]].

Alphabet:

- Payload byte `b` → Braille codepoint `U+2800 + b`. The Braille
  Patterns block spans `U+2800..U+28FF` — exactly 256 codepoints,
  covering all 8-bit values.

Framing: none. The Braille run is appended verbatim after the cover;
receiver strips everything before the first `U+2800..U+28FF` codepoint
and decodes.

## Where it dies

Almost nowhere. Braille codepoints round-trip through every UTF-8
pipeline without touching NFKC decomposition rules. If a channel
preserves Unicode text at all, it preserves Braille.

Edge cases:

- **Aggressive script-based sanitizers** that whitelist Latin script
  and strip everything else may filter Braille.
- **Some accessibility software** interprets Braille codepoints and
  reads them aloud — that reveals the payload to sighted attackers
  monitoring a screen reader.

## Where it survives

- Raw UTF-8 pipelines (files, HTTP, git, all consumer messengers).
- Slack paste, Discord, WhatsApp text, iMessage — all preserve.
- Terminal stdout (Braille codepoints render as tiny dot-patterns
  and copy through mouse-select).

## Why "visibly-perturbed"

A wall of `⠈⠑⠇⠇⠕` at the end of a message is not stealth. Anyone
reading sees the Braille block. But when the goal is *round-trip
guarantee* rather than *concealment* — say, embedding a payload in an
image caption that MUST decode identically on the other end — Braille
is the safest choice in this family.

## Detection

- Byte scan: any codepoint in `U+2800..U+28FF`.
- Trivially recognized by every steganalysis tool that checks Unicode
  blocks.
- Visual: the dot pattern.

## Sources

- [[st3gg-field-guide]] — ST3GG-specific framing
- Unicode Standard Ch. 22 — Braille Patterns block
