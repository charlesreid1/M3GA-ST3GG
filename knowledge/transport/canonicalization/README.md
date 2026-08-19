# The canonicalization principle

**Every transport has a canonical form it treats as "the real message."
Anything you hid *at or above* the canonical form survives; anything
you hid *below* it gets normalized, stripped, or re-encoded out of
existence.**

This is the single principle behind every row of `survival.json`.

## The five canonical forms

- **File bytes** — the transport delivers your file byte-identical.
  Everything survives. Email attachment, HTTP raw, GitHub, Telegram-
  as-file, iMessage attachment, Slack snippet, Slack upload (for
  PNG bytes).
- **Visible glyph stream** — the transport delivers the *visible*
  text, discarding formatting metadata. Terminal mouse-copy is the
  canonical example. Kills zero-width, variation selectors,
  combining marks. See [[myth-vs-terminal]].
- **Rendered post / structural** — the transport delivers a
  rendered representation of your message. Slack paste (rendered
  as `blocks[]`), Discord/iMessage message body. Emoji get
  canonicalized to `:colon_form:`; some metadata slots survive
  the block tree.
- **Perceptual approximation** — the transport re-encodes for a
  target size/format. JPEG recode, WhatsApp photo, Instagram/
  Twitter/most social media. Kills LSB, PVD, direct pixel overwrite.
  May preserve DCT-robust hides and spread-spectrum watermarks.
- **NFC / NFKC** — the transport normalizes Unicode. Some search
  boxes, some DB TEXT columns, aggressive input sanitizers. Kills
  homoglyph-cyrillic (Cyrillic а → Latin a) and cjk_homoglyph
  (fullwidth ， → ASCII ,), some VS, combining marks. See
  [[myth-homoglyph-nfkc]].

## Applying the principle

For every (technique, transport) pair, ask:

1. What is the transport's canonical form?
2. What layer does the technique hide in?
3. Is the technique's layer ≥ (survives) or < (dies) the canonical
   form?

If the technique's layer is *at* the canonical form (e.g. PNG chunk-
level hide when the transport is "PNG bytes"), it survives.

If it's *below* (e.g. PNG named text chunks — a byte-level anchor —
when the transport is Slack's "PNG-with-named-chunks-stripped"), it
dies.

If it's *above* (e.g. pixel-domain LSB when the transport
canonicalizes to a perceptual approximation), it dies too — the
approximation destroys the pixel bits.

## The Slack three-transport lesson

Slack is not one transport; it is *three*:

- `slack_upload` — canonical form is "file bytes Slack re-serves from
  CDN." PNG IDAT byte-identical; JPEG re-encoded; named PNG text
  chunks and EXIF/XMP stripped. See [[transport-slack-upload]].
- `slack_paste` — canonical form is "rendered rich-text post as a
  `blocks[]` tree, ~4000 char cap, emoji as `:colon_form:`." See
  [[transport-slack-paste]].
- `slack_snippet` — canonical form is "raw file bytes with no render
  pipeline, no length cap, no colon-form conversion." Strictly
  stronger than `slack_paste` for text stego. See
  [[transport-slack-snippet]].

Same product, three totally different survival profiles.

## Sources

- [[st3gg-field-guide]] — the canonicalization principle
- [[st3gg-transport-matrix]] — the empirical scoreboard
- [[st3gg-transport-results-slack]] — the 2026-07 Slack probe
