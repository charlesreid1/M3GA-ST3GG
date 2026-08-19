# ST3GG knowledge base — manifest

Two-layer corpus, modeled directly on PHR34CKER5's split. See
`../plan-knowledge-base.md` for the design.

- **`records/`** — typed KR: JSON arrays with a mandatory envelope
  (`id`, `name`, `aliases`, `category`, `carrier_family`, `layer`,
  `era_bounds`, `confidence`, `citations`, `see_also`, `disputed`,
  `technical_body`). Every citation must resolve into `bibliography.json`
  or startup fails. This is what the `stegg_lookup_*` / `stegg_verify_*`
  tools read.
- **Topic directories** — prose corpus. One idea per file. Each topic
  starts with `README.md` (orient) and can drill down with per-technique
  subdirectories that carry a `README` + `reference` + `walkthrough` +
  `recognition` split (e.g. `image/lsb/reference.md`,
  `text/zero-width/walkthrough.md`).

  As of this doc, topic READMEs live under `image/`, `text/`, `emoji/`,
  `audio/`, `network/`, `document/`, `detection/`, `transport/`,
  `crypto/`, `ctf/`, `history/`, and `glossary/`. Per-technique deep
  splits exist under `image/lsb/`, `image/f5/`, `text/zero-width/`,
  and `text/homoglyph-cyrillic/`; every other technique named in the
  plan has an orient README under its topic dir.

  Every markdown file is exposed as an MCP resource at
  `stegg://<topic>/<name>`. The walker is depth-agnostic: subdirectory
  files land at `stegg://<topic>/<subtopic>/<file>` (name segment can
  contain slashes).

## Discipline

- **Numbers not adjectives.** "Roughly 1 bpp" is a defect;
  `bits_per_carrier_unit=1, header=v3, prefix="16-bit LE length"` is a
  record.
- **Disputes are first-class.** Carry conflicting values with provenance
  in `disputed{}`. `stegg_verify_claim` returns `needs_qualification`
  rather than silently picking a side.
- **Prose ↔ records cross-reference.** `[[topic/name]]` links in prose,
  `see_also[]` in records. The four-file split per topic maps 1:1 to
  the four questions the assistant asks: README → what, reference →
  params, walkthrough → what does it look like end-to-end, recognition
  → is *this* an example.

## Known unknowns

`known-unknowns.md` at this directory's root enumerates every claim
ST3GG acts on that isn't yet tied to a primary source or a first-party
measurement. Read it before adding a record whose provenance is thin —
you may already know the fix.

## Packaging

This directory is force-included into the wheel as
`m3gast3gg._knowledge` (see `pyproject.toml`). Adding a new record or
prose file requires no packaging change — the loader resolves it either
from the source tree (dev) or from the installed package data (wheel).

## Adding a record

1. Author the entry in the correct `records/*.json` category file.
2. Every fact needs a `citations[]` entry that resolves into
   `bibliography.json` — add the source there first if needed.
3. Fill `era_bounds` even if it's `[YYYY-MM-DD, null]`. Techniques get
   deprecated, transports canonicalize differently over time, CVEs
   land. Date every record.
4. Restart the MCP server (or the ST3GG runtime) — records are
   validated at load time; a missing citation is a startup error, not
   a runtime warning.
