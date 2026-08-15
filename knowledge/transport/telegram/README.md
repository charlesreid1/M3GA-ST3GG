# Telegram — photo vs file

Telegram has two upload paths with wildly different survival
profiles. Same product, different canonical forms.

## The two sub-transports

- **`telegram_photo`** ([[transport-telegram-photo]]) — canonical
  form: perceptual approximation. Telegram compresses photos on the
  photo path. Destroys LSB, PVD, direct pixel overwrite. Preserves
  visible content only. Rated *community* confidence — we haven't
  first-party probed edge cases like "does photo mode preserve PNG
  when the client detects PNG."
- **`telegram_file`** ([[transport-telegram-file]]) — canonical
  form: file bytes. Byte-identical delivery. Everything survives.

## The routing UI

Telegram's UI defaults to photo mode when you drag-drop an image.
"Send as file" is a separate menu option (or paperclip → "File").
Users often send accidentally as photo when they meant to preserve
the file.

## Where things survive

- **`telegram_file`** — everything (byte-identical).
- **`telegram_photo`** — content-visible payloads only (visible-glyph
  stream analog for images).

## Where things die

- **`telegram_photo`** kills:
  - LSB (image [[image-lsb]])
  - PVD ([[image-pvd]])
  - Direct pixel overwrite
  - DCT-domain hides ([[image-f5]], [[image-jsteg]],
    [[image-outguess]])
  - PNG chunks (Telegram converts to JPEG on the photo path)
  - Trailing bytes

## Known unknowns

- Does Telegram photo mode preserve PNG format if the client
  auto-detects PNG? Undocumented; not first-party probed.
- Which recompression Q table does Telegram use? Unknown per-region.

See [[known-unknowns.md]] for the full list.

## Sources

- [[st3gg-transport-matrix]] — matrix cells + evidence pointers
- [[st3gg-field-guide]] — canonicalization principle
