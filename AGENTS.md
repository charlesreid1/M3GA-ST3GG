# AGENTS.md

Guide for coding agents dropped into this repo. Short intentionally — for depth, follow the pointers.

## What this is

ST3GG is a steganography toolkit covering three carrier families as equal peers: **image** (PNG/JPEG/BMP LSB, chunk smuggling, metadata, polyglots), **text** (zero-width, cyrillic_homoglyph, cjk_homoglyph, whitespace, and eleven others), and **emoji** (substitution, skin-tone modifiers, braille block, variation selectors). Python core + CLI, browser-side Text Lab (`index.html`), plus two agent entry points.

## Two agent entry points

Both wrap the same underlying library (`img_core`, `text_core`, `analysis_tools`, `transforms_core`, `crypto`). Pick one:

### `stegg --json` — subprocess CLI
Skill: `skills/stegg-cli/SKILL.md`. Invoke as `stegg --json <command>`. JSON output. **Prefer this for routine encode/decode/analyze** — output stays out of LLM context.

### `stegg-mcp` — HTTP MCP server
Skill: `skills/stegg-stego/SKILL.md`. Reference: `skills/stegg-stego/REFERENCE.md`. Package: `st3ggmcp/`. Streamable HTTP on `:8765/mcp`. **Use this when you want to reason over results inline**, chain tools with LLM judgment between steps, or need the `stegg://field-guide` resource loaded.

Rule of thumb: `stegg --json` for context hygiene, MCP for inline reasoning.

## Docs map

Five docs, five audiences. Don't conflate them — a fact should live where its audience will read it, and cross-link the rest.

| Doc | Audience | When read | Discovered via |
| --- | --- | --- | --- |
| `AGENTS.md` | Agent modifying this repo | Once, at session start after `cd` | Convention (auto-read by Claude Code etc.) |
| `skills/*/SKILL.md` | The MCP host's skill picker, before touching the repo | Skill-selection time, from a global listing | Host's skill dir (`~/.claude/skills/`, plugin skills), matched by `description:` frontmatter |
| `skills/stegg-stego/REFERENCE.md` | Agent that already selected `stegg-stego` and needs full tool specs | On-demand, when SKILL.md says "see REFERENCE" | Linked from SKILL.md |
| `st3ggmcp/field_guide.md` | Agent about to analyze a file with the MCP tools | On-demand, fetched mid-turn | MCP resource `stegg://field-guide` |
| `knowledge/**/*.md` + `knowledge/records/*.json` | Agent that needs a cited number, a technique record, or a transport-survival cell | On-demand, mid-turn, via `stegg_lookup_*` / `stegg_verify_*` / `stegg://<topic>/<name>` | Retrieval tools (`stegg_list_topics`, `stegg_read_lore`, `stegg_lookup_technique`, `stegg_verify_survival`, ...) + MCP resources |

Rule: `AGENTS.md` owns repo layout + install + entry-point framing. `SKILL.md` owns when-to-fire triggers + tool-selection heuristics. `REFERENCE.md` owns per-tool specs. `field_guide.md` owns the analyst *persona* and dispatch/verdict *heuristics* — it is intentionally light on catalog data. The knowledge base owns cited numeric facts (records) and split-per-topic prose (technique catalog, capacity formulas, transport-survival cells, pattern-diagnosis snippets, myth refutations). Overlap is fine when audiences differ; contradiction is a bug — when the field guide and a record disagree, the record wins (records are load-time-validated and cited; the field guide is voice).

## Field guide

`st3ggmcp/field_guide.md` — persona layers (Bender / ST3GG overlay / AND!XOR analyst), the five-mode gate, image + text dispatch tables, verdict semantics (`*FOUND*` / `*NOTHING*` / `*INCONCLUSIVE*`), and response-format rules. Reads under 300 lines. Also served as MCP resource `stegg://field-guide`.

**What used to live here but doesn't anymore** — technique catalog, per-method framing, transport-survival tables, and pattern-diagnosis snippets migrated into the KR during the Tier-1 fill. If you need a technique's numbers, call `stegg_lookup_technique`; for a (technique, transport) cell call `stegg_verify_survival`; for signal-pattern snippets `stegg_search_records(category="signature")`.

`st3ggmcp/TRANSPORT_MATRIX.md` — the transport survival scoreboard. The technique × transport table is **generated** from `knowledge/records/survival.json` by `scripts/render_transport_matrix.py` (fenced by `<!-- BEGIN autogen: transport matrix -->`). The Slack mechanism-notes prose around it is hand-authored. CI guards drift via `tests/unit/test_transport_matrix_autogen.py` — edit `survival.json`, then run `python scripts/render_transport_matrix.py --write`.

## Knowledge base

`knowledge/` — two-layer corpus modeled on PHR34CKER5's split:

- `knowledge/records/*.json` — typed KR, one file per category: `bibliography`, `techniques`, `carrier_formats`, `layers`, `transports`, `survival`, `detectors`, `signatures`, `myths`, `capacity_models`, `external_tools`, `ctf_genres`. Every record has a mandatory envelope (`id`, `name`, `aliases`, `category`, `carrier_family`, `layer`, `era_bounds`, `confidence`, `citations`, `see_also`, `disputed`, `technical_body`). Load-time validation is strict — empty `citations[]` or an unresolved bibliography id raises `RecordError` and the MCP server won't boot. Loaded by `st3ggmcp/records.py`; served by `st3ggmcp/tools/knowledge.py` as `stegg_lookup_technique` / `stegg_verify_survival` / `stegg_verify_claim` / `stegg_explain_pipeline` / `stegg_bibliography` / `stegg_cross_reference` / `stegg_search_records`.
- `knowledge/<topic>/**/*.md` — prose corpus, one idea per file. Topic-level `README.md` orients; per-technique subdirectories (e.g. `image/lsb/`, `image/f5/`, `text/zero-width/`, `text/homoglyph-cyrillic/`) split into `README` / `reference` / `walkthrough` / `recognition` as the material demands. The MCP resource walker is depth-agnostic — every markdown file under `knowledge/<topic>/` is exposed at `stegg://<topic>/<name>` (where `<name>` may include subdirectory segments) and searchable via `stegg_list_topics` / `stegg_read_lore` / `stegg_search_lore`.
- `knowledge/known-unknowns.md` — running audit of every claim ST3GG *acts on* that isn't yet tied to a primary source or a first-party measurement. Read before adding a thin-provenance record; add to it whenever you notice a claim in the field guide or KR that can't be cited.

Design + discipline: `knowledge/MANIFEST.md`. Motivation and the tier-by-tier fill order: `plan-knowledge-base.md`.

## Jailbreak / transforms

`jailbreak_core.py` composes multi-vector prompt-injection payloads — Unicode Tag smuggling (the 2025 "hidden emoji" technique), text-stego-wrapped templates with optional transform pre-pipelines from `transforms_core`, and full image jailbreaks (LSB payload + matching PNG metadata + injection filename). It also exposes the detection sweep that pairs with them.

Framing, consistent with the field guide: this tooling is for **CTFs, DEF CON challenges, hardware badges, authorized red-team ops, detection-tuning, and forensic research**. The composers exist because those particular pipelines (obfuscation chain + text stego + optional image wrap) are common enough to standardize; the detectors exist so blue teams can see them. Skills that describe these tools should carry the same framing sentence rather than inventing new phrasing.

## Repo layout

- `img_core.py` — image LSB encode/decode + config + capacity math
- `text_core.py` — text/emoji encode/decode (14 methods)
- `analysis_tools.py` — 264+ detection/analysis functions
- `transforms_core.py` — pure text transforms (zalgo, leetspeak, fullwidth) for pre-obfuscation
- `crypto.py` — optional AES-256-GCM
- `cli.py` — main CLI (Rich TUI by default; `--json` for machine-readable output)
- `operations.py` — shared operation layer (file I/O + validation + core calls)
- `webui.py` — optional NiceGUI UI
- `st3ggmcp/` — HTTP MCP server package
  - `server.py` — ASGI app + entry point
  - `records.py` — typed-record loader with strict load-time validation (empty `citations[]` or unresolved bib id = `RecordError`)
  - `tools/` — per-family tool modules (`image`, `text`, `triage`, `network`, `jailbreak`, `knowledge`, `meta`), each colocating executors with their JSON schemas
  - `field_guide.md` — persona + heuristics + mode gate + response format (technical catalog lives in the KR, not here)
  - `TRANSPORT_MATRIX.md` — transport survival table; the matrix is autogenerated from `knowledge/records/survival.json`
- `knowledge/` — two-layer corpus (typed KR + prose corpus). See "Knowledge base" above.
- `scripts/` — doc-generation helpers (`render_skill_tool_index.py` syncs `skills/*.md` tool tables to `TOOL_SCHEMAS`; `render_transport_matrix.py` regenerates `TRANSPORT_MATRIX.md` from `survival.json`). Both are guarded by CI tests under `tests/unit/`.
- `skills/stegg-cli/`, `skills/stegg-stego/` — agent skill definitions
- `index.html` — browser Text Lab + F5 JPEG (legacy, frozen)
- `tests/` — pytest suite (image round-trips, text detectors, cross-language fixtures, KR gold-standard Q/A + adversarial traps)
- `examples/` — pre-encoded fixtures
- `plan-knowledge-base.md` — motivation + tiered fill plan for the KR

## Install

```bash
pip install -e .              # core CLI
pip install -e '.[mcp]'       # + HTTP MCP server
pip install -e '.[all]'       # everything (web, crypto, MCP)
```

### Install the skills

Claude Code's skill listing scans `~/.claude/skills/` (plus plugin skills), not arbitrary in-repo folders — so cloning the repo does not by itself make `stegg-cli` / `stegg-stego` selectable. Symlink them into place once:

```bash
mkdir -p ~/.claude/skills
ln -s "$(pwd)/skills/stegg-cli"   ~/.claude/skills/stegg-cli
ln -s "$(pwd)/skills/stegg-stego" ~/.claude/skills/stegg-stego
```

Symlinks (vs. copies) mean edits to `SKILL.md` / `REFERENCE.md` in the repo are picked up immediately — no reinstall. Verify by triggering a keyword from the skill's `description:` frontmatter (e.g. "analyze this PNG for hidden data") and confirming the host loads the skill.

## Tests

```bash
pytest -q
pytest -q -m "not slow"       # skip round-trip sweeps
```

Markers: `slow`, `crypto`, `pipeline`, `regenerates_examples`. `regenerates_examples` writes under `examples/pipelines/` — don't run casually.

## Ground rules

- Text and emoji are first-class carriers, not afterthoughts. Any change that assumes "steg == image LSB" is wrong.
- Detection has real failure modes. `stegg_triage` verdicts encode this — HIGH severity requires corroboration across multiple probes; a single-probe hit is MEDIUM at best.
- No auth on the MCP server. Container-to-container use only.
- Don't rename `st3ggmcp` casually — it's wired into `pyproject.toml` entry points and the `skills/stegg-stego/` skill.
