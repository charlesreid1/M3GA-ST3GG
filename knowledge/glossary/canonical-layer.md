# canonical layer

**The form a transport treats as "the real message."** Anything you
hid *at or above* the canonical layer survives; anything you hid
*below* it gets stripped, normalized, or re-encoded.

## The five canonical layers

- **File bytes** — email attachment, HTTP raw, GitHub, Slack snippet,
  Slack upload (for PNG bytes).
- **Visible glyph stream** — terminal mouse-copy.
- **Rendered post** — Slack paste, Discord message body.
- **Perceptual approximation** — JPEG re-encoder, WhatsApp photo,
  Instagram.
- **NFC / NFKC-normalized text** — some search boxes, some DB TEXT
  columns.

See [[transport/canonicalization]] for the principle in narrative
form.

## In the KR

Every transport record carries `canonical_layer` as a field in its
`technical_body`. See [[transports]] and the individual transport
records ([[transport-slack-upload]], [[transport-terminal-stdout]],
etc.).

## Related terms

- [[layer]] — where a *technique* embeds. If technique.layer <
  transport.canonical_layer, the technique dies.
- [[stealth-class]] — how perceptible the technique is (orthogonal to
  survival).
