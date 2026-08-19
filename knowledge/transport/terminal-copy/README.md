# Terminal / clipboard — the visible-glyph vs byte-stream split

Two adjacent transports with opposite canonical forms:

- **Terminal mouse-copy** (`transport-terminal-stdout`): canonical
  form is the visible glyph stream. Zero-width, VS, combining marks,
  and other invisible-format characters get dropped.
- **`pbcopy` / `xclip` / `clip.exe`** ([[transport-pbcopy]]): canonical
  form is the byte stream. Everything survives.

## Where things dies (terminal mouse-copy)

- [[text-zero-width]] — dropped. See [[sv-zero-width-terminal-stdout]].
- [[text-variation]] — dropped. See [[myth-vs-terminal]].
- [[text-combining]] — dropped (mostly).
- [[text-invisible-ink]] — dropped.
- [[text-hangul]] — Hangul filler dropped on some terminals.

## Where things survive (terminal mouse-copy)

- [[text-cyrillic-homoglyph]] — Cyrillic letters render, get copied.
- [[text-cjk-homoglyph]] — fullwidth punctuation renders, gets
  copied.
- [[text-mathbold]] — mathbold letters render, get copied.
- [[text-braille]] — Braille codepoints render as tiny dot patterns,
  get copied.
- [[text-capitalization]] — case swaps are part of the visible glyphs.

## Where everything survives (pbcopy / xclip / clip.exe)

Byte stream transports bypass the terminal's rendering-and-selection
pipeline entirely. Any technique that round-trips through UTF-8
text survives.

## Practical routing

- **Prompt-injection payloads via terminal history** → use pbcopy.
- **Text stego demo to a colleague on a screen share** → use
  pbcopy or a snippet file transfer, not "select text and copy."
- **Round-trip test through terminal** → always test with pbcopy AND
  with mouse-select; they differ.

## Detection

- No detection needed on the survivor side; if your invisible chars
  arrive intact, the transport preserved them.
- Ask "how did you copy this?" — if the answer is "I selected it
  with the mouse," invisibles are missing.

## Sources

- [[st3gg-transport-matrix]] — the specific cells
- [[st3gg-field-guide]] — canonicalization principle
