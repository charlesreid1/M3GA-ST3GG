# SQLite database steganography

Payload as bytes on unallocated pages, in the freelist, or in
rollback-journal / WAL leftover regions. Invisible to SQL queries;
visible to any forensic tool that reads the raw page structure.

## What ST3GG implements

`document-sqlite-slack` — see [[document-sqlite-slack]]. Reading
requires the SQLite file format parser; no in-repo helper (yet).

## Where the bytes hide

SQLite databases are page-organized (typical page size 4096 B).

- **Freelist pages** — pages that used to hold data but were freed
  by `DELETE`. Their content survives until `VACUUM`.
- **Rollback journal (`*.db-journal`)** — pages the DB was about to
  overwrite. Sits next to the .db file until committed or rolled
  back.
- **WAL file (`*.db-wal`)** — write-ahead log frames. Contains
  pages waiting to be checkpointed into the main DB.
- **Reserved page space** — at the end of every page, SQLite can
  reserve N bytes (usually 0) via the `PRAGMA reserved_bytes`
  mechanism.
- **B-tree slack** — space between the end of used B-tree entries
  and the start of the cell content area, per page.

## The hide procedure

1. Insert dummy rows to allocate pages.
2. `DELETE` them (freelist reclaim).
3. Overwrite the freed page bytes with payload (direct file I/O
   after closing the DB).
4. Ship the .db file (byte-identical) to the receiver.
5. Receiver opens the file raw, walks freelist pages, extracts
   payload.

Alternative: don't delete anything, just write payload into the
reserved-page-bytes region at each page's tail — needs `PRAGMA
reserved_bytes` set at DB creation.

## Where it survives

- **Byte-identical .db transports**: HTTP raw, GitHub, email.
- **SQL queries** all ignore freelist and reserved bytes.

## Where it dies

- **`VACUUM`** rebuilds the DB and drops freelist content.
- **`.dump | .read`** round-trip through SQL text and produces a
  clean DB.
- **iCloud / Google Drive sync sometimes rewrites**: depends on the
  syncer.

## Detection

- SQLite forensic tools (Sanderson SQLite Forensic Explorer, Cellebrite,
  `sqlparse` + hexdump).
- `strings <file>.db` catches ASCII payloads.
- `sqlite3 <file> VACUUM` followed by size comparison flags large
  slack payloads.

## Sources

- SQLite file format documentation (sqlite.org)
- [[st3gg-field-guide]] — ST3GG-specific tooling
