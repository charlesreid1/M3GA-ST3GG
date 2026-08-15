# Image metadata (EXIF / XMP / IPTC / ICC / tEXt) steganography

Payload smuggled through the metadata slots defined by image format
specs. Sibling of [[image/png-chunks]] with a wider view: EXIF and
XMP are format-independent metadata standards that live in JPEG,
TIFF, HEIC, PNG, and more.

## What the ST3GG implementation does

`img_core` exposes `stegg_read_metadata` for reading (PNG chunks +
PIL image.info + EXIF/XMP/IPTC via optional `stegg[metadata]` extra).
Direct write-side helpers live in the format-specific tools:

- PNG text chunks — see [[image/png-chunks]] and
  [[image-png-text-chunk]].
- JPEG EXIF / XMP / IPTC — writable via `piexif` or `exiftool`
  (external binary; capability-check first).

## The metadata slot catalog

- **EXIF** — Exchangeable Image File Format. Camera metadata:
  make, model, GPS, timestamps, thumbnail. Wide payload capacity via
  user comment (`0x9286`), maker note (`0x927C`), and image
  description tags.
- **XMP** — Adobe's Extensible Metadata Platform. RDF/XML embedded as
  an APP1 segment (JPEG), an iTXt chunk (PNG), or a standalone
  packet. Effectively unbounded payload.
- **IPTC** — International Press Telecommunications Council photo
  metadata. Older, byline/caption fields. Shorter capacity slots.
- **ICC** — color profile data. Not usually a payload channel (parsers
  validate ICC structure) but binary blobs of tens of KB are legal.
- **PNG tEXt / zTXt / iTXt** — see [[image/png-chunks]].
- **JPEG COM segment** (`FFFE`) — free-form comment marker,
  ignored by decoders.

## Where it dies

Consumer messengers strip metadata aggressively by default:

- **Slack upload** ❌ strips EXIF/XMP/IPTC and named PNG text chunks
  (see [[myth-slack-preserves-metadata]] and
  [[st3gg-transport-results-slack]]).
- **WhatsApp photo** ❌ strips everything (privacy default).
- **Signal attachment** ❌ strips EXIF.
- **iMessage photo** ❌ often strips (HEIC transcode also destroys).
- **Discord upload** ❌ strips EXIF.
- **Instagram / Twitter / most social media** ❌ strip EXIF for
  privacy.

See [[myth-metadata-survives-anywhere]].

## Where it survives

- **HTTP raw / GitHub blob / email attachment**: byte-identical, all
  metadata survives. See [[myth-github-strips-exif]].
- **Telegram-as-file** (not photo): file-byte transport.
- **iMessage attachment** (not photo): file-byte transport.

## Detection

- `stegg_read_metadata` dumps every slot.
- `exiftool -a -G -u <file>` shows every EXIF/XMP/IPTC/ICC tag.
- `strings` catches raw text embeds.
- Any modern DFIR toolkit lists metadata as a first-pass check.

## Note on private chunks

PNG's private-chunk convention (see [[image-png-private-chunk]]) is
a metadata-adjacent smuggle that survives Slack's named-chunk
stripper. Not spec'd as metadata but functionally equivalent for
payload purposes.

## Sources

- [[rfc-2083-png]] — PNG chunks
- [[itu-t81-jpeg]] — JPEG APPn segments
- EXIF 2.32 spec (via CIPA DC-008-2019)
- XMP Specification (Adobe, 2012)
- [[st3gg-field-guide]] — ST3GG-specific metadata routing
