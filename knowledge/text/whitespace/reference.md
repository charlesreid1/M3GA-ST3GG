# Whitespace — reference

Exact numeric spec of ST3GG's `text_core.encode_whitespace /
decode_whitespace`. SNOW-style trailing space/tab encoding.

## Alphabet

- `' '` (`0x20`, ASCII space) → bit `0`
- `'\t'` (`0x09`, ASCII tab) → bit `1`

Only ASCII whitespace, only at end-of-line. Zero use of Unicode
codepoints or invisible characters — the stego is *literally* 1 or
0 encoded as space or tab appended after each line's visible
content.

## Wire format

```
Line 0: <visible line 0><8 trailing space/tab chars>\n
Line 1: <visible line 1><8 trailing space/tab chars>\n
...
Line N-1: <visible line N-1><≤8 trailing chars>
```

The 8 trailing chars per line encode bits contiguously — the
receiver concatenates every line's trailing whitespace, reads the
first 16 bits as a big-endian length, then that-many bytes of
payload (8 bits each).

**No magic, no CRC** — the length prefix is the only framing. A
truncated payload silently returns partial output or `''`.

## Framing detail

The 16-bit length prefix distributes across the first two lines:
line 0 carries bits 0-7, line 1 carries bits 8-15. From line 2
onward, the payload proper begins.

Consequence: the cover MUST have at least 2 lines just to carry
the length prefix, plus `ceil(payload_bytes / 1)` more lines
(each additional line holds 1 payload byte).

## Capacity formula

```
carrier_bits(cover) = 8 * (cover.count('\n') + 1)
usable_bytes        = max(0, (carrier_bits - 16) // 8)
```

Examples:

| Cover lines | Carrier bits | Length prefix | Usable payload bytes |
|-------------|--------------|----------------|-----------------------|
| 3           | 24           | 16             | 1                     |
| 10          | 80           | 16             | 8                     |
| 100         | 800          | 16             | 98                    |
| 1000        | 8000         | 16             | 998                   |

Roughly 1 byte per line of cover.

## Encoder step

For each of `N` lines (index `i` from 0):

1. Take next 8 bits of payload (or fewer for the last line).
2. For each bit `b`: append `' '` if `b == 0` else `'\t'`.
3. Concatenate: `line[i] + trailing_chars`.
4. Re-join with `'\n'`.

If the payload has fewer bits than `8 * (N)`, the last lines get
truncated trailing runs (fewer than 8 chars).

If the payload has MORE bits than `8 * N`, encoder raises
`TextStegCapacityError` with an explicit "N bits short" message.

## Decoder step

For each line in `stego.split('\n')`:

1. `stripped = line.rstrip(' \t')`
2. `trailing = line[len(stripped):]`
3. For each `ch` in trailing:
   - `' '` → append `'0'` to bit stream
   - `'\t'` → append `'1'` to bit stream
   - anything else → ignore (defensive; shouldn't happen in valid
     stego)

Read first 16 bits as length; validate `1 <= length <= 10000`; read
next `length * 8` bits; convert to bytes; decode as UTF-8.

Guard: `length > 10000` → return `''` (defensive against
maliciously-crafted long-length claims).

## Sources

- [[text-whitespace]] — the technique record
- [[morkovkin-snow]] — Matthew Kwan's SNOW paper (1998), the direct
  ancestor
- [[cap-text-whitespace]] — capacity formula record
