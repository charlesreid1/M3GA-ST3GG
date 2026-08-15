# Invisible ink — 15-second triage

"Is this text an invisible-ink hide?"

## The two-second discriminator

**Count codepoints in the range `U+E0000..U+E007F`**:

```python
from unicode_tags import count_tags
n = count_tags(text)
```

- `n = 0` — no tag-block characters. Not an invisible-ink hide.
  (Doesn't rule out other techniques.)
- `n ≥ 2` — a tag-block payload is present (minimum: start
  sentinel + terminator; usually payload bytes between them).

Any non-zero count in text that shouldn't have Plane 14 codepoints
is a strong signal. Real user text almost never contains tag
codepoints — they were originally spec'd for language tagging
(deprecated) and are only in wide use for emoji subdivision flags
(gbeng, gbsct, gbwls).

## The subdivision-flag confound

The one legitimate use of tag codepoints is emoji subdivision flags
like 🏴󠁧󠁢󠁥󠁮󠁧󠁿 (England). Rule out this case before flagging:

```python
# A subdivision flag is a base emoji (usually 🏴 U+1F3F4) followed
# by exactly 3-6 tag codepoints matching a subdivision code, then
# the CANCEL TAG.
def looks_like_subdivision_flag(text):
    # Simplified — real check is more nuanced
    return "\U0001F3F4" in text and count_tags(text) <= 7
```

If the tag codepoints are attached to a `🏴` base emoji and there
are ≤7 of them, it's likely a subdivision flag, not a steg
payload. Beyond that, treat as suspicious.

## Signal cheat sheet

| Signal | Diagnosis |
|--------|-----------|
| `count_tags(text) > 7` | Almost certainly a steg payload; count == length of hidden ASCII + 2 |
| Tag codepoints without a `🏴` base emoji | Steg payload; not a subdivision flag |
| Multiple START (`U+E0000`) sentinels | Multi-payload or ST3GG-format wrapped payload |
| Tag codepoints scattered throughout, not in a run | Unusual — check for a splicing pattern |
| Text ends with an unmatched `U+E0000` (no `U+E007F`) | Truncated / corrupted payload |
| Text has `U+E0000..U+E001F` range codepoints | Non-printable ASCII in the payload — could be control bytes, uncommon |

## Practical detection flow

1. **Byte-scan the file / text for the Plane 14 range**. `hexdump
   -C file.txt | grep -E "f3 a0 (80|81)"` — the UTF-8 encoding of
   `U+E0000..U+E007F` starts with `F3 A0 80..81`.
2. **Run `decode_invisible_ink(text)`**. If it returns non-empty
   ASCII, extraction complete.
3. **Try `strip_tags(text)`** to see the visible cover without the
   payload — useful for the CTF write-up.

## Practical decoder shortcuts

```python
from unicode_tags import decode_tag_run

# Standard invisible_ink format (start sentinel + terminator):
decode_tag_run(text, require_start_sentinel=True,
               stop_on_terminator=True, printable_only=False)

# Prompt-injection jailbreak format (no start sentinel, terminator):
decode_tag_run(text, require_start_sentinel=False,
               stop_on_terminator=True, printable_only=True)

# Raw tag scan (permissive — gets everything):
decode_tag_run(text, require_start_sentinel=False,
               stop_on_terminator=False, printable_only=False)
```

Try all three if the first fails.

## The LLM-detection angle

If the CTF is a prompt-injection challenge:

1. Check the input's tag count.
2. Decode and see what the payload says.
3. Test what happens if that payload is fed to a target model
   (in a sandbox, with rate limits).

Vendor safety-classifiers have (as of 2025-2026) added Plane 14
detection to their moderation stack — the signal is now
well-established.

## Sources

- [[text-invisible-ink]]
- [[unicode-tag-block]]
- [[greenberg-2024-tag-injection]]
- [[myth-unicode-tag-passes-sanitizers]]
