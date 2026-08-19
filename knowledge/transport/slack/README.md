# Slack — three transports, three canonical forms

Slack is not one transport; it's three. Each has its own canonical
form, its own strip list, and its own survival profile.

## The three sub-transports

- **`slack_upload`** ([[transport-slack-upload]]) — file attached
  to a message. Canonical form: the file bytes Slack re-serves from
  CDN. PNG IDAT survives byte-identical; JPEG gets recoded; named
  PNG text chunks and EXIF/XMP/IPTC are stripped.
- **`slack_paste`** ([[transport-slack-paste]]) — text in the
  message body. Canonical form: the rendered rich-text post stored
  as a `blocks[]` tree, capped at ~4000 characters of colon-form-
  expanded content. Emoji stored as colon-form (`:red_circle:`,
  `:+1::skin-tone-3:`).
- **`slack_snippet`** ([[transport-slack-snippet]]) — text uploaded
  as a `.txt` / code snippet via `files.upload snippet_type=text`.
  Canonical form: raw file bytes. No rendering pipeline, no length
  cap, no colon-form conversion.

## Which one when

- **PNG LSB / PNG private chunks** → `slack_upload`. IDAT is
  byte-identical; private chunks survive; named text chunks and
  EXIF do NOT (see [[myth-slack-preserves-metadata]]).
- **Zero-width / homoglyph text**, ≤4000 chars → either
  `slack_paste` or `slack_snippet`. Snippet is stricter (byte-
  identical); paste is the natural in-thread channel.
- **Emoji tag-sequences / skintone modifiers** → `slack_snippet`
  ONLY. Slack paste canonicalizes emoji, dropping tag chars and
  modifier bits. See [[myth-emoji-tag-survives-paste]].
- **Whitespace / SNOW-style** → `slack_snippet`. Paste trims
  trailing whitespace; snippet preserves it. See
  [[sv-whitespace-slack-paste]] vs [[sv-whitespace-slack-snippet]].
- **JPEG steg (F5, jsteg, OutGuess)** → mostly dies. Slack re-encodes
  JPEGs. Tuned DCT can survive at ⚠ level. See
  [[sv-f5-slack-upload]], [[sv-jsteg-slack-upload]],
  [[sv-dct-slack-upload]].

## What we know first-hand

The empirical Slack probe (2026-07-26,
[[st3gg-transport-results-slack]]) established byte-identical PNG
IDAT preservation, named-chunk stripping, EXIF stripping, private-
chunk pass-through, emoji canonicalization to colon-form, and
paste-length cap at ~4000. Every survival record with citation
`st3gg-transport-results-slack` is grounded in that probe.

## What we don't know

Discord upload / paste / snippet — the plan calls for a matching
probe. See [[known-unknowns.md]].

## Sources

- [[st3gg-transport-results-slack]] — the 2026-07 probe results
- [[st3gg-transport-matrix]] — full transport matrix
- [[st3gg-field-guide]] — canonicalization principle applied to Slack
