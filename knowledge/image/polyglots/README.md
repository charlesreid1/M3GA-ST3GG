# File-format polyglots

A file that parses as TWO (or more) formats. PNG-in-ZIP is the
canonical: same bytes, PNG parser sees an image, unzip sees an
archive. Ange Albertini's catalog is the reference corpus.

## What the ST3GG implementation does

`img_core.polyglot_png_zip_encode / polyglot_zip_png_encode` — the
two orderings for the PNG+ZIP polyglot. See [[image-polyglot]].

Other polyglot builders live in the docs but aren't shipped as
`img_core` builders; hand-authored per the artifact.

## Why polyglots work

Different formats scan from different starting offsets:

- **PNG** starts at byte 0 with the `89 50 4E 47 0D 0A 1A 0A` magic.
  Chunks flow linearly to `IEND`. Bytes after `IEND` are
  unreachable by a strict PNG parser.
- **JPEG** starts at byte 0 with `FF D8`. Ends at `FF D9`.
- **ZIP** scans from the END of the file for the End Of Central
  Directory (EOCD) record — magic `50 4B 05 06`. Whatever precedes
  EOCD (including a whole PNG) is fine.
- **PDF** accepts up to 1024 bytes of garbage BEFORE the `%PDF-`
  header. That's the widest permissive slot.
- **ELF** starts at byte 0 with `7F 45 4C 46`; ignores trailing
  garbage.

Two parsers reading in opposite directions is the whole trick.

## Where it dies

- **Any transport that re-serializes just one of the containers**
  (JPEG re-encoder on WhatsApp photo destroys the JPEG side; a
  ZIP recompressor destroys the ZIP side).
- **Some CDNs**: aggressive content-type sniffers detect polyglots
  and strip the offending trailer.

## Where it survives

- Byte-identical file transports (email attachment, GitHub blob,
  HTTP raw).

## Canonical examples

- **PNG + ZIP** (`img_core.polyglot_png_zip_encode`)
- **JPEG + ZIP** (append ZIP after FF D9)
- **PDF + ZIP** ("Zip inside a PDF" — the `%%EOF` and EOCD tricks)
- **PDF + JAR** (the JAR is a ZIP)
- **HTML + JS + XSS-in-comment polyglots** — cross-parser web
  vulnerabilities
- **PDF + ELF** — the PoC||GTFO 0x08 issue famously

## Constraints

Polyglot construction is bounded by per-format offset rules. See
[[myth-polyglot-order]] — order is a HARD constraint, not a free
variable. PNG must be first byte 0; ZIP must be last EOCD.

## Detection

- `binwalk` scans for embedded magic bytes and finds every embedded
  format.
- `stegg_carve` tries every format decoder on the same bytes and
  reports which parsed.
- File-size mismatch: PNG says 12 KB, file is 400 KB → almost
  certainly a polyglot.

## Sources

- [[albertini-polyglots]] — Ange Albertini's catalog
- PoC||GTFO — the polyglot canon; each issue is itself a polyglot
- [[st3gg-field-guide]] — ST3GG-specific builders
