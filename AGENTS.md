# AGENTS.md

Guide for coding agents dropped into this repo. Short intentionally — for depth, follow the pointers.

## What this is

ST3GG is a steganography toolkit covering three carrier families as equal peers: **image** (PNG/JPEG/BMP LSB, chunk smuggling, metadata, polyglots), **text** (zero-width, cyrillic_homoglyph, cjk_homoglyph, whitespace, and eleven others), and **emoji** (substitution, skin-tone modifiers, braille block, variation selectors). Python core + CLI, browser-side Text Lab (`web/index.html`), plus two agent entry points.

## Two agent entry points

Both wrap the same underlying library (`m3gast3gg.core.*` — `img`, `text`, `analysis`, `transforms`, `crypto`). Pick one:

### `stegg --json` — subprocess CLI
Skill: `skills/stegg-cli/SKILL.md`. Invoke as `stegg --json <command>`. JSON output. **Prefer this for routine encode/decode/analyze** — output stays out of LLM context.

### `m3gast3gg-mcp` — HTTP MCP server
Skill: `skills/stegg-stego/SKILL.md`. Reference: `skills/stegg-stego/REFERENCE.md`. Package: `m3gast3gg.mcp` (server in `m3gast3gg.server`). Streamable HTTP on `:8765/mcp`; `m3gast3gg-mcp-stdio` for stdio transport. **Use this when you want to reason over results inline**, chain tools with LLM judgment between steps, or need the `stegg://field-guide` resource loaded.

Rule of thumb: `stegg --json` for context hygiene, MCP for inline reasoning.

## Docs map

Four docs, four audiences. Don't conflate them — a fact should live where its audience will read it, and cross-link the rest.

| Doc | Audience | When read | Discovered via |
| --- | --- | --- | --- |
| `AGENTS.md` | Agent modifying this repo | Once, at session start after `cd` | Convention (auto-read by Claude Code etc.) |
| `skills/*/SKILL.md` | The MCP host's skill picker, before touching the repo | Skill-selection time, from a global listing | Host's skill dir (`~/.claude/skills/`, plugin skills), matched by `description:` frontmatter |
| `skills/stegg-stego/REFERENCE.md` | Agent that already selected `stegg-stego` and needs full tool specs | On-demand, when SKILL.md says "see REFERENCE" | Linked from SKILL.md |
| `src/m3gast3gg/field_guide.md` | Agent about to analyze a file with the MCP tools | On-demand, fetched mid-turn | MCP resource `stegg://field-guide` |

Rule: `AGENTS.md` owns repo layout + install + entry-point framing. `SKILL.md` owns when-to-fire triggers + tool-selection heuristics. `REFERENCE.md` owns per-tool specs. `field_guide.md` owns the analyst persona + technique catalog. Overlap is fine when audiences differ; contradiction is a bug.

## Field guide

`src/m3gast3gg/field_guide.md` — the ST3GG analyst persona, technique catalog, signal-reading heuristics, verdict semantics, transport-survival tables. Read this before analyzing a suspicious file. Also served as MCP resource `stegg://field-guide`.

`src/m3gast3gg/TRANSPORT_MATRIX.md` — which techniques survive which delivery channels (Slack, terminal stdout, JPEG re-encode, etc.).

## Jailbreak / transforms

`m3gast3gg.core.jailbreak` composes multi-vector prompt-injection payloads — Unicode Tag smuggling (the 2025 "hidden emoji" technique), text-stego-wrapped templates with optional transform pre-pipelines from `m3gast3gg.core.transforms`, and full image jailbreaks (LSB payload + matching PNG metadata + injection filename). It also exposes the detection sweep that pairs with them.

Framing, consistent with the field guide: this tooling is for **CTFs, DEF CON challenges, hardware badges, authorized red-team ops, detection-tuning, and forensic research**. The composers exist because those particular pipelines (obfuscation chain + text stego + optional image wrap) are common enough to standardize; the detectors exist so blue teams can see them. Skills that describe these tools should carry the same framing sentence rather than inventing new phrasing.

## Repo layout

Src-layout single package `m3gast3gg` under `src/`. The core steganography library and the MCP server ship together in one wheel.

```
M3GA-ST3GG/
├── src/m3gast3gg/
│   ├── __init__.py
│   ├── __main__.py               # `m3gast3gg-mcp` entry point
│   ├── server.py                 # ASGI MCP app + stdio entry (`main_stdio`)
│   ├── cli.py                    # `stegg` CLI (Rich TUI; `--json` for machine output)
│   ├── field_guide.md            # analyst persona (served as MCP resource `stegg://field-guide`)
│   ├── TRANSPORT_MATRIX.md       # delivery-channel survival notes
│   ├── core/                     # steganography library
│   │   ├── img.py                # image LSB encode/decode + config + capacity math
│   │   ├── text.py               # text/emoji encode/decode (14 methods)
│   │   ├── audio.py, network.py, pdf.py, metadata.py, matryoshka.py, …
│   │   ├── analysis.py           # 264+ detection/analysis functions
│   │   ├── transforms.py         # pure text transforms (zalgo, leetspeak, fullwidth)
│   │   ├── jailbreak.py          # multi-vector prompt-injection composer + detectors
│   │   ├── crypto.py             # optional AES-256-GCM
│   │   ├── operations.py         # shared operation layer (file I/O + validation)
│   │   └── f5/                   # F5 JPEG DCT stego (Python port of the JS reference)
│   ├── mcp/                      # per-family MCP tool modules
│   │   ├── image.py, text.py, network.py, jailbreak.py, meta.py, triage.py
│   │   └── __init__.py           # merges per-family EXECUTORS/SCHEMAS
│   └── webui/                    # optional NiceGUI UI (`stegg-web`, [web] extra)
│
├── tests/                        # pytest suite
├── examples/                     # 100+ pre-encoded fixtures
├── transport_probes/             # delivery-channel probe harness + results
│   └── slack/TRANSPORT_RESULTS_SLACK.json
├── scripts/                      # standalone helpers
├── skills/stegg-cli/, skills/stegg-stego/   # agent skill definitions
├── docs/                         # long-form guides (standard.md, …)
├── knowledge/                    # force-included into the wheel as `m3gast3gg._knowledge`
├── web/                          # browser Text Lab + F5 JPEG (legacy, frozen)
│   └── index.html                # standalone; open directly, no server
├── pyproject.toml                # hatchling, src-layout
├── README.md, INSTALL.md, AGENTS.md, LICENSE
```

## Install

```bash
pip install -e .              # core CLI + MCP servers (MCP is core here)
pip install -e '.[all]'       # + web UI, crypto, jpeg, pdf, metadata
```

Full guide with extras table: [INSTALL.md](INSTALL.md).

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
- Don't rename `m3gast3gg` or its `mcp`/`core`/`webui` subpackages casually — they're wired into `pyproject.toml` entry points (`m3gast3gg-mcp`, `stegg`, `stegg-web`) and the `skills/stegg-stego/` skill.
