# Invisible ink — reference

Exact numeric spec of ST3GG's `text_core.encode_invisible_ink /
decode_invisible_ink`, built on the tag primitive in `unicode_tags`.

## Codepoint block

Unicode Tags block: `U+E0000..U+E007F` (Plane 14, first row).

| Codepoint     | Role                                    |
|---------------|-----------------------------------------|
| `U+E0000`     | LANGUAGE TAG — used as **START** sentinel |
| `U+E0001..1F` | Not used by ST3GG (reserved / unused ASCII shadows) |
| `U+E0020..7E` | Printable ASCII shadows (space through `~`) |
| `U+E007F`     | CANCEL TAG — used as **END** terminator |

The ASCII shadow map is a straight offset:

```
tag_codepoint = 0xE0000 + ascii_byte
```

So `H` (0x48) becomes `U+E0048`, `e` (0x65) becomes `U+E0065`, etc.
One tag codepoint per payload byte, plus a start sentinel and an
end terminator.

## Wire format

```
+---------+-------------------------+---------+
| START   | ASCII-SHADOW PAYLOAD    | END     |
| U+E0000 | one tag per byte        | U+E007F |
+---------+-------------------------+---------+
```

Payload capacity: 1 codepoint per payload byte + 2 sentinel codepoints.

## What ST3GG's encoder accepts

`text_core.encode_invisible_ink(cover, secret)`:

- **Cover**: any non-empty string. Payload is spliced in after
  `cover[0]` so the visible glyph pattern is unchanged from cover.
- **Secret**: any string. Non-ASCII characters (`ord(ch) >= 128`)
  are **silently dropped** to preserve JS interop; only ASCII bytes
  survive into the shadow.

Under the hood: `encode_tag_run(secret, printable_only=False,
start_sentinel=True, terminator=True)`. Payload bytes 0x00-0x7F
are all valid (control chars included).

## What ST3GG's decoder returns

`text_core.decode_invisible_ink(stego)`:

- **Require start sentinel** (`U+E0000`) — decode begins after
  spotting it. Text before the sentinel is ignored.
- **Stop on terminator** (`U+E007F`) — decode ends at the first
  CANCEL TAG.
- **`printable_only=False`** — accepts the full 0x00-0x7F range,
  not just printable.

Under the hood: `decode_tag_run(stego,
require_start_sentinel=True, stop_on_terminator=True,
printable_only=False)`.

## The jailbreak variant

`jailbreak_core.compose_unicode_tag_jailbreak` uses a stricter
configuration on the same primitive:

- `printable_only=True` — restricts payload to 0x20-0x7E only. Any
  control byte in the secret raises `TagPayloadError`.
- No start sentinel — the payload rides directly on a base emoji.
- Terminator conventional (`U+E007F` at end).

Rationale: prompt-injection payloads are always human-readable
prompt text; the printable-only constraint catches malformed input
early rather than pushing control bytes through to the model.

## Capacity formula

```
tag_codepoints = 1 + len(payload_bytes) + 1     # sentinels + payload
utf8_bytes_added = 4 * tag_codepoints           # every tag codepoint is 4 UTF-8 bytes
```

For a 100-byte payload, the stego string grows by 102 codepoints /
408 UTF-8 bytes.

## The strip helper

`unicode_tags.strip_tags(text)` removes every `U+E0000..U+E007F`
codepoint — the canonical defender sanitizer. Every input pipeline
that shouldn't accept tag payloads should apply this filter.

`unicode_tags.count_tags(text)` is the detector primitive: any
non-zero count in a text that shouldn't have tag codepoints is a
signal.

## Sources

- [[text-invisible-ink]] — the technique record
- [[unicode-tag-block]] — the block spec
- [[greenberg-2024-tag-injection]] — the 2024 prompt-injection wave
