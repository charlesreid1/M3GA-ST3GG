<p align="center">
<pre>
     ███████╗████████╗██████╗  ██████╗  ██████╗
     ██╔════╝╚══██╔══╝╚════██╗██╔════╝ ██╔════╝
     ███████╗   ██║    █████╔╝██║  ███╗██║  ███╗
     ╚════██║   ██║    ╚═══██╗██║   ██║██║   ██║
     ███████║   ██║   ██████╔╝╚██████╔╝╚██████╔╝
     ╚══════╝   ╚═╝   ╚═════╝  ╚═════╝  ╚═════╝
</pre>
</p>

<div align="center">

<!-- ⊰ If you can read this, you understand steganography. The real flag is in the banner image. Decode it with ST3GG. ST3GG{s0urc3_v13w3r} LOVE PLINY ⊱ -->

### ⊰•-•✧ THE ULTIMATE STEGANOGRAPHY TOOLKIT ✧•-•⊱

**Hide anything. In any file. Across every modality. Undetected.**

👉 **Hosted site: [ste.gg](https://ste.gg)**

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL_3.0-purple.svg)](https://github.com/elder-plinius/st3gg/blob/main/LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://python.org)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)
[![100+ Examples](https://img.shields.io/badge/Examples-100%2B_files-purple.svg)](https://github.com/elder-plinius/st3gg/tree/main/examples)

```
       __                                    .--.
      /  '-.                               .'    '.
     / .-. |  ⊰ ev͏er͏y pi͏x͏el͏ ha͏s a͏ story͏ ⊱ /  .--.  \
    /.'   \|     you just can't see it    |  /    \  |
   //   |\  \                             | |      | |
  ||   | \  |    ⊰ LOVE PLINY ⊱          |  \    /  |
 /||   |  \ |                              \  '--'  /
/ ||__/   \/                                '.____..'
```

</div>

<p align="center">
<img src="examples/st3gg_banner.png" alt="ST3GG Banner" width="600">
<br><sub><i>This image contains hidden data. Can you find it?</i></sub>
</p>

---

## ⊰ What Is ST3GG? ⊱

[STE.GG](https://ste.gg)‍​‌​‌​​​​​‌​​‌‌​​​‌​​‌​​‌​‌​​‌‌‌​​‌​‌‌​​‌​​‌​​​​​​‌​​‌‌​​​‌​​‌‌‌‌​‌​‌​‌‌​​‌​​​‌​‌​‌​‌​​‌‌​​‌​​​​​​‌​‌‌​​‌​‌​​‌‌‌‌​‌​‌​‌​‌‍ is a feature-rich, open-source steganography toolkit that hides secret data inside images, audio, documents, network packets, and more — using **100+ encoding techniques** across every file format imaginable.

It runs **100% in your browser** (static site, no server) or as a **Python CLI/WebUI**. No data ever leaves your machine. Every technique that encodes also decodes. Every attack surface is also a detection surface.

> *⊰•-•✧ Some secrets are hidden in plain sight ✧•-•⊱*

---

## ⊰ Why ST3GG? ⊱

| Feature | Other Tools | **ST3GG** |
|---------|-------------|-----------|
| Channel Options | RGB only | **15 presets** (R, G, B, A, RG, RB, RA, GB, GA, BA, RGB, RGA, RBA, GBA, RGBA) |
| Bit Depth | 1 bit fixed | **1-8 bits per channel** (adjustable) |
| Encoding Strategies | Sequential | **4 strategies** (sequential, interleaved, spread, randomized) |
| Nested Steg | - | **Up to 11 layers deep** (Matryoshka mode — CLI + API) |
| Channel Cipher | - | **Novel cross-channel hopping** (SPECTER) |
| Compression Survival | - | **F5 survives JPEG/social media; DCT designed for compression resistance** |
| Smart Decode | - | **120+ config auto-detection** |
| Encryption | Basic/None | **AES-256-GCM + XOR** |
| Image Formats | PNG only | **PNG, JPEG, WebP, GIF** |
| File Types | Images only | **Images, audio, text, docs, network, archives, code** |
| Example Library | None | **100+ pre-encoded example files** |
| Browser-Based | - | **100% client-side JS, no server** |
| AI Agent | - | **Exhaustive AI-powered decoding across all methods** |

---

## ⊰ The Big Picture: Offense & Defense ⊱

ST3GG is a **dual-use** toolkit — built for both sides of the steganography battlefield.

### RED TEAM / Offense — Poisoning Simulations

Data exfiltration doesn't always look like data exfiltration. ST3GG lets red teams and researchers simulate **every known data smuggling vector** to test whether defenses actually catch them:

- **100+ encoding techniques** across images, audio, text, documents, network packets, archives, and code files
- **Polyglot file generation** — files that are simultaneously valid as two formats (PNG+ZIP)
- **Network protocol covert channels** — data hidden in DNS queries, ICMP payloads, TCP sequence numbers, HTTP headers
- **Unicode steganography** — invisible homoglyphs (Cyrillic letters + CJK/fullwidth punctuation), zero-width chars, variation selectors, confusable whitespace
- **Compression-resistant encoding** — F5 mode operates directly on JPEG coefficients (proven to survive social media); DCT mode designed for compression resistance
- **Multi-layer nesting** — tested to 11 recursive layers; practical depth bounded by carrier capacity (see `stegg matryoshka plan`)
- **Ghost Mode** — AES-256 encryption + bit scrambling + noise decoys for maximum evasion

*If your DLP can't catch it, you need to know that before the adversary does.*

### BLUE TEAM / Defense — ALLSIGHT Comprehensive Detection

The same toolkit that creates steganographic payloads also **detects and decodes them**. ST3GG's analysis engine provides full-spectrum visibility across all known data smuggling surfaces:

- **20+ detection functions** — chi-square analysis, bit-plane entropy, histogram analysis, signature scanning, STEG header detection
- **AI-powered exhaustive analysis** — autonomous agent tests every decoding method for the uploaded file type
- **File type identification** — magic byte detection for 20+ formats (PNG, JPEG, GIF, BMP, WebP, TIFF, ICO, SVG, WAV, AIFF, AU, MIDI, PCAP, PDF, ZIP, GZip, TAR, SQLite, and more)
- **Unicode steganography detection** — zero-width chars, homoglyphs (Cyrillic letters + CJK/fullwidth punctuation), variation selectors, combining marks, confusable whitespace, emoji patterns
- **Whitespace analysis** — trailing space/tab encoding, Unicode space variant detection
- **Metadata forensics** — base64/hex string extraction, EXIF analysis, PNG chunk inspection
- **Network packet analysis** — PCAP parsing for covert channel indicators
- **200+ automated tests** verifying detection accuracy with zero false negatives on known techniques

*See everything. Miss nothing. That's ALLSIGHT.*

> *⊰•-•✧ The best defense starts with understanding the offense ✧•-•⊱*

---

## ⊰ Who Is This For? ⊱

ST3GG isn't just a toy. Different communities use steganography tools for very different — and very real — reasons.

### Penetration Testers & Red Teams
Simulate data exfiltration through steganographic channels during engagements. Test whether endpoint DLP, SIEM rules, and network monitoring catch covert data smuggling across 100+ vectors. Generate adversarial payloads across every file type to validate detection coverage.

### Blue Teams & SOC Analysts
Use ALLSIGHT to scan suspicious files for hidden payloads. Run exhaustive analysis against every known encoding method. Build detection rules from the comprehensive example library. Train analysts on what steganographic artifacts look like in the wild.

### CTF Players & Competitive Hackers
The ultimate steg toolkit for Capture The Flag competitions. Encode and decode across every channel/bit/strategy combination. Auto-detect unknown configurations with Smart Scan. Unwrap multi-layered Matryoshka challenges with `stegg matryoshka decode` or `stegg analyze --recursive`.

### Digital Forensics & Incident Response
Analyze seized media for steganographic communication channels. Detect hidden data in image attachments, document metadata, audio files, and network captures. Identify which encoding technique was used and extract the hidden payload.

### Privacy Researchers & Journalists
Explore steganography as a privacy-preserving communication channel. Understand the trade-offs between capacity, stealth, and compression survival. Test which techniques survive social media re-encoding for real-world deniable communication.

### Academics & Students
Study the full landscape of steganographic techniques across every modality. Use the 100+ example files as a teaching dataset. Benchmark new detection algorithms against known encodings. The codebase is well-documented and AGPL-3.0 licensed — free for individuals, researchers, and open-source projects.

### AI Safety & LLM Security
Test how AI systems handle steganographic content — hidden instructions in images, invisible Unicode in prompts, polyglot files that bypass content filters. Understand the data smuggling surface area that AI systems need to defend against.

### Data Loss Prevention (DLP) Vendors
Benchmark your DLP solution against ST3GG's 100+ encoding techniques. If your product can't detect data hidden in DNS query names, TCP sequence numbers, or invisible Unicode characters — your customers deserve to know. ST3GG is your adversarial test suite.

### AI Agent Security & Red Teaming
The next frontier of steganography is **agent-to-agent covert communication** and **prompt injection via hidden payloads**. ST3GG is the toolkit for this emerging attack surface:

- **Prompt injection via images** — embed hidden instructions in images that vision-enabled agents process. The agent sees a normal photo; the hidden payload says "ignore all previous instructions."
- **Agent data exfiltration** — test whether your agent can be tricked into encoding stolen data into images it generates, smuggling it past output filters.
- **Covert agent channels** — agents passing hidden instructions through innocuous-looking files in shared tool contexts.
- **Agent output watermarking** — embed provenance or tracking data in images agents generate for attribution.
- **Content filter bypass** — test moderation systems by hiding prohibited content in image payloads that pass automated review.
- **Multi-modal poisoning** — craft images that look normal to humans but contain hidden data that alters agent behavior when processed.

**Use ST3GG as a Python library in your agent pipeline:**

```python
from m3gast3gg.core.img import encode, decode, detect_encoding, StegConfig, get_channel_preset
from m3gast3gg.core.analysis import detect_unicode_steg, detect_file_type, TOOL_REGISTRY
from PIL import Image

# Encode a hidden payload into an image
img = Image.open("carrier.png")
config = StegConfig(channels=get_channel_preset("RGB"), bits_per_channel=1)
stego = encode(img, b"hidden agent instructions", config)
stego.save("stego.png")

# Detect and decode hidden data
detected = detect_encoding(Image.open("stego.png"))
if detected:
    payload = decode(Image.open("stego.png"))
    print(f"Found: {payload.decode()}")

# Scan for ALL steganography types
tools = TOOL_REGISTRY.list_tools()  # 48 detection tools
result = detect_unicode_steg(open("message.txt", "rb").read())
if result['found']:
    print(f"Hidden Unicode: {result['invisible_chars']} chars")
```

---

## ⊰ Megalithic Features ⊱

### SPECTER — Channel Cipher Steganography

*A novel approach where data hops between color channels like a cryptographic dance.*

Instead of hiding all data in one channel, SPECTER distributes bits across R, G, and B channels in a pattern that becomes your key:

```
Pattern: R1-G2-B1-RG2-B1
         │  │  │  │   └─ 1 bit in Blue
         │  │  │  └───── 2 bits in Red+Green
         │  │  └──────── 1 bit in Blue
         │  └─────────── 2 bits in Green
         └────────────── 1 bit in Red
```

Two modes: **Manual Pattern** (you define) or **Password Mode** (derived from passphrase + optional encryption). Embed via **LSB** (high capacity) or **DCT** (compression-resistant).

### Ghost Mode — Maximum Stealth

Triple-layer obfuscation for when the stakes are real:

1. **AES-256-GCM Encryption** — authenticated, military-grade
2. **Bit Scrambling** — Fisher-Yates shuffle with seeded PRNG
3. **50% Noise Decoys** — half the embedded bits are random noise

An attacker would need to know the channel pattern, the password for unscrambling, AND the decryption key. Trade-off: halves capacity.

### Matryoshka Mode — Recursive Nesting

Hide images within images within images — tested to **11 layers deep**. Encode nested payloads from the CLI (`stegg matryoshka encode`), decode recursively (`stegg matryoshka decode`), or auto-detect nested layers in any image with `stegg analyze --recursive`. The library API (`m3gast3gg.core.matryoshka`) is importable for scripting. Russian nesting dolls, but for secrets.

### DCT Mode — Compression Resistant

Traditional LSB is destroyed by ANY JPEG compression — even quality 99%. DCT mode embeds in frequency-domain coefficients of 8x8 pixel blocks, designed for compression resistance. For **proven** social media survival, use **F5 mode** which operates directly on JPEG DCT coefficients via matrix encoding.

> **LSB** → PNG only (lossless). **DCT** → compression resistant. **F5** → survives JPEG/social media.

### AI Agent — Reveal & Conceal

The AI agent has two modes:

**🔍 Reveal** — Upload any file. The agent tests every known decoding method automatically, finds hidden data, and extracts it as downloadable artifacts.

**🔮 Conceal** — Type a secret message, upload (or generate) a carrier image, and the agent hides your data using the optimal encoding method. One click from secret to stego image.

Powered by OpenRouter. Works with Claude, GPT, Gemini, and other models.

---

## ⊰ 100+ Steganographic Techniques ⊱

ST3GG doesn't just hide data in images. It covers **every modality**:

### Image Techniques
LSB embedding (RGB, RGBA, grayscale) across PNG, BMP, TIFF, GIF, WebP, ICO, PPM, PGM — plus alpha channel LSB, PNG filter-type encoding, palette index manipulation, DCT frequency domain, PNG+ZIP polyglots, metadata injection (EXIF, XMP, tEXt chunks), and trailing data after IEND.

> **F5 (JPEG DCT)** — hides data in the least significant bits of quantized DCT coefficients of a JPEG's luminance channel. Uses matrix encoding (Westfeld 2001) with permuted coefficient order and shrinkage handling. Requires the `jpeg` extra (`pip install -e '.[jpeg]'` in this fork; see [INSTALL.md](INSTALL.md)).
>
> ```bash
> stegg dct f5 encode -i in.jpg -t "secret" -p password -o out.jpg
> stegg dct f5 decode -i out.jpg -p password
> stegg dct f5 capacity -i in.jpg
> ```

### Text & Unicode Techniques
Zero-width characters (ZWSP/ZWNJ/ZWJ), invisible ink (Unicode tag chars U+E0000), homoglyph substitution (Cyrillic letters + CJK/fullwidth punctuation), variation selectors, combining diacritics (CGJ), confusable whitespace (en/em/thin/hair spaces), whitespace encoding (space=0/tab=1), emoji substitution, and capitalization encoding.

### Audio Techniques
Sample LSB in WAV, AIFF, and AU formats. Silence interval timing (gap duration encodes bits). MIDI SysEx message embedding.

### Network Protocol Techniques
DNS tunneling (base32 in query labels), ICMP payload injection, TCP covert channels (ISN + timestamps), HTTP header smuggling (custom X- headers, cookies).

### Document & Archive Techniques
PDF (metadata streams + XMP + post-EOF), HTML (comments + hidden elements + data attributes + zero-width), XML (CDATA + PIs + namespaces), JSON (Unicode escapes + key ordering), CSV/YAML/TOML/INI (comment encoding + whitespace), RTF (hidden text groups), Markdown (HTML comments + link references), ZIP/TAR/GZip (comments + extended headers + extra fields), SQLite (hidden tables), and more.

### Code Techniques
Python, JavaScript, C, CSS, Shell, SQL, LaTeX — all with steganographic comments, hex byte tables, zero-width docstrings, and per-byte calibration entries.

### Text Transformations (reversible reshaping, not hiding)

Distinct from text steganography: text transforms *reshape input visibly*
(ROT13, Base64, homoglyph) instead of *hiding a payload invisibly* in a
carrier. Useful for CTFs, jailbreak-obfuscation chains, and as pipeline
stages upstream of steg. 26 registered transforms across 7 categories:

- **cipher** (5): `caesar`, `rot13`, `atbash`, `vigenere`, `bacon` — classical ciphers, not encryption.
- **encoding** (10): `base64`, `base32`, `base58`, `hex`, `binary`, `ternary`, `ascii85`, `morse`, `url`, `quoted-printable`.
- **concealment** (3): `homoglyph`, `invisible-text` (Unicode Tag), `zero-width` (ZWJ/ZWSP/ZWNJ bridge to `core.text`).
- **unicode** (2): `fullwidth`, `zalgo`.
- **case** (3): `uppercase`, `lowercase`, `titlecase`.
- **format** (2): `reverse`, `remove-whitespace`.
- **visual** (1): `leetspeak`.

```bash
stegg transform list                                # every transform, grouped
stegg transform encode caesar --text "Attack" --option shift=5
stegg transform decode base64 --text "SGVsbG8="
stegg transform auto-decode --text "SGVsbG8sIFdvcmxkIQ=="   # universal decoder
stegg transform chain --text "Attack" \
    --step 'caesar shift=5' --step base64                   # ordered pipeline
```

Same surface over MCP: `stegg_list_transforms`, `stegg_inspect_transform`,
`stegg_encode_transform`, `stegg_decode_transform`, `stegg_chain_transforms`,
`stegg_auto_decode`. See [`docs/standard.md#transforms-vs-steg`](docs/standard.md#transforms-vs-steg)
for the transforms-vs-steg framing.

> *⊰•-•✧ See the full catalog: [`examples/README.md`](examples/README.md) ✧•-•⊱*

---

## ⊰ Quick Start ⊱

> **This repo is [`charlesreid1/M3GA-ST3GG`](https://github.com/charlesreid1/M3GA-ST3GG),
> a fork of upstream [`elder-plinius/st3gg`](https://github.com/elder-plinius/st3gg).
> It is not published to PyPI** — `pip install stegg` pulls the upstream
> package, not this fork. Install this fork from source (below). For the full
> install guide including extras, requirements, and upstream instructions, see
> [INSTALL.md](INSTALL.md).

### Install from source (this fork)

```bash
git clone git@github.com:charlesreid1/M3GA-ST3GG.git
cd M3GA-ST3GG
python3 -m venv venv
source venv/bin/activate
pip install -e '.[all]'       # or bare `-e .` for core CLI + MCP servers only
```

Now you have `stegg` in your terminal:

```bash
# Encode a secret message
stegg encode image.png "your secret message" -o stego.png

# Decode hidden data
stegg decode stego.png

# Analyze a suspicious file
stegg analyze suspicious.png --full

# SPECTER mode with password
stegg encode image.png "{SPECTER:ENABLED}" -o stego.png
```

### Browser (No Install)

```bash
# Just open web/index.html — that's it. No server needed.
open web/index.html
```

Everything runs 100% client-side. No data ever leaves your machine.

### Upstream via PyPI (separate project)

The upstream project `elder-plinius/st3gg` is on PyPI as `stegg`. That is a
different codebase from this fork — installing it does **not** install this
repo's changes:

```bash
pip install stegg
pip install 'stegg[all]'
```

### Interfaces

```bash
stegg --help          # Interactive CLI (Rich output)
stegg --json <cmd>    # Same CLI, JSON output — subprocess-friendly for agents
stegg-web             # Browser UI (requires the [web] extra — see INSTALL.md)
m3gast3gg-mcp         # MCP server for AI agents; `--transport {stdio,sse,streamable-http}`
```

### AI Agent Integration

Two interfaces for AI agents — pick based on context cost needs:

```bash
# CLI (subprocess, zero context cost — output stays out of LLM context)
stegg --json encode-cmd -i carrier.png -t "secret" -o stegged.png
stegg --json decode-cmd -i stegged.png
stegg --json analyze suspect.png --full

# MCP server (results go into agent context)
m3gast3gg-mcp                              # streamable-http on :8765/mcp (default)
m3gast3gg-mcp --transport stdio            # local clients (Claude Desktop, opencode)
m3gast3gg-mcp --transport sse              # legacy SSE on :8765/sse
m3gast3gg-mcp-stdio                        # alias for `--transport stdio`
```

| Transport         | When to use                                              | Endpoint  |
|-------------------|----------------------------------------------------------|-----------|
| `stdio`           | Client spawns the server; JSON-RPC on stdin/stdout       | (n/a)     |
| `sse`             | Legacy MCP web transport (Server-Sent Events)            | `/sse`    |
| `streamable-http` | Modern HTTP transport (default)                          | `/mcp`    |

Five docs describe the agent surface. Each has a different audience and a different loading moment — don't conflate them:

| Doc | Purpose | Read by |
| --- | --- | --- |
| [`AGENTS.md`](AGENTS.md) | Repo orientation, install, entry-point framing, ground rules | An agent dropped into the repo to modify code |
| [`skills/stegg-cli/SKILL.md`](skills/stegg-cli/SKILL.md) | When-to-fire triggers + invocation recipes for the subprocess CLI | The host's skill picker, before touching the repo |
| [`skills/stegg-stego/SKILL.md`](skills/stegg-stego/SKILL.md) + [`REFERENCE.md`](skills/stegg-stego/REFERENCE.md) | When-to-fire triggers, tool-selection heuristics, workflow recipes for the MCP server (SKILL.md); exhaustive per-tool spec (REFERENCE.md) | The host's skill picker (SKILL.md); the agent mid-session when it needs argument tables (REFERENCE.md) |
| [`src/m3gast3gg/field_guide.md`](src/m3gast3gg/field_guide.md) | ST3GG persona, mode gate, dispatch tables, verdict semantics, response format (~290 lines; the technique catalog / capacity numbers / transport-survival tables / pattern-diagnosis snippets live in the KR — cite via `stegg_lookup_technique` / `stegg_verify_survival` / `stegg_search_records`) | An agent about to analyze a file, fetched on-demand via the `stegg://field-guide` MCP resource |
| [`knowledge/`](knowledge/) (records + prose corpus) | Cited numeric facts (bits/pixel, survival cells, capacity formulas, bibliography) and split-per-topic prose (`README` / `reference` / `walkthrough` / `recognition` / `history`) | An agent that needs a citation-backed answer, fetched on-demand via `stegg_lookup_technique` / `stegg_verify_survival` / `stegg_verify_claim` / `stegg_explain_pipeline` / `stegg://<topic>/<name>` |

For the full audience-and-when-read matrix, plus the rule about which doc owns what, see [`AGENTS.md#docs-map`](AGENTS.md#docs-map). To make the skills discoverable in Claude Code, follow the symlink recipe in [`AGENTS.md#install-the-skills`](AGENTS.md#install-the-skills).

---

## ⊰ Channel & Bit Depth ⊱

### 15 Channel Presets x 8 Bit Depths = 120 Combinations

| Preset | Stealth | Capacity | Best For |
|--------|---------|----------|----------|
| B (Blue, 1-bit) | Excellent | Low | Maximum invisibility |
| RGB (3-channel, 1-bit) | Very Good | Medium | Balanced |
| RGBA (4-channel, 4-bit) | Moderate | **4MB+** | Large file hiding |

### 4 Encoding Strategies

| Strategy | Description |
|----------|-------------|
| **Sequential** | Bits placed in pixel order (fastest) |
| **Interleaved** | Alternating pixels across image |
| **Spread** | Distributed evenly across entire image |
| **Randomized** | Pseudo-random placement (seeded PRNG) |

### Capacity Formula

```
Capacity = (Width x Height x Channels x BitsPerChannel) / 8 bytes
```

A 1920x1080 image with RGB 1-bit holds ~760KB. With RGBA 4-bit: **~4MB**.

---

## ⊰ Encryption ⊱

| Method | Strength | Speed | Use Case |
|--------|----------|-------|----------|
| **AES-256-GCM** | Maximum | Medium | Ghost Mode |
| **XOR Obfuscation** | Minimal | Fast | Basic scrambling only (not encryption) |
| **None** | - | Fastest | When secrecy isn't needed |

---

## ⊰ Example Library ⊱

ST3GG ships with **100+ pre-encoded example files** spanning every technique — images, audio, documents, network captures, code files, and more. Each one contains a hidden message that the analysis tools can find.

```bash
# Regenerate all examples
python examples/generate_examples.py

# Run the pytest suite
pytest -q -m "not slow"
```

See [`examples/README.md`](examples/README.md) for the full catalog.

---

## ⊰ Project Structure ⊱

Src-layout single package `m3gast3gg` under `src/`. Core steganography library and the MCP server ship together in one wheel.

```
M3GA-ST3GG/
├── src/m3gast3gg/            # the package
│   ├── __main__.py           # `m3gast3gg-mcp` entry point
│   ├── server.py             # ASGI MCP app (HTTP + stdio)
│   ├── cli.py                # `stegg` CLI (Rich TUI; `--json` for machine output)
│   ├── records.py            # typed-record KR loader (strict load-time validation)
│   ├── field_guide.md        # served as MCP resource `stegg://field-guide`
│   ├── TRANSPORT_MATRIX.md   # delivery-channel survival notes (matrix autogen'd from survival.json)
│   ├── core/                 # steganography library
│   │   ├── img.py            # image LSB encode/decode + capacity math
│   │   ├── text.py           # text/emoji encode/decode (14 methods)
│   │   ├── analysis.py       # 264+ detection/analysis functions
│   │   ├── crypto.py         # optional AES-256-GCM
│   │   ├── transforms/       # text transforms (cipher/encoding/unicode/concealment/format/visual)
│   │   ├── decoder.py        # universal auto-decoder over the transforms registry
│   │   ├── jailbreak.py      # multi-vector prompt-injection composer
│   │   ├── audio.py, network.py, pdf.py, metadata.py, matryoshka.py, …
│   │   └── f5/               # F5 JPEG DCT (Python port of the JS reference)
│   ├── mcp/                  # per-family MCP tools (image/text/network/…)
│   │   └── knowledge.py      #   `stegg_lookup_*` / `stegg_verify_*` / lore tools
│   └── webui/                # optional NiceGUI UI (`stegg-web`, [web] extra)
│
├── web/                      # browser Text Lab + F5 JPEG (legacy, frozen)
│   └── index.html            # 100% client-side; open directly, no server
│
├── tests/                    # pytest suite (round-trips, detectors, KR gold-standard Q/A + adversarial traps)
├── examples/                 # 100+ pre-encoded fixtures + generate_examples.py
├── transport_probes/slack/   # delivery-channel probe harness + results
├── scripts/                  # doc-generation helpers (render_skill_tool_index.py, render_transport_matrix.py)
├── skills/, docs/
├── knowledge/                # two-layer corpus (typed KR + prose); wheel force-includes it as `m3gast3gg._knowledge`
├── pyproject.toml            # hatchling, src-layout
└── README.md, INSTALL.md, AGENTS.md, LICENSE
```

See [AGENTS.md](AGENTS.md) for the full layout with per-module notes.

## ⊰ Knowledge Base ⊱

ST3GG ships a two-layer knowledge base with a split-per-topic pattern. Agents connected via the MCP server (or humans reading the repo) get **cited numeric answers** instead of folklore — every technique, transport, detector, and myth is a typed record with a mandatory citation envelope.

### Typed records — `knowledge/records/*.json`

One JSON array per category, each record carrying a mandatory envelope (`id`, `name`, `aliases`, `category`, `carrier_family`, `layer`, `era_bounds`, `confidence`, `citations`, `see_also`, `disputed`, `technical_body`). Load-time validation is strict: empty `citations[]` or an unresolved bibliography id raises `RecordError` and the MCP server won't boot.

| File | What it holds |
| --- | --- |
| `bibliography.json` | Every source anything else cites (RFCs, papers, repo docs). |
| `techniques.json` | One record per encode/decode method with numeric `technical_body` (bits/carrier, prefix scheme, capacity formula, stealth class). |
| `carrier_formats.json` | Format specs: PNG chunk grammar, JPEG DCT structure, WAV RIFF, PCAP frames. |
| `layers.json` | The five canonical steg layers (bit / coefficient / character / container / semantic). |
| `transports.json` | Delivery channels with `canonical_layer`, `known_strips[]`, `known_recodes[]`. |
| `survival.json` | (technique, transport) cells with `status ∈ {✅, ❌, ⚠, ❓}`, evidence, tested_at. Regenerates `TRANSPORT_MATRIX.md`. |
| `detectors.json` | Chi-square, RS, sample-pairs, bit-plane entropy, F5 signature, PVD detector. |
| `signatures.json` | "If you see X, technique is probably Y" pattern-diagnosis records (with Python snippets where they clarify). |
| `myths.json` | Explicit false claims (powers `stegg_verify_claim`). |
| `capacity_models.json` | Per-technique capacity formulas + worked examples (image LSB / PVD / DCT / F5 / jsteg + eight text methods). |
| `external_tools.json` | steghide, jsteg, outguess, zsteg, stegdetect, binwalk, foremost, StegExpose, Aletheia, ExifTool with capability + interop notes. |
| `ctf_genres.json` | Compound-technique catalog: matryoshka, chained-carrier, polyglot-injection, spectrogram, unicode-tag-jailbreak, alpha-channel, PNG private-chunk. |

### Prose corpus — `knowledge/<topic>/`

One directory per topic (`image`, `text`, `emoji`, `audio`, `network`, `document`, `detection`, `transport`, `crypto`, `ctf`), one idea per markdown file. Each topic starts with `README.md` and can drill down with per-technique subdirectories that carry a `README` (orient) + `reference` (params) + `walkthrough` (end-to-end) + `recognition` (15-second triage) — for example `knowledge/image/lsb/{README,reference,walkthrough,recognition}.md`, and analogous splits under `image/f5/`, `text/zero-width/`, and `text/homoglyph-cyrillic/`. Every markdown file is auto-exposed as an MCP resource at `stegg://<topic>/<name>` (and `<topic>/<subtopic>/<file>` where the split exists).

### Honesty signal — `knowledge/known-unknowns.md`

A running audit of every claim ST3GG *acts on* in the field guide or KR that isn't yet tied to a primary source or a first-party measurement. Fix by adding a citation or by running a probe and landing the result in `survival.json`. Adding to the list is *good* — it's the audit trail for what ST3GG doesn't know it doesn't know.

### Retrieval tools (MCP)

The `stegg-mcp` server exposes ten tools that read this knowledge base:

- `stegg_lookup_technique` — full technique record + envelope. The "numbers not adjectives" tool.
- `stegg_verify_survival` — (technique, transport) status + evidence + tested_at + caveat/workaround.
- `stegg_verify_claim` — grade a natural-language assertion as `false` / `needs_qualification` / `unverified` against `myths.json`.
- `stegg_explain_pipeline` — ordered list of technique records for a goal (filters by carrier + transport + stealth constraint).
- `stegg_bibliography` — resolve a citation or list every source.
- `stegg_cross_reference` — walk a record's `see_also` links.
- `stegg_search_records` — filter records by `category` / `carrier_family` / `layer` / `transport`.
- `stegg_list_topics` / `stegg_read_lore` / `stegg_search_lore` — enumerate + read + regex-search the prose corpus.

See [`knowledge/MANIFEST.md`](knowledge/MANIFEST.md) and [`knowledge/records/README.md`](knowledge/records/README.md) for the discipline conventions.

---

## ⊰ Security Notes ⊱

- Standard LSB steganography is **statistically detectable** — chi-square and bit-plane analysis can reveal it
- **SPECTER Channel Cipher** increases resistance by hopping across channels unpredictably
- **Ghost Mode** adds encryption + scrambling + noise for maximum stealth
- **DCT mode** designed for compression resistance; **F5 mode** proven to survive JPEG recompression
- **LSB** is destroyed by ANY JPEG compression — use PNG format only
- Always **encrypt** sensitive data before embedding
- For maximum security: **Ghost Mode + DCT + strong password**

---

## ⊰ Roadmap ⊱

```
╔══════════════════════════════════════════════════════════════════╗
║                    ST3GG EVOLUTION ROADMAP                       ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  ✅ SHIPPED                                                      ║
║  ────────                                                        ║
║  ✓ 112 steganographic techniques across all modalities           ║
║  ✓ 15 channel presets × 8 bit depths = 120 LSB combinations     ║
║  ✓ 8 encoding methods (LSB, DCT, PVD, F5, Chroma, Palette,     ║
║    Spread Spectrum, SPECTER channel cipher)                      ║
║  ✓ AI Agent with Reveal + Conceal modes                          ║
║  ✓ 13 text steganography methods with encode + decode            ║
║  ✓ 50 registered analysis/decode tools                           ║
║  ✓ RS Analysis + Sample Pairs Analysis (academic steganalysis)   ║
║  ✓ Raw PNG parser (bypasses canvas premultiplied alpha)          ║
║  ✓ Password-derived headers (stealth mode)                       ║
║  ✓ AES-256-GCM with PBKDF2 600k iterations                      ║
║  ✓ AI carrier image generation (OpenRouter + procedural)         ║
║  ✓ 109 example files, 659 automated tests                        ║
║  ✓ pip install stegg  (upstream only — this fork: from source)   ║
║  ✓ 100% browser-based at ste.gg                                  ║
║                                                                  ║
║  🔜 NEXT UP                                                      ║
║  ──────────                                                      ║
║  ○ Spread + Randomized strategies in browser                     ║
║    (defined but only interleaved is implemented)                 ║
║  ○ Password brute-forcer with wordlist support                   ║
║    (Stegseek does 10M/sec — we should match it)                 ║
║  ○ Content-adaptive embedding (HUGO/WOW-inspired)                ║
║    (embed in texture, skip smooth areas)                         ║
║  ○ Steghide format compatibility                                 ║
║    (read/write steghide's embedding format)                      ║
║  ○ Weighted Stego (WS) analysis                                  ║
║    (more accurate LSB detection than chi-square)                 ║
║  ○ Calibrated RS/SPA for real-world detection accuracy           ║
║                                                                  ║
║  🔮 FUTURE                                                       ║
║  ──────────                                                      ║
║  ○ ML-based steganalysis                                         ║
║    (CNN trained on StegoAppDB — Aletheia-grade detection)        ║
║  ○ nsF5 / S-UNIWARD embedding                                    ║
║    (academic state-of-the-art, minimal detectability)            ║
║  ○ Adversarial steganography                                     ║
║    (GAN-based embedding that defeats ML detectors)               ║
║  ○ Video steganography (frame-by-frame + temporal)               ║
║  ○ Network protocol live capture + injection                     ║
║    (real-time covert channel creation, not just PCAPs)           ║
║  ○ WebAssembly acceleration for browser-side analysis            ║
║  ○ Plugin system for community-contributed techniques            ║
║  ○ Mobile-native app (iOS/Android)                               ║
║  ○ VS Code / JetBrains extension for inline text steg            ║
║  ○ MCP server for Claude Code / AI agent integration             ║
║                                                                  ║
║  🌊 MOONSHOTS                                                    ║
║  ────────────                                                    ║
║  ○ Quantum-resistant steganographic protocols                    ║
║  ○ Blockchain-anchored provenance watermarking                   ║
║  ○ Cross-modal steganography (hide audio in images,              ║
║    images in text, text in network traffic)                      ║
║  ○ Federated steganalysis (distributed detection network)        ║
║  ○ Self-modifying steganographic payloads                        ║
║  ○ Steganographic filesystem (deniable encryption layer)         ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

> *⊰•-•✧ Want to help build any of these? PRs welcome. ✧•-•⊱*

---

## ⊰ Contributing ⊱

PRs are welcome! Whether it's new steganographic techniques, better detection algorithms, or entirely new modalities.

```bash
# Run the pytest suite
pytest -q -m "not slow"

# Regenerate all example files
python examples/generate_examples.py
```

Areas we'd especially love contributions in:
- **ML steganalysis** — train detection models on stego datasets
- **New encoding methods** — academic techniques (HUGO, WOW, HILL, UNIWARD)
- **Format support** — HEIC, AVIF, FLAC, MP4 steganography
- **Steghide compatibility** — read/write steghide's format natively
- **Performance** — WebAssembly for browser-side analysis
- **Mobile** — responsive improvements, native app wrappers

---

## ⊰ License ⊱

**AGPL-3.0** — free and open source for individuals, researchers, educators, and open-source projects. See [LICENSE](LICENSE) for details.

**Enterprise / Commercial use?** If you want to use ST3GG in a proprietary product or SaaS without open-sourcing your code, contact us for a commercial license.

This tool is intended for **authorized security research**, **CTF competitions**, **digital forensics education**, and **privacy research**. Use responsibly.

---

<div align="center">

```
⊰•-•✧•-•-⦑ ST3GG ⦒-•-•✧•-•⊱
  every pixel has a story
    you just can't see it
           🦕︁
```

*⊰ hidden in plain sight ⊱*

</div>

[//]: # (⊰ ST3GG{r34dm3_h4ck3r} - you found the hidden link reference! The Plinian divider lives in all things. LOVE PLINY ⊱)
