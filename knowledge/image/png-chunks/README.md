# PNG chunk-injection steganography

PNG files are a chain of chunks: `[length][type][data][CRC]` repeated
until `IEND`. Text metadata chunks (`tEXt`, `iTXt`, `zTXt`) and
*private* chunks (any 4-char name with the private-chunk convention
bit set) are wide-open smuggling slots.

## What the ST3GG implementation does

Two related techniques:

- `img_core.inject_text_chunk / inject_itxt_chunk` — see
  [[image-png-text-chunk]].
- `img_core.inject_private_chunk` — see [[image-png-private-chunk]].

`stegg_read_png_chunks` iterates every chunk with byte offset and
CRC status.

## The chunk taxonomy

Per [[rfc-2083-png]]:

- **Critical chunks** (uppercase first letter): IHDR, IDAT, PLTE, IEND.
  Required for decode; not steg carriers.
- **Ancillary chunks** (lowercase first letter): text (tEXt, zTXt,
  iTXt), gamma (gAMA), palette histograms (hIST), physical dims
  (pHYs), background (bKGD), suggested palette (sPLT), significant
  bits (sBIT), time (tIME), and application-specific extras.
- **Public** vs **private** — signaled by the *second* letter's case.
  Public means "standardized in an ISO registry"; private means
  "application-defined, avoid name collisions with public chunks."

Named text chunks (tEXt/iTXt/zTXt) are public ancillary chunks. The
`stEg` custom chunk (private ancillary) uses a private lowercase-
second-letter name to signal "don't standardize me."

## What survives what

- **Slack upload**: strips named text chunks (tEXt/iTXt/zTXt) but
  preserves private chunks. See
  [[sv-png-textchunk-slack-upload]] (❌) and
  [[sv-png-private-chunk-slack-upload]] (✅) and
  [[myth-slack-preserves-metadata]].
- **GitHub / HTTP raw / email attachment**: byte-identical, every
  chunk survives.
- **WhatsApp photo / Telegram photo**: JPEG-recodes PNGs on the
  photo path, destroying every chunk. Use the file-attachment path.
- **iMessage attachment**: byte-identical.

## Trailing bytes past IEND

Distinct technique — see [[image/trailing-bytes]].

## Detection

- `stegg_read_png_chunks` lists every chunk with byte offset and CRC.
- `pngcheck -v` or `pngmeta` at the CLI.
- Trivial to notice; not stealth. But *extremely common* in real
  CTFs — hiders often skip the LSB step and just drop a `tEXt` chunk.

## Sources

- [[rfc-2083-png]] — the PNG spec
- [[st3gg-field-guide]] — ST3GG-specific framing
- [[st3gg-transport-results-slack]] — 2026-07 Slack chunk-strip probe
