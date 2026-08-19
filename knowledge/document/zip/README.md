# ZIP archive steganography

ZIP archives carry several payload slots the extraction path never
touches: archive-level comment (up to 65 KB), inter-entry slack
space, and per-entry extra fields.

## What ST3GG implements

`document-zip-comment` — see [[document-zip-comment]]. Full
zip-object tooling isn't in-repo; use standard `zipfile` /
`zip -c` / hex tools.

## Where the bytes hide

- **Archive-level comment** — up to 65535 bytes, stored in the
  End-Of-Central-Directory record. `unzip -z <file>` shows it;
  `unzip file` never touches it.
- **Inter-entry slack** — bytes between the local file header of one
  entry and the local file header of the next. No spec limit; no
  extractor addresses them.
- **EOCD comment** — the archive comment (same as archive-level).
- **Per-entry extra field** — up to 65535 bytes per entry, structured
  as `[header_id][size][data]...`. Most tools ignore unknown IDs.
- **Password-protected entries with dummy passwords** — the
  encrypted stream is opaque; some tools store extra data in that
  region.

## Why ZIP scans from END

The EOCD record magic `50 4B 05 06` appears near the end of every
ZIP. Extractors scan backward from EOF looking for it. Anything
before it — including a whole other file's worth of bytes — is
tolerated (this is why PNG-in-ZIP polyglots work; see
[[image/polyglots]]).

## Where it survives

- **HTTP raw, GitHub, email attachment**: byte-identical.

## Where it dies

- **ZIP re-serializers**: `zip -F` (fix), `zip -U` (update), any
  path that reads all entries and rewrites the archive. Strips
  archive comments, inter-entry slack, unknown extra fields.

## Detection

- `unzip -z <file>` shows the archive comment.
- `zipdetails` shows every structural field.
- File-size vs sum-of-entry-sizes mismatch signals slack.
- `strings <file>` catches ASCII payloads.

## Sources

- APPNOTE.TXT — PKWARE's ZIP file format spec
- [[albertini-polyglots]] — ZIP + other-format polyglots
- [[st3gg-field-guide]] — ST3GG-specific tooling
