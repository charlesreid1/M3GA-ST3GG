# Text whitespace (SNOW-style) steganography

Payload as trailing whitespace on each line — space (`0x20`) → bit 0,
tab (`0x09`) → bit 1. Named after Matthew Kwan's SNOW tool (1998).

## What the ST3GG implementation does

`text_core.encode_whitespace / text_core.decode_whitespace`. See
[[text-whitespace]].

Alphabet:

- Space (`0x20`) at end of line → bit 0
- Tab (`0x09`) at end of line → bit 1

Framing: 16-bit LE length prefix distributed across the first two
lines, then 8 bits per subsequent line as trailing whitespace.
Capacity: `floor((line_count - 2) / 1)` bytes for 8-bit-per-line
packing.

## Where it dies

Everywhere trailing whitespace is normalized — which is more places
than you'd think:

- **Slack paste**: trims trailing whitespace on the rendered post.
  See [[sv-whitespace-slack-paste]] (❌) vs
  [[sv-whitespace-slack-snippet]] (✅).
- **Git pre-commit hooks and `core.whitespace`**: strip trailing WS
  by default in many repos.
- **Most rich-text editors**: trim on save (VSCode "Trim Trailing
  Whitespace on Save" is on by default in many configs).
- **Email clients**: often strip trailing whitespace on the wire.
- **Markdown parsers**: eat trailing spaces (though preserve 2+ as
  hard line breaks).
- **Web forms**: `.trim()` in JavaScript, aggressive input sanitizers.

The technique is a raw-file transport only. If it must survive a
render pipeline, use something else.

## Where it survives

- Byte-identical file transports: HTTP raw, direct file transfer,
  Telegram-as-file, GitHub raw blob URL, email as attachment (not
  as inline).
- Slack snippet upload ([[sv-whitespace-slack-snippet]]).
- Terminal write / read pipelines that don't invoke a normalizer.

## Detection

- Trivial: `grep -P '[ \t]$'` on the file.
- `text_core.detect_unicode_steg` includes trailing-whitespace scan.
- A visible pattern in any editor with "show whitespace" turned on.

## Sources

- [[morkovkin-snow]] — Matthew Kwan's original SNOW paper (1998)
- [[st3gg-field-guide]] — ST3GG-specific framing
