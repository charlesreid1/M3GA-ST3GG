---
name: stegg-cli
description: "Subprocess CLI for ST3GG steganography — encode/decode, steganalysis, PNG chunk/EXIF injection, and AI red-team payloads. Runs as subprocess so output stays out of context. Use when hiding data in images, analyzing images for hidden content, injecting metadata, crafting steganographic PoCs, or detecting steganographic content. Triggers on stegg, steganography, steg, LSB, hide data in image, hidden data, steganalysis."
---

# ST3GG CLI

Subprocess steganography CLI. Output stays out of LLM context — invoke as `stegg --json <command>`. All output is JSON.

**This is the primary interface for steganography operations.** Prefer this over the MCP server for routine use (zero context cost). Fall back to MCP tools when you need results inline.

## Commands

```
encode-cmd       -i IMAGE [-t TEXT|-f FILE] [-o OUT] [--channels C] [--bits N] [--password P]
decode-cmd       -i IMAGE [-o OUT] [--no-auto] [--channels C] [--bits N] [--password P]
analyze          IMAGE [--full] [--recursive]
detect           IMAGE
capacity         IMAGE [--channels C] [--bits N]
chunks           IMAGE
inject chunk     -i IMAGE -o OUT --text TEXT [--type tEXt] [--keyword Comment]
inject exif      -i IMAGE -o OUT [--comment C] [--author A] [--custom-fields JSON]
inject filename  [--template T] [--channels C] [--count N]
inject templates
analysis-tool    IMAGE ACTION
list-tools
info-cmd
```

## Quick Reference

### Encode + Verify + Decode

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

### Analyze + Detect

```bash
# Quick header check
stegg --json detect suspect.png

# Chi-square anomaly analysis
stegg --json analyze suspect.png

# Specific analysis function
stegg --json analysis-tool suspect.png rs_analysis
stegg --json analysis-tool suspect.png sample_pairs_analysis
```

### Metadata Injection

```bash
# PNG chunk
stegg --json inject chunk -i image.png -o out.png --text "hidden metadata"

# Private chunk type
stegg --json inject chunk -i image.png -o out.png --type stEg --text "private"

# EXIF fields
stegg --json inject exif -i image.png -o out.png --comment "payload" --author "red-team"

# Read chunks
stegg --json chunks image.png
```

### AI Red Team

```bash
# Generate injection filenames
stegg --json inject filename --template claude_decoder --channels R --count 3

# List jailbreak templates
stegg --json inject templates
```

## Key Constraints

- **Use `interleaved` strategy** (default) — only strategy with auto-detect on decode
- `spread` and `randomized` have upstream decode bugs
- `sequential` works but needs `--no-auto` on decode
- All `--json` output is JSON; errors print to stderr with exit code 1
- **Always verify encode with decode** before distributing stegged images

## Installation

```bash
pip install stegg
# CLI is available as stegg, or:
python3 cli.py --json <command>
```
