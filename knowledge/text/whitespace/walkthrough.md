# Whitespace — end-to-end walkthrough

Hide the payload `"hi"` (2 bytes) in a 5-line cover. Encode, view
the trailing whitespace directly, decode.

## Setup

```python
from stegg import text_core

cover = "Line one.\nLine two.\nLine three.\nLine four.\nLine five."
secret = "hi"
```

## Pre-flight capacity

```python
lines = cover.count('\n') + 1                # 5
carrier_bits = 8 * lines                     # 40
prefix = 16
usable = (carrier_bits - prefix) // 8        # 3 bytes
```

3 bytes usable. 2-byte payload fits.

## Encode

```python
stego = text_core.encode_whitespace(cover, secret)
```

Payload `"hi"` = `b"hi"` = `0x68 0x69` = binary:

```
Length prefix (16 bits): 0000 0000 0000 0010     # length = 2
Byte 0 'h' (0x68):        0110 1000
Byte 1 'i' (0x69):        0110 1001
```

Concatenated: `0000000000000010 01101000 01101001` = 32 bits.

Distributed across 5 lines (8 bits per line):

```
Line 0 gets bits  0-7:   00000000 → SP SP SP SP SP SP SP SP
Line 1 gets bits  8-15:  00000010 → SP SP SP SP SP SP TAB SP
Line 2 gets bits 16-23:  01101000 → SP TAB TAB SP TAB SP SP SP
Line 3 gets bits 24-31:  01101001 → SP TAB TAB SP TAB SP SP TAB
Line 4 gets bits 32-... : (no bits left — no trailing)
```

Stego:

```
Line one.        \n     (8 trailing spaces)
Line two.       \n     (7 spaces + tab)      # bit 14 is 1
Line three. \t\t \t   \n
Line four. \t\t \t  \t
Line five.
```

The visible content is byte-identical to the cover. Every character
of `Line one.`, `Line two.`, etc. is unchanged. The stego is
literally invisible until you enable "show whitespace" in your
editor.

## View the stego

```python
for i, line in enumerate(stego.split('\n')):
    trailing = line[len(line.rstrip(' \t')):]
    trailing_repr = trailing.replace(' ', '·').replace('\t', '→')
    print(f"Line {i}: {line.rstrip()!r} + [{trailing_repr}]")
```

Sample output:

```
Line 0: 'Line one.' + [········]
Line 1: 'Line two.' + [······→·]
Line 2: 'Line three.' + [·→→·→···]
Line 3: 'Line four.' + [·→→·→··→]
Line 4: 'Line five.' + []
```

## Decode

```python
recovered = text_core.decode_whitespace(stego)
assert recovered == secret  # 'hi'
```

The decoder:

1. Splits on `\n`.
2. Extracts trailing whitespace from each line.
3. Concatenates: `SPSPSPSPSPSPSPSP + SPSPSPSPSPSPTABSP + SPTABTABSPTABSPSP + SPTABTABSPTABSPTAB + ()`.
4. First 16 bits = `0000000000000010` = length 2.
5. Next 16 bits = `0110100001101001` = `hi`.

## Round-trip test through common transports

```python
# HTTP raw / GitHub / email attachment
# → trailing whitespace preserved byte-identical → decode succeeds ✅

# Slack paste
# → Slack trims trailing whitespace on rendered post → payload lost ❌
# See [[sv-whitespace-slack-paste]]

# Slack snippet (files.upload with snippet_type=text)
# → raw file bytes preserved → decode succeeds ✅
# See [[sv-whitespace-slack-snippet]]

# Git commit
# → depends on .gitattributes / .editorconfig / pre-commit hooks.
#   Many repos strip trailing WS by default. Payload usually lost.

# VSCode default save
# → "Trim Trailing Whitespace on Save" is often on → payload lost
```

The transport story dominates whitespace-steg viability. Ship
through raw-file paths only.

## What would go wrong

| Change | Effect |
|--------|--------|
| Any editor / hook that trims trailing WS | Payload destroyed |
| Cover has < 2 lines | 16-bit length prefix doesn't fit → `TextStegCapacityError` |
| Payload > `(N * 8 - 16) / 8` bytes | `TextStegCapacityError` with explicit "N bits short" |
| Cover has trailing WS ALREADY on some lines | Existing WS becomes part of the bit stream — decode gets garbage |
| Windows CRLF vs Unix LF | Line count same, but the CR may or may not be part of the trailing region depending on how the file's read |
| Decoded length > 10000 | Decoder returns `''` (defensive against corruption) |

## The "obvious-to-tools, invisible-to-people" trade

Whitespace-steg is one of the least perceptually stealthy techniques
against tools:

- `cat -A` shows trailing spaces as `·` and tabs as `^I`.
- `grep -P '[ \t]$'` finds every affected line.
- Any diff of the cover vs stego shows exact trailing patterns.

But it's also one of the least perceptually stealthy against
*humans* — nobody actually renders trailing whitespace in a text
viewer. The paradox: whitespace-steg is invisible to almost every
human reader, obvious to almost every tool.

## Sources

- [[text-whitespace]]
- [[morkovkin-snow]]
- [[sv-whitespace-slack-paste]] / [[sv-whitespace-slack-snippet]]
