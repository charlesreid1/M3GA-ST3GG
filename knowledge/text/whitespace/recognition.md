# Whitespace — 15-second triage

"Is this text a whitespace-steg hide?"

## The one-line discriminator

```bash
grep -P '[ \t]+$' <file>
```

Any line ending in space or tab characters is a potential carrier.
The counter is:

```bash
grep -c -P '[ \t]+$' <file>
```

- **0 lines with trailing WS**: not a whitespace hide.
- **2-100 lines with trailing WS in a small text file**: high
  likelihood of a whitespace hide.
- **N lines with trailing WS where N matches cover size**: almost
  certainly a whitespace hide with `bytes ≈ (N - 2)`.

## Practical decode

```python
from stegg.text_core import decode_whitespace
recovered = decode_whitespace(open("suspect.txt").read())
```

If it returns non-empty text, extraction is complete.

## Signal cheat sheet

| Signal | Diagnosis |
|--------|-----------|
| Text file, every line ends in 4-8 whitespace chars | Almost certainly whitespace-steg |
| Text file, only some lines have trailing WS | Could be residual editor state; run decoder anyway |
| Trailing WS pattern is only spaces (no tabs) | Whitespace-steg encoding all-zero payload, OR unrelated coding style |
| Trailing WS pattern is only tabs | Same but all-one payload — implausible; probably tab-indent style |
| Mix of spaces and tabs at end of lines | Strong whitespace-steg signal |
| Trailing WS on some lines, followed by valid CRLF | Same as above — CRLF is not the stego |
| First two lines' trailing bits interpret to a plausible length | Confirmed whitespace-steg (decoder will succeed) |

## Where it's likely to survive

- Raw file transports (HTTP direct, GitHub raw, email attachment).
- Slack snippet upload (raw bytes).
- File-attach mode of consumer messengers.

## Where it's likely to die

- Anything that runs "trim trailing whitespace" — most editors on
  save, git pre-commit hooks, `.editorconfig` policies.
- Slack paste (rendered post trims).
- Markdown renderers (except 2+ trailing spaces = hard break, which
  the encoder doesn't rely on).

## The visualization trick

To see the payload without decoding:

```bash
cat -A <file>       # shows spaces as $, tabs as ^I
```

Or, in Python:

```python
with open("suspect.txt") as f:
    for i, line in enumerate(f):
        line = line.rstrip('\n')
        stripped = line.rstrip(' \t')
        trailing = line[len(stripped):]
        pattern = trailing.replace(' ', '·').replace('\t', '→')
        print(f"L{i}: {pattern}")
```

Every `·` is a bit 0, every `→` is a bit 1.

## Comparison to other invisible-text techniques

| Technique             | What's added                | Cover shape needed |
|-----------------------|------------------------------|--------------------|
| Whitespace            | trailing SP/TAB              | Multi-line text    |
| Zero-width            | ZWSP/ZWNJ codepoints inline  | Any text           |
| Invisible-ink (tags)  | Plane 14 tag codepoints      | Any text           |
| Variation selectors   | VS-1 after alphanumerics     | ASCII-letter-heavy |

Whitespace-steg is unique in requiring *only ASCII* and *no
Unicode carriers* — an advantage in pipelines that strip
non-ASCII, but a disadvantage in every transport that trims
trailing whitespace.

## Sources

- [[text-whitespace]]
- [[morkovkin-snow]]
- [[sv-whitespace-slack-paste]] / [[sv-whitespace-slack-snippet]]
- [[st3gg-field-guide]]
