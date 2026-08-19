# Discord — upload vs paste

Discord parallels Slack's upload/paste split, but the specifics
(what strips, what preserves) haven't been first-party probed by
ST3GG yet.

## The two sub-transports

- **`discord_upload`** ([[transport-discord-upload]]) — file
  attachment. Canonical form: file bytes served from Discord's CDN.
  Rated *community* confidence — behavior is similar to Slack
  upload (bytes preserved, some metadata stripped) but the exact
  strip list isn't documented and hasn't been probed by us.
- **`discord_paste`** ([[transport-discord-paste]]) — message body.
  Canonical form: rendered post. Emoji get resolved to Discord's
  custom-emoji IDs where applicable; text preserved but with
  markdown parsing.

## Known behaviors

- **Message-body markdown**: Discord parses markdown (`*bold*`,
  ``code``, `~~strike~~`). This changes what "the visible text"
  is, which changes what visible-glyph-stream techniques survive.
- **Uploads have file-size limits** (25 MB free, 500 MB Nitro
  as of last check).
- **Discord CDN often serves images through a proxy** that may
  re-encode for very large images.

## Where things dies (likely)

- Named PNG text chunks — assumed stripped (similar to Slack).
- EXIF/XMP — assumed stripped (privacy default).
- Trailing bytes after IEND — likely stripped on some paths.

## Where things survive (likely)

- PNG IDAT / pixel data — assumed byte-identical.
- Byte-level file transfer for non-image formats.

## Known unknowns

Every one of the "likely" statements above is un-probed. The plan's
next Slack-style probe is Discord; see [[known-unknowns.md]] for
details.

## Sources

- [[st3gg-transport-matrix]] — placeholder cells
- [[st3gg-field-guide]] — canonicalization principle
