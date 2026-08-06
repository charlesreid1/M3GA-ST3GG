# Transport survival — the canonicalization principle

**Every transport has a canonical form it treats as "the real
message." Anything you hid at or above that form survives; anything
you hid below it gets normalized, stripped, or re-encoded out of
existence.**

This is the single principle that explains why Slack strips EXIF,
why terminal stdout eats zero-width chars, why Telegram-as-photo
destroys LSB but Telegram-as-file preserves it, why WhatsApp murders
JPEG metadata. They're all the same failure — a canonical layer
that isn't yours.

Ask, for any hide + any pipe: *what does this transport treat as
canonical, and is my payload above or below that line?*

## The five canonical forms

- **File bytes** — HTTP raw, GitHub upload, email attachment,
  Telegram-as-file, WhatsApp document, Signal, Slack upload for
  PNG/BMP/GIF. Everything at every layer survives.
  → [[transport-http-raw]], [[transport-github-upload]],
    [[transport-email-attachment]], [[transport-slack-upload]],
    [[transport-telegram-file]], [[transport-whatsapp-document]].
- **Rendered post** — Slack paste, Discord paste, iMessage body.
  Metadata stripped; emoji canonicalized to colon-form on the wire;
  whitespace / tag-block chars normalized.
  → [[transport-slack-paste]], [[transport-discord-paste]].
- **Perceptual approximation** — WhatsApp photo, Telegram photo,
  Instagram, any lossy JPEG re-encode. Kills [[layer-bit]] payloads
  ([[image-lsb]]); coefficient-domain hides
  ([[image-f5]], [[image-dct]]) survive only if the destination Q
  matches. See [[myth-jpeg-steg-survives-recode]].
  → [[transport-whatsapp-photo]], [[transport-telegram-photo]],
    [[transport-imessage-photo]].
- **Visible glyphs** — terminal stdout + mouse-copy. Filters
  zero-width, some VS, some combining marks.
  → [[transport-terminal-stdout]]. Fix: pipe through
  [[transport-pbcopy]] (or xclip / clip.exe).
- **NFC / NFKC** — some search boxes, aggressive input sanitizers,
  some DB columns. Kills [[text-cyrillic-homoglyph]] and
  [[text-cjk-homoglyph]] under NFKC. See [[myth-homoglyph-nfkc]].

## Slack is three transports

The single most useful thing to know about Slack: it has three
distinct upload paths with three different canonical layers.

- **[[transport-slack-upload]]** — file attached to a channel.
  File-bytes canonical. PNG LSB byte-identical
  ([[sv-lsb-slack-upload]]); JPEG always re-encoded
  ([[sv-f5-slack-upload]]); named text chunks stripped
  ([[sv-png-textchunk-slack-upload]]) but private chunks survive
  ([[sv-png-private-chunk-slack-upload]]).
- **[[transport-slack-paste]]** — text in the message body.
  Rendered-post canonical. 13/15 text techniques survive; whitespace
  and invisible-ink recode ([[sv-whitespace-slack-paste]],
  [[sv-invisible-ink-slack-paste]]).
- **[[transport-slack-snippet]]** — text uploaded as a snippet.
  File-bytes canonical. Everything text-family tested SURVIVES,
  including the two that recode on paste. Strictly stronger than
  paste when "attach as a snippet" is acceptable UX.

## The retrieval gotcha

`conversations.history` returns `.text` (colon-form-rendered,
capped at 4000 chars) alongside `blocks[]`. Do NOT compare against
`.text` — walk `blocks[].rich_text_section.elements[]` and read the
`unicode` field on emoji nodes to see what actually rode the wire.
