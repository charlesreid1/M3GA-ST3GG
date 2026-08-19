# Emoji steganography

Emoji as a carrier. Emoji are UTF-8 codepoints — everything here
inherits from [[text/README]], but the carrier's shape (base emoji ±
modifiers ± tag chars) is expressive enough to deserve its own
family.

## Techniques

- **[[text-emoji-substitution]]** — 🔴 = 1, 🔵 = 0, appended as a
  block after the cover. Overt but bulletproof round-trip.
- **[[emoji-skintone]]** — 2 bits per human-emoji carrier via the
  four skintone modifiers (U+1F3FB..U+1F3FE). Subtler than 🔴/🔵.
- **[[emoji-tag-sequence]]** — black-flag base + ASCII-shadow tag
  chars + cancel-tag. Invisible; the technique behind the 2024–2026
  hidden-prompt-injection wave. Dies to Slack paste
  ([[myth-emoji-tag-survives-paste]]), survives Slack snippet
  ([[sv-emoji-tag-slack-snippet]]).

## Slack retrieval gotcha

Slack stores emoji in two places:
- `blocks[].rich_text_section.elements[]` (authoritative — raw
  codepoints preserved).
- `.text` (rendered — `:colon_form:` with modifiers/tag chars
  compressed away).

If a receiver reads `.text`, VS-16 / skintone modifier bits / tag
chars all disappear. See [[transport-slack-paste]] and
[[sv-skintone-slack-paste]] for the exact behavior.
