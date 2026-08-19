# Emoji substitution steganography (🔴/🔵)

One bit per emoji using a red/blue circle pair. Overt (nobody thinks
a wall of 🔴🔵🔴🔵 is random) but round-trips everywhere emoji do.

## What the ST3GG implementation does

`text_core.encode_emoji / text_core.decode_emoji`. See
[[text-emoji-substitution]].

Alphabet:

- 🔴 U+1F534 → bit 1
- 🔵 U+1F535 → bit 0

Framing: 16-bit LE length prefix + payload bits as red/blue emoji
block appended after the cover. Capacity: 8 emoji per payload byte
+ 16-bit prefix.

## Where it dies

Rare — Unicode emoji are preserved by essentially every text
pipeline. Failure modes:

- **Emoji-substituting sanitizers** (some corporate chat filters
  swap emoji for text descriptors).
- **Character limits**: a payload requires 8× its size in emoji.
  A tweet-length carrier only fits ~35 bytes.

## Where it survives

- Every UTF-8 pipeline: files, HTTP, chat, email.
- Slack paste ([[transport-slack-paste]]) as long as the receiver
  reads `blocks[]` (emoji canonicalize to `:red_circle:` /
  `:blue_circle:` on `.text` but the color choice survives).

## Detection

- Trivial: unbroken runs of only 🔴 and 🔵.
- Any casual reader spots it immediately.

## Alternatives with more stealth

- [[emoji/skintone]] — 2 bits per emoji, subtler.
- [[emoji/tag-sequences]] — invisible tag chars riding a base emoji.
- Round-trip: red/blue is the safest "just get it there" emoji
  channel; skintone and tag-sequences trade stealth for fragility.

## Sources

- [[st3gg-field-guide]] — ST3GG-specific framing
