# Document steganography

Payload hidden inside document containers — PDF, ZIP, SQLite,
office formats. Layer here is almost always [[layer-container]].

## PDF

- **Metadata streams** — Info dict, XMP metadata, custom entries.
- **Post-EOF bytes** — anything after `%%EOF` is ignored by the
  parser but preserved by cat-of-file.
- **Incremental updates** — appended cross-reference tables + new
  objects. Unlinked entries are payload channels.
- **Object streams** — hide inside PDF stream contents (encrypted
  or compressed).

See [[iso-32000-pdf]] for the spec.

## ZIP

- **Slack space** in the central directory.
- **Extra fields** on each local file header.
- **Archive comment** field (up to 65535 bytes).
- **Spanned-archive tricks** — non-first parts that never resolve.

## SQLite

- Unallocated pages between the freelist and used pages.
- WAL / journal files carrying pre-checkpoint state.

## Polyglots

[[image-polyglot]] applies here too. PDF+ZIP, PDF+ELF, JPEG+PDF —
see Ange Albertini's canon ([[albertini-polyglots]]) for the pattern
catalog.

## Not implemented in ST3GG

The current codebase has [[image-polyglot]] for PNG+ZIP and PDF
support via `pdf_core`, but the deeper PDF/ZIP/SQLite techniques are
knowledge-only, not yet encoders. This README is a roadmap.
