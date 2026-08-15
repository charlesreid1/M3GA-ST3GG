# Text mathematical-alphanumerics steganography

Payload as swaps between plain Latin letters and their Mathematical
Alphanumeric bold twins (`U+1D400..`). Higher stealth than emoji
substitution, lower stealth than homoglyphs — bold letters are
visibly different.

## What the ST3GG implementation does

`text_core.encode_mathbold / text_core.decode_mathbold`. See
[[text-mathbold]].

Alphabet:

- Plain Latin letter (e.g. `A` U+0041) → bit 0
- Mathbold twin (e.g. `𝐀` U+1D400) → bit 1

Framing: 16-bit LE length prefix, 1 bit per Latin cover position.

The math alphanumerics block spans `U+1D400..U+1D7FF` and covers bold,
italic, bold-italic, script, fraktur, double-struck, and several other
"styled" variants of Latin/Greek letters and digits. ST3GG's default
uses bold (`U+1D400..`) but the alphabet expansion is straightforward.

## Where it dies

- **NFKC normalization**: math alphanumerics decompose to their plain
  ASCII/Latin base under NFKC (compatibility mapping). One NFKC pass
  destroys the payload. See [[myth-homoglyph-nfkc]] — same trap.
- **Font substitution**: math alphanumerics require Unicode 3.1+ font
  coverage. On systems without them, letters render as tofu (visible
  hole in the message).
- **Screen-reader accessibility software**: some transcribers convert
  math alphanumerics to plain letters before reading aloud — the
  payload is preserved for sighted readers only.

## Where it survives

- Raw UTF-8 (files, HTTP, git).
- Chat clients with modern Unicode fonts.
- Slack paste ([[sv-mathbold-slack-paste]]) — mathbold renders in Slack.

## Why "visibly-perturbed"

The stego is *readable* — humans see bold-letter runs mixed with
plain letters and their brain reads through it. But it's **not
invisible**; anyone looking at the raw string sees the perturbation
immediately. Trade-off vs Cyrillic homoglyphs: mathbold looks like
"someone was trying to be fancy", Cyrillic homoglyphs look like plain
prose. Pick per audience.

## Detection

- Byte scan: any codepoint in `U+1D400..U+1D7FF`.
- `text_core.detect_unicode_steg` includes mathbold detection.
- Visual: mixed bold/plain text is the tell.

## Sources

- [[unicode-nfkc]] — NFKC compatibility decomposition of math
  alphanumerics
- [[st3gg-field-guide]] — ST3GG-specific framing
