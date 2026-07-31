---
name: stegg-cli
description: "Subprocess CLI for ST3GG steganography. Covers image LSB encode/decode + steganalysis + PNG chunk/EXIF injection, DCT + F5 (JPEG-survivable), text/emoji encode/decode (14 methods), Matryoshka nested-image steg, SPECTER channel-cipher steg, and jailbreak / prompt-injection composers + detectors. All output is JSON — invoke as `stegg --json <command>` so results stay out of LLM context. Use when running many operations, encoding/decoding routine payloads, or emitting artifacts for later inspection. For inline reasoning over results (verdicts, triage, chained decisions between steps) use `stegg-stego` (MCP) instead. Triggers on stegg, steganography, steg, LSB, DCT, F5, hide data, hidden data, steganalysis, PNG chunk, EXIF injection, matryoshka, SPECTER, jailbreak, prompt injection."
---

# ST3GG CLI

Subprocess steganography CLI. Output stays out of LLM context — invoke as `stegg --json <command>`. Most subcommands emit JSON on stdout; errors on stderr with exit code 1.

**Known gap** (tracked in `plan-06-follow-on.md` §1): a handful of subcommands (`text encode|decode|capacity`, `analyze`, `analysis-tool`, `inject filename|templates|detect`) still print leftover Rich/TUI output regardless of `--json`. If you need parseable output from those, work around it until the Rich calls get ripped out of `cli.py`. JSON-clean subcommands: `encode-cmd`, `decode-cmd`, `detect`, `capacity`, `chunks`, `inject chunk`, `inject exif`, `list-tools`.

**When to use this vs. `stegg-stego` (MCP):** prefer this for routine encode/decode/analyze and for batch runs where output is verbose. Reach for the MCP server when you want the LLM to reason over results inline, chain tools with judgment between steps, or need the `stegg_triage` verdict + `stegg://field-guide` resource loaded.

## Commands

Top-level:

```
encode-cmd     Hide payload in image (LSB). -i IMAGE [-t TEXT|-f FILE] [-o OUT] [--channels C] [--bits N] [--password P]
decode-cmd     Recover payload from image (LSB). -i IMAGE [-o OUT] [--no-auto] [--channels C] [--bits N] [--password P]
analyze        Full analysis on an image. IMAGE [--full] [--recursive]
detect         Quick ST3GG v3 header detection check. IMAGE
capacity       Report LSB payload capacity. IMAGE [--channels C] [--bits N]
chunks         Dump PNG chunks (type, length, text content). IMAGE
analysis-tool  Run one named analysis function. IMAGE ACTION      (see `list-tools`)
list-tools     List all registered analysis actions (currently 75).
info-cmd       Show system info + build capabilities.
```

Subcommand groups:

```
dct encode | decode | capacity        Frequency-domain steg (survives JPEG recompression).
dct f5 encode | decode | capacity     F5 (Westfeld 2001) — matrix-encoded JPEG DCT.
text encode | decode | capacity       Text/emoji steg — 14 methods (see `stegg-stego` REFERENCE for the method list).
matryoshka embed | extract | plan     Recursive nested-image steg.
specter encode | decode               SPECTER channel-cipher steg.
inject chunk | exif                   PNG text-chunk / EXIF metadata injection.
inject filename | templates | show    Jailbreak filename generator + template catalog.
inject compose | detect               Multi-vector jailbreak composer + detection sweep.
inject zalgo | leet                   Text-transform helpers used by `inject compose`.
```

Not in the CLI: network / PCAP steg and image PVD live only in the MCP tool surface (`stegg-stego`). If you need those, use MCP.

## Quick Reference

### Encode + verify + decode

```bash
# Hide text
stegg --json encode-cmd -i carrier.png -t "secret message" -o stegged.png
# Always verify roundtrip after encoding
stegg --json decode-cmd -i stegged.png

# Hide file with encryption
stegg --json encode-cmd -i carrier.png -f payload.bin -o stegged.png --password s3cret
stegg --json decode-cmd -i stegged.png --password s3cret

# Decode with manual config (non-interleaved strategies)
stegg --json decode-cmd -i stegged.png --no-auto --strategy sequential
```

### Analyze + detect

```bash
# Quick header check
stegg --json detect suspect.png

# Full analysis
stegg --json analyze suspect.png --full

# One specific analysis function (see `stegg --json list-tools`)
stegg --json analysis-tool suspect.png rs_analysis
stegg --json analysis-tool suspect.png sample_pairs_analysis
```

### JPEG-survivable (DCT + F5)

```bash
# DCT — spatial DCT coefficients
stegg --json dct encode -i carrier.jpg -t "secret" -o stegged.jpg
stegg --json dct decode -i stegged.jpg

# F5 — matrix-encoded JPEG DCT (Westfeld 2001)
stegg --json dct f5 encode -i in.jpg -t "secret" -p password -o out.jpg
stegg --json dct f5 decode -i out.jpg -p password
stegg --json dct f5 capacity -i in.jpg
```

### Text / emoji

Cover and stego inputs are file paths (use `-` for stdin).

```bash
stegg --json text capacity --method zero_width --cover cover.txt
stegg --json text encode   --method zero_width --cover cover.txt --secret "hi" --out stego.txt
stegg --json text decode   --method zero_width --stego stego.txt
```

### Metadata injection

```bash
# PNG chunk (public tEXt)
stegg --json inject chunk -i image.png -o out.png --text "hidden metadata"

# Private chunk type
stegg --json inject chunk -i image.png -o out.png --type stEg --text "private"

# EXIF-adjacent tEXt fields via PIL PngInfo
stegg --json inject exif -i image.png -o out.png --comment "payload" --author "red-team"

# Read chunks back
stegg --json chunks image.png
```

### Jailbreak / prompt-injection (authorized red-team, CTFs, detection tuning)

Framing consistent with `AGENTS.md` — for CTFs, DEF CON challenges, hardware badges, authorized red-team ops, detection-tuning, and forensic research.

```bash
# Templates
stegg --json inject templates
stegg --json inject show <template-name>

# Filename generator
stegg --json inject filename --template claude_decoder --channels R --count 3

# Full multi-vector composer (LSB + PNG metadata + filename)
stegg --json inject compose --template <name> -i carrier.png -o out.png

# Blue-team side: detection sweep across all vectors
stegg --json inject detect -i suspect.png --full
```

## Key Constraints

- **Use `interleaved` strategy** (default) — only strategy with auto-detect on decode.
- `sequential` works but needs `--no-auto` on decode.
- `--json` is honored by most (not all) subcommands — see the "Known gap" note at the top for the current holdouts. When honored, JSON goes to stdout, errors to stderr with exit code 1.
- **Always verify encode with decode** before distributing stegged images.
- No `stegg-cli` executable exists — the CLI is `stegg` with the `--json` flag.

## Installation

This fork installs from source; see `INSTALL.md` at the repo root for the full recipe. Short version: `pip install -e .` inside a venv exposes `stegg` on your PATH.
