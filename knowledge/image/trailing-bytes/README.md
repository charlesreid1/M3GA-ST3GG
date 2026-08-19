# Trailing bytes past IEND / EOI

Payload as raw bytes appended after the container's end marker
(`IEND` for PNG, `FFD9` EOI for JPEG). The dumbest smuggle in
the book and the one that lands most often in real CTFs.

## What the ST3GG implementation does

`img_core` exposes `detect_trailing` (find bytes past the last valid
end marker) and `carve` (peel them out and hand them to
[[document-pdf-post-eof]] / [[document-zip-comment]] / raw-bytes
consumers). See [[image-trailing-bytes]].

## The trick

- **PNG**: readers scan for the `IEND` chunk (magic bytes `49 45 4E 44`
  followed by the CRC32 `AE 42 60 82`) and stop. Bytes after that byte
  sequence are unreachable by normal PNG decode; the file still
  renders the image cleanly.
- **JPEG**: readers scan for `FFD9` (End of Image marker). Same
  story — bytes after `FFD9` are unaddressed.

## Where it dies

- **Any transport that re-serializes the file**: Slack upload
  (`[[sv-trailing-bytes-slack-upload]]` — ❌), WhatsApp photo
  ([[transport-whatsapp-photo]]), Discord upload proxy — most consumer
  messengers re-serialize the file and drop trailing bytes.
- **PDF and other container formats** that scan from EOF backward
  (PDF's `%%EOF` search) — see [[document-pdf-post-eof]]. Different
  technique; distinct record.

## Where it survives

- File-byte-identical transports: HTTP raw, GitHub, email attachment,
  Telegram-as-file, iMessage attachment, Signal attachment.

## Detection

- Trivial: `stegg_detect_trailing` compares file size to end-marker
  offset.
- Any hex viewer scrolling past the end marker.
- `binwalk` recognizes appended file magic bytes.
- `foremost` / `scalpel` carve out embedded formats.

## The classic form: PNG + ZIP polyglot

A PNG followed by a ZIP central directory (which is read from the
end) makes a file that opens as a picture AND unzips to reveal an
archive. That's a *polyglot*, not just trailing bytes — see
[[image/polyglots]]. Trailing bytes is the simpler case where the
appended data isn't itself a valid container.

## Sources

- [[rfc-2083-png]] — PNG end marker (`IEND` + trailing CRC)
- [[itu-t81-jpeg]] — JPEG End of Image
- [[st3gg-field-guide]] — ST3GG detect/carve tooling
- [[st3gg-transport-results-slack]] — the Slack strip evidence
