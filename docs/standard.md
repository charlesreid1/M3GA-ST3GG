# ST3GG Architecture Standard

## The three-function rule

Every stego technique exposed to users **must** provide three operations:

| Function | Purpose | Returns |
|---|---|---|
| `*_encode(data, payload, ...)` | Embed a payload into a carrier | `bytes` (the modified carrier) |
| `*_decode(data, ...)` | Recover a payload from a carrier | `bytes` (the extracted payload) |
| detect | Determine whether a carrier contains a payload | `dict` with at minimum `{"found": bool}` |

A technique without all three is incomplete — you can't hide what you can't find, and you can't find what you can't recover.

Detection is often satisfied by the decode function itself (returning empty bytes or `{"found": false}` on clean carriers), or by a function in `m3gast3gg.core.analysis` for file-format-specific scanning.

## Naming conventions

### Core modules

Domain-specific stego modules live under `m3gast3gg.core`:

```
m3gast3gg/core/img.py        core/audio.py       core/text.py
m3gast3gg/core/network.py    core/pdf.py         core/metadata.py
m3gast3gg/core/jailbreak.py  core/transforms/    core/matryoshka.py
m3gast3gg/core/decoder.py
```

Shared primitives that don't own a domain use descriptive names:

```
m3gast3gg/core/crypto.py        core/unicode_tags.py     core/specter.py
m3gast3gg/core/capabilities.py  core/analysis.py
```

### Packages

Packages follow the same logic. `m3gast3gg/core/f5/` is a package (not `f5.py`) because it contains multiple interdependent modules:

```
m3gast3gg/core/f5/
  __init__.py       # re-exports public API: F5Base, F5Stegg, F5Error, ...
  f5_base.py        # public: abstract F5 core
  f5_stegg.py       # public: stegg-dialect F5
  jsteg.py          # public: JSteg implementation
  _dct.py           # private: JPEG DCT coefficient I/O
  _errors.py        # private: exception classes
  _framing.py       # private: stegg 2/3-byte LE length framing
  _matrix.py        # private: matrix encoding/decoding
  _prng_stegg.py    # private: RC4-KSA keystream PRNG
```

Underscore-prefixed modules (`_*.py`) are **private internals** of the package. Nothing outside the package imports them directly (tests are the exception). Public modules have no underscore.

### Function naming

Encode/decode functions follow the pattern `<domain>_<method>_encode` / `_decode`:

```
f5_encode / f5_decode
jsteg_encode / jsteg_decode
audio_lsb_encode / audio_lsb_decode
gif_comment_encode / gif_comment_decode
gif_palette_lsb_encode / gif_palette_lsb_decode
apng_fdat_encode / apng_fdat_decode
polyglot_png_zip_encode
```

Where the plan called for `_smuggle`, prefer `_encode` for consistency. The one exception is `pdf_smuggle` (the carrier is created from scratch, not modified in place — "smuggle" signals no carrier input).

## Three-layer architecture

Every technique has the same call path:

```
CLI (m3gast3gg/cli.py)     MCP (m3gast3gg/mcp/*.py)
       │                              │
       │  Typer commands               │  async executor
       │  reads/writes files          │  reads/writes files via _common.py
       │                              │
       └──────────┬───────────────────┘
                  │
                  ▼
         Core (*_core.py)
         Pure functions, no I/O
         str | bytes → bytes | dict
```

### Layer 1: Core (`m3gast3gg/core/*.py`, `m3gast3gg/core/f5/`)

Pure functions. No file I/O, no CLI argument parsing, no MCP awareness.

**Input convention:** functions accept `str | bytes` for carrier data (file path or raw bytes) and `str | bytes` for payloads (UTF-8 string or raw bytes). Internal `_to_bytes()` and `_payload_to_bytes()` helpers normalize at the top of each function. The actual algorithm works with `bytes`.

**Output convention:** encode returns `bytes` (the modified carrier). Decode returns `bytes` (the extracted payload). Detection/analysis returns `dict`.

**Framing convention:** payloads are prefixed with a **4-byte big-endian length header** before embedding:

```python
framed = struct.pack(">I", len(payload)) + payload
```

This is the library-wide standard, used by `audio_lsb`, `jsteg`, and `gif_palette_lsb`. The F5 dialect uses its own 2/3-byte little-endian framing for byte-compatibility with `f5stego-lib.js`.

### Layer 2: MCP (`m3gast3gg/mcp/`)

One module per tool family. Each module exports two dicts:

```python
# image.py
EXECUTORS = {
    "stegg_f5_encode": execute_f5_encode,
    "stegg_f5_decode": execute_f5_decode,
    ...
}
SCHEMAS = {
    "stegg_f5_encode": {
        "description": "...",
        "inputSchema": { ... },
    },
    ...
}
```

The `__init__.py` merges all families' dicts and validates that every executor has a schema and vice versa.

**Executor pattern:** every executor is an `async` function with signature:

```python
async def execute_<name>(path: str, ..., output_path: str | None = None, **_kw) -> str:
```

Key conventions:
- **Input**: `path` (carrier file), `message` (UTF-8 string payload), `payload_hex` (hex-encoded payload). Exactly one of `message`/`payload_hex` must be provided.
- **File I/O**: `read_bytes(path)` from `_common.py` reads the carrier. `Path(out_path).write_bytes(...)` writes output.
- **Blocking work**: wrapped in `def work():` and dispatched via `await run_sync(work)`.
- **Error handling**: `{"__err__": str}` dicts from `work()` become user-visible error strings. Timeout and exception handlers wrap all async boundaries.
- **Return value**: JSON string from `truncate_json(summary_dict)` with keys `output_path`, `output_bytes`, `config`, `payload_bytes`, and `text` (human-readable one-liner).

**Schema pattern:** inputSchema follows JSON Schema. Every encode tool requires at least `path` (carrier) and `message`/`payload_hex` (payload). Decode tools require only `path`. Output is always written to `output_path` (auto-generated if omitted).

**Tool naming:** `stegg_<domain>_<method>_<operation>`. Operations are `encode`, `decode`, `capacity`, `scan`, `detect`.

### Layer 3: CLI (`m3gast3gg/cli.py`)

Typer command tree with Rich TUI output by default. All major commands accept
`--json` for machine-readable JSON to stdout.

```
stegg encode-cmd  -i IMAGE -t TEXT [-o OUT] [--channels C] [--bits N] [--password P]
stegg decode-cmd  -i IMAGE [-o OUT] [--no-auto] [--password P]
stegg analyze     IMAGE [--full] [--recursive]
stegg detect      IMAGE
stegg capacity    IMAGE [--channels C] [--bits N]
stegg chunks      IMAGE
stegg analysis-tool IMAGE ACTION
stegg list-tools
stegg inject chunk  -i IMAGE -o OUT [--type TYPE] [--keyword K] --text TEXT
stegg inject exif   -i IMAGE -o OUT [--comment C] [--author A] [--custom-fields JSON]
stegg dct encode    -i IMAGE -t TEXT [-o OUT] [--robustness low|medium|high]
stegg dct f5 encode -i JPEG -t TEXT -p PASSWORD [-o OUT]
stegg text encode   --method M --cover COVER --secret SECRET
stegg specter encode -i IMAGE -t TEXT --pattern P1-P2-P3 [-o OUT]
stegg matryoshka embed   -p PAYLOAD -c CARRIER1 -c CARRIER2 [-o OUT]
stegg matryoshka extract IMAGE [-d MAX_DEPTH] [-e EXTRACT_DIR]
stegg info-cmd
```

**Naming convention — matryoshka verbs.** The matryoshka subcommands use
`embed`/`extract`, not `encode`/`decode`.  A single-pass LSB/DCT/F5 operation
*encodes* data into one carrier.  Matryoshka *embeds* a payload by encoding it
through a stack of carriers — every layer is an encode step, but the composite
action is an embedding across the stack.

## Shared primitives

Some modules are neither core nor tool layers — they're shared building blocks:

| Module | Role | Used by |
|---|---|---|
| `m3gast3gg.core.crypto` | AES-256-GCM encrypt/decrypt | `core.img`, `core.jailbreak` |
| `m3gast3gg.core.unicode_tags` | Unicode Tag block (U+E0000-U+E007F) encode/decode | `core.text`, `core.jailbreak` |
| `m3gast3gg.core.specter` | Specter LSB stego (frequency-domain spread spectrum) | MCP `image.py` |
| `m3gast3gg.core.analysis` | File-format parsing, detection, carving | MCP `image.py`, tests |
| `m3gast3gg.core.capabilities` | External tool/packages detection (exiftool, steghide, etc.) | MCP `meta.py` |
| `m3gast3gg.core.operations` | Shared operation layer: plain-Python-type functions that own file I/O, validation, and error-wrapping. Returns dataclasses — callers format for their output channel. | `m3gast3gg.cli`, MCP tools |

These are singletons — they don't follow the encode/decode/detect triple pattern because they're plumbing, not end-user techniques.

## Tests

Tests live in `tests/unit/` and `tests/examples/`. Test fixtures are self-contained: nothing in the test suite should depend on a binary file checked into the repo that isn't explicitly a pinned interop fixture (e.g. JS-generated F5 outputs in `tests/unit/fixtures/f5/jpeg/`). Carrier images needed for roundtrip tests are generated in the fixture with a fixed `RandomState` seed.

## Dependency policy

Optional dependencies are declared in `pyproject.toml` under `[project.optional-dependencies]`:

```toml
jpeg = ["jpeglib>=0.5"]
metadata = ["piexif>=1.1"]
pdf = ["pypdf>=4.0"]
```

Core modules that require optional deps use lazy imports with clear error messages:

```python
try:
    import piexif
except ImportError as exc:
    raise ImportError(
        "EXIF write requires piexif. Install with `pip install stegg[metadata]`."
    ) from exc
```

The base `stegg` install stays "just Pillow + numpy + scapy + rich + typer."

<a id="transforms-vs-steg"></a>
## Text transforms vs text steganography

ST3GG carries two related-but-distinct text surfaces. They share the same
Unicode primitives (`m3gast3gg.core.unicode_tags`, `m3gast3gg.core.crypto`)
but do different jobs — pick the right one for the task or you'll fight
the API.

**Text steganography (`m3gast3gg.core.text`)** — hide a *secret* inside a
*cover*, so a reader sees only the cover. The output looks like the cover
did, plus a hidden payload nobody else notices. Every method has an
`encode(cover, secret) -> str` and `decode(stego) -> str`. Fourteen
methods: zero-width, cyrillic-homoglyph, cjk-homoglyph, whitespace,
invisible-ink, variation, combining, confusable, directional, hangul,
mathbold, braille, emoji, skintone, capitalization. All take a cover +
secret pair; none work on a bare string.

**Text transforms (`m3gast3gg.core.transforms`)** — reshape the *input*
into a different visible form. The output IS the transformed input; there
is no cover, no secret, just a reversible mapping. Every transform is a
`BaseTransformer` with `func(text, **options) -> str` and (usually)
`reverse(text, **options) -> str`. Twenty-six transforms across seven
categories: ciphers (caesar, rot13, atbash, vigenere, bacon), encodings
(base64/32/58, hex, binary, ternary, ascii85, morse, url,
quoted-printable), unicode reshaping (fullwidth, zalgo), concealment
bridges (homoglyph, invisible-text, zero-width), case (uppercase,
lowercase, titlecase), format (reverse, remove-whitespace), visual
(leetspeak).

**Concealment transforms** are the bridge — they wrap steg primitives to
fit the transform contract. `concealment/zero-width.py` takes a text
input and *self-embeds* it in a default cover, so it looks like a
one-arg transform to callers even though the underlying primitive is a
two-arg steg encoder. This is a deliberate ergonomic choice: pipeline
callers (`stegg transform chain`, jailbreak composers) want `f(x) ->
y`, not `f(cover, x) -> y`.

**When to use which:**

- Hiding *this* string inside *that* cover article? → text steg.
- Reshape *this* string into a different visible form (ROT13, Base64,
  fullwidth, ...)? → text transform.
- Building a jailbreak-obfuscation pipeline that ends in a stego
  wrapper? → transforms in the middle, steg at the end.
- "Which encoding is this mystery string?" → `stegg transform
  auto-decode` (`m3gast3gg.core.decoder.universal_decode`) runs the
  detector-gated auto-decoder over the transform registry.

Both surfaces are stable ABI. Neither will "grow into" the other —
they're kept apart because their function signatures don't align, and
merging them would either force covers on transforms (ugly) or drop
covers from steg (silently wrong).

