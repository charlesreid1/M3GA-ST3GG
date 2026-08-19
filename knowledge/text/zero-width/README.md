# Text zero-width steganography

Payload as a run of invisible Unicode codepoints appended to (or
bracketed inside) a normal-looking cover string. The most common
"invisible payload in text" technique.

## What the ST3GG implementation does

`text_core.encode_zero_width / text_core.decode_zero_width`. See
[[text-zero-width]] and [[cap-text-zero-width]].

Alphabet:

- `U+200B` ZWSP (zero-width space) → bit 0
- `U+200C` ZWNJ (zero-width non-joiner) → bit 1
- `U+200D` ZWJ (zero-width joiner) → start/end marker

Framing: `[ZWJ] [payload bits as ZWSP/ZWNJ codepoints] [ZWJ]`.

## The four questions

- **What is this?** → this README.
- **How do the numbers work?** → [[text/zero-width/reference]] — the
  codepoint table, capacity, framing bytes, how UTF-8 encodes each
  codepoint.
- **What does an end-to-end run look like?** → [[text/zero-width/walkthrough]] —
  a 32-byte payload appended to a 3-line cover, byte-hex trace of the
  output.
- **Is *this text* a zero-width hide?** → [[text/zero-width/recognition]] —
  15-second triage: how a stego string looks in a hex viewer, in a
  chat client, and to Python's `.encode('utf-8')`.

## Where it dies

- **NFKC normalization**: not directly — zero-width codepoints are NOT
  normalized away by NFKC — but the surrounding text often is, breaking
  the alignment for delimiter-based schemes. Zero-width itself survives
  NFC/NFKC.
- **Terminal glyph filtering**: many terminals strip invisibles from the
  mouse-copy path. See [[sv-zero-width-terminal-stdout]] — workaround is
  `pbcopy` / `xclip` / `clip.exe`.
- **Aggressive input sanitizers**: some search boxes, some form
  validators, some LLM tokenizer preprocessors strip zero-width chars.
- **Slack message body paste**: zero-width survives on paste (see
  [[sv-zero-width-slack-paste]]). Also survives snippet
  ([[sv-zero-width-slack-snippet]]).

## Where it survives

- Any UTF-8-preserving pipeline: paste into a chat client, save to disk,
  upload as `.txt`, send via HTTP. See [[sv-text-http-raw]].
- Copy/paste between rich-text UIs (Slack, Discord, Google Docs) —
  usually preserved intact.

## Detection

- **[[det-bit-plane-entropy]]** doesn't apply to text.
- Byte-level detection: `text_core.detect_unicode_steg` — scans for
  ZWSP/ZWNJ runs longer than natural text ever produces (>3 in a row).
  Zero-width chars have legitimate uses (word-joiner in Indic scripts,
  emoji ZWJ sequences) but never as unbroken sequences of tens of
  codepoints.

## Sources

- [[rfc-3629-utf8]] — UTF-8 spec
- [[unicode-tr36-security]] — Unicode Technical Report on security
  implications (zero-width chars in phishing)
- [[st3gg-field-guide]] — ST3GG-specific framing
