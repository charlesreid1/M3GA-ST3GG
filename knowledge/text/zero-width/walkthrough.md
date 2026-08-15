# Text zero-width — end-to-end walkthrough

Hide `"HIDDEN"` (6 bytes) inside a 2-line cover, byte-hex out.

## Setup

```python
from stegg import text_core
cover = "You reach the crossroads at dusk.\nThe cat picks the north path."
payload = b"HIDDEN"
```

## Encode

```python
stego = text_core.encode_zero_width(cover, payload)
print(len(stego))         # cover length + payload framing
print(stego.encode("utf-8")[-90:].hex())
# ...actual bytes below
```

Under the hood:

1. Convert payload to bits: `HIDDEN` = `48 49 44 44 45 4E` hex
   = `01001000 01001001 01000100 01000100 01000101 01001110` binary
   (48 bits total).
2. Map bit 0 → ZWSP `E2 80 8B`, bit 1 → ZWNJ `E2 80 8C`.
3. Wrap in delimiters: `ZWJ + [48 codepoints] + ZWJ`.
4. Concatenate to cover.

Output shape:

```
"You reach the crossroads at dusk.\nThe cat picks the north path." + ZWJ + [48 codepoints] + ZWJ
```

Byte-hex of the appended payload (tail of stego.encode("utf-8")):

```
e2 80 8d                                    ← ZWJ start
e2 80 8b e2 80 8c e2 80 8b e2 80 8b         ← 0100 = "H" high nibble
e2 80 8c e2 80 8b e2 80 8b e2 80 8b         ← 1000 = "H" low nibble
... (44 more codepoints for the rest of HIDDEN) ...
e2 80 8d                                    ← ZWJ end
```

Total appended bytes: `(1 + 48 + 1) * 3 = 150` bytes.

## Decode

```python
recovered = text_core.decode_zero_width(stego)
assert recovered == b"HIDDEN"
```

Parser:

1. Find first ZWJ (`U+200D`).
2. Read codepoints until the next ZWJ:
   - `U+200B` → bit 0
   - `U+200C` → bit 1
   - anything else → abort (not a valid zero-width stego)
3. Group bits into bytes; return.

## What renders

To a human reading the cover text: **exactly the same as the cover**.
Every zero-width codepoint renders as nothing. The cursor advances zero
pixels for each.

To a hex viewer or `cat -A`: a run of `E2 80 8B` / `E2 80 8C` / `E2 80 8D`
bytes after the visible content. Loud in a hex dump; invisible on the
page.

## What would go wrong

| Change | Effect |
|--------|--------|
| User pastes stego through Terminal.app mouse-copy | Zero-width codepoints stripped by the terminal glyph filter; use `pbcopy` instead |
| Cover passes through `.strip()` in Python | Trailing whitespace removed but zero-width chars survive `.strip()` (they aren't in the default whitespace set) |
| Cover passes through NFKC | Zero-width chars are preserved by NFKC; payload survives |
| Cover passes through a search input that strips ZWSP | Payload dies — this is why aggressive input sanitizers matter |
| Slack paste | Survives ([[sv-zero-width-slack-paste]]) |
| Slack snippet | Survives ([[sv-zero-width-slack-snippet]]) |
| WhatsApp text message | Believed to survive (text-family HTTP raw analogy) — [[known-unknowns]] |

## Detection walkthrough — spot the hide as a defender

```python
from stegg.text_core import detect_unicode_steg
result = detect_unicode_steg(stego)
# {"hit": True, "method": "zero_width", "codepoint_run_length": 48, ...}
```

Or eyeball for the byte pattern in a hex viewer: a dense run of
`E2 80 8B` / `E2 80 8C` bytes is the signature.

## Sources

- [[text-zero-width]]
- [[cap-text-zero-width]]
- [[unicode-tr36-security]]
