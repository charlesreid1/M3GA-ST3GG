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

Four docs, four audiences. Don't conflate them — a fact should live where its audience will read it, and cross-link the rest.

| Doc | Audience | When read | Discovered via |
| --- | --- | --- | --- |
| `AGENTS.md` | Agent modifying this repo | Once, at session start after `cd` | Convention (auto-read by Claude Code etc.) |
| `skills/*/SKILL.md` | The MCP host's skill picker, before touching the repo | Skill-selection time, from a global listing | Host's skill dir (`~/.claude/skills/`, plugin skills), matched by `description:` frontmatter |
| `skills/stegg-stego/REFERENCE.md` | Agent that already selected `stegg-stego` and needs full tool specs | On-demand, when SKILL.md says "see REFERENCE" | Linked from SKILL.md |
| `st3ggmcp/field_guide.md` | Agent about to analyze a file with the MCP tools | On-demand, fetched mid-turn | MCP resource `stegg://field-guide` |

Rule: `AGENTS.md` owns repo layout + install + entry-point framing. `SKILL.md` owns when-to-fire triggers + tool-selection heuristics. `REFERENCE.md` owns per-tool specs. `field_guide.md` owns the analyst persona + technique catalog. Overlap is fine when audiences differ; contradiction is a bug.

## Field guide

`st3ggmcp/field_guide.md` — the ST3GG analyst persona, technique catalog, signal-reading heuristics, verdict semantics, transport-survival tables. Read this before analyzing a suspicious file. Also served as MCP resource `stegg://field-guide`.

`st3ggmcp/TRANSPORT_MATRIX.md` — which techniques survive which delivery channels (Slack, terminal stdout, JPEG re-encode, etc.).

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
  - `tools/` — per-family tool modules (`image`, `text`, `triage`, `network`, `jailbreak`, `meta`), each colocating executors with their JSON schemas
  - `field_guide.md`, `TRANSPORT_MATRIX.md` — persona + delivery-channel notes
- `skills/stegg-cli/`, `skills/stegg-stego/` — agent skill definitions
- `index.html` — browser Text Lab + F5 JPEG (legacy, frozen)
- `tests/` — pytest suite (image round-trips, text detectors, cross-language fixtures)
- `examples/` — pre-encoded fixtures

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
