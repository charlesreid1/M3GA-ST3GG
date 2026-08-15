# WhatsApp — photo vs document

Same dual-path story as Telegram. Photo mode is perceptual-
approximation; document mode is file-bytes.

## The two sub-transports

- **`whatsapp_photo`** ([[transport-whatsapp-photo]]) — canonical
  form: perceptual approximation. Aggressive JPEG recompression on
  the photo path. Kills every pixel-domain hide.
- **`whatsapp_document`** ([[transport-whatsapp-document]]) —
  canonical form: file bytes. Byte-identical for most formats.

## Where things survive

- **`whatsapp_document`** — pass-through for most formats. Text stego,
  file trailing bytes, ZIP comments, PDF hides all survive.
- **`whatsapp_photo`** — visible content only.

## Where things die

- **`whatsapp_photo`** destroys:
  - Image LSB, PVD, direct pixel overwrite (aggressive JPEG recode).
  - Metadata (EXIF/XMP/IPTC stripped for privacy).
  - PNG chunks (photos are converted to JPEG).
  - Trailing bytes past IEND / EOI.
  - DCT-domain hides in most cases.

## Confidence notes

The photo-path destruction is well-known but ST3GG's own probe hasn't
run — we cite [[myth-metadata-survives-anywhere]] and community
sources. First-party WhatsApp probe is a known unknown; see
[[known-unknowns.md]].

## Sources

- [[st3gg-transport-matrix]] — matrix cells
- [[st3gg-field-guide]] — canonicalization principle
