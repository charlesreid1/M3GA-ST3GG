# Steg Transport Survival Matrix

Which steganography techniques survive which consumer messaging / file-transport channels? Real transports strip metadata, re-encode images, canonicalize Unicode, and mangle files in undocumented ways. This matrix records what does and doesn't survive, so that:

- CTF authors picking a distribution channel know what won't survive it.
- Steg tool builders know which techniques are actually usable through a given transport.
- Users trying to smuggle a payload through a channel can pick a technique that arrives intact.
- Defensive teams know what an adversary can still push through sanctioned tools.

## The one principle behind every row

Every transport has a **canonical form** it treats as "the real message." Anything you hid *at or above* the canonical form survives; anything you hid *below* it gets normalized, stripped, or re-encoded out of existence. The rows below are just instances of this one principle:

- **Slack has three distinct transports, not one.** Each has its own canonical form:
  - **`slack_upload`** (file attached to a message) canonicalizes to *the file bytes Slack re-serves from CDN*. PNG IDAT survives byte-identical; JPEG gets recoded; named PNG text chunks and EXIF/XMP/IPTC are stripped.
  - **`slack_paste`** (text in the message body) canonicalizes to *the rendered rich-text post* stored as a `blocks` tree, capped at ~4000 characters of colon-form-expanded content. **Emoji are stored as colon-form (`:red_circle:`, `:+1::skin-tone-3:`)** — anything a receiver reconstructs from raw codepoints (VS-16, skintone modifier bits, tag-block payloads riding an emoji) is downstream of that canonicalization and is unrecoverable if the consumer reads the rendered form.
  - **`slack_snippet`** (text uploaded as a .txt/code snippet via `files.upload snippet_type=text`) canonicalizes to *the raw file bytes*. No rendering pipeline, no length cap, no colon-form conversion — the strictly stronger channel for text stego whenever "attach as a snippet" is acceptable UX.
- **Discord / iMessage bodies** canonicalize to the *rendered post*. Same class of behavior as `slack_paste` — emoji canon, metadata strip, image CDN re-serving.
- **Terminal stdout + manual mouse-copy** canonicalizes to the *visible glyph stream*. → Kills zero-width, VS, combining marks. `pbcopy` / `xclip` / `clip.exe` bypass the canonicalization by preserving the byte stream directly.
- **JPEG re-encode / WhatsApp photo / Instagram** canonicalize to a *perceptual approximation*. → Kills LSB, high-nibble embed, direct pixel overwrite. May preserve DCT-robust hides and spread-spectrum watermarks.
- **Email SMTP / raw HTTP / GitHub upload / Telegram-as-file** canonicalize to *the file bytes*. → Everything survives; this is the happy path.
- **Aggressive Unicode normalizers** (some search boxes, some DBs, some sanitizers) canonicalize to *NFC/NFKC*. → Kills cyrillic_homoglyph (Cyrillic `а` normalizes to Latin `a`) and cjk_homoglyph (fullwidth `，` normalizes to ASCII `,`), some VS, combining marks.

Read every cell as: "does this transport's canonical form sit above or below the layer this technique hides in?"

## Legend

| Symbol | Meaning |
|--------|---------|
| **✅ SURVIVES** | Confirmed to arrive byte-identical or technique-intact. |
| **❌ STRIPPED** | Confirmed to be removed / destroyed at some point in the transport pipeline. |
| **⚠ RECODED** | File bytes are re-encoded; technique may or may not survive depending on specifics. |
| **❓ UNKNOWN** | Not yet tested. Contributions welcome. |
| **➖ N/A** | Combination is nonsensical (e.g. audio steg on a text-only channel). |

Every confirmed cell should link to or reference the specific test that confirmed it. Every UNKNOWN cell is a testing opportunity.

## Carriers (rows)

- **PNG LSB** — hiding in the least significant bits of PNG pixel data.
- **PNG tEXt/iTXt/zTXt** — payload in PNG ancillary text chunks.
- **PNG private chunks** — payload in caller-defined 4-char private PNG chunks.
- **PNG trailing bytes (after IEND)** — appended data past the PNG end marker.
- **JPEG LSB / DCT (F5, jsteg, outguess)** — payload in JPEG quantized DCT coefficients.
- **JPEG EXIF/XMP/IPTC** — payload in JPEG metadata blocks.
- **JPEG trailing bytes (after EOI)** — appended data past the JPEG end marker.
- **Unicode zero-width / homoglyph** — payload as zero-width chars, Latin↔Cyrillic letter swaps (cyrillic_homoglyph), or ASCII↔CJK-fullwidth punctuation swaps (cjk_homoglyph) in text.
- **Emoji tag sequences (U+E0020–E007F)** — payload as tag characters appended to a base emoji (the "black flag with tags" trick).
- **Emoji variation selectors** — payload as VS characters (U+FE00–FE0F, U+E0100–E01EF) on emoji or letters.
- **Whitespace steg (SNOW)** — payload as trailing spaces / tab-vs-space patterns in text.
- **File-container polyglot (PNG-in-ZIP, etc.)** — payload as a valid second-format prefix/suffix.
- **Audio LSB (PCM WAV/AIFF)** — payload in low bits of PCM samples.
- **Audio spectrogram** — payload as an image encoded into the audio's frequency domain.

## Transport channels (columns)

- **Slack (upload)** — file attached to a channel via `files.getUploadURLExternal` + `files.completeUploadExternal`, retrieved via `files.info` → `url_private_download`. File-bytes canonical form.
- **Slack (paste)** — text sent via `chat.postMessage`, retrieved via `conversations.history`. Note: the retrieval `text` field is a truncated colon-form preview capped at 4000 chars; the authoritative form is `blocks[].rich_text_section.elements[]`, which itself caps at ~4000 chars of colon-form-expanded content on the storage side. Text sent in the message body.
- **Slack (snippet)** — text uploaded as a snippet via `files.upload snippet_type=text` (deprecated but still working as of 2026-07), retrieved via `url_private_download` — raw file bytes, no rendering pipeline.
- **Discord** — attachment upload via Discord client or bot.
- **Telegram** — attachment upload; note that Telegram distinguishes "photo" (recoded) vs "file" (raw).
- **WhatsApp** — attachment upload via the mobile client or WhatsApp Web.
- **Signal** — attachment upload via the Signal client.
- **iMessage** — attachment upload via Messages.app.
- **Email attachment** — SMTP attachment (base64 wrapped in MIME).
- **Gmail (inline)** — image embedded in Gmail message body.
- **GitHub upload** — file uploaded via GitHub web UI to a repo.
- **HTTP raw (curl)** — direct file transfer over HTTP, no intermediate service.

## Matrix

Confirmed cells first, unknown cells left for later.

Slack is split across three columns because the three transports behave very differently — see the "Slack: mechanism notes" section below. `➖` in a Slack column means the technique doesn't fit that transport (e.g. text steg can't ride an image upload; image steg has no message-body form).

| Carrier                                | Slack (upload)   | Slack (paste)    | Slack (snippet)  | Discord | Telegram (photo) | Telegram (file) | WhatsApp  | Signal | iMessage | Email attach | Gmail inline | GitHub upload | HTTP raw |
|----------------------------------------|------------------|------------------|------------------|---------|------------------|-----------------|-----------|--------|----------|--------------|--------------|---------------|----------|
| PNG LSB (1–4 bit, any channel/strategy)| ✅               | ➖               | ➖               | ❓      | ⚠ likely recoded | ❓              | ❓        | ❓     | ❓       | ✅ likely    | ❓           | ✅ likely     | ✅       |
| PNG tEXt/iTXt/zTXt                     | ❌               | ➖               | ➖               | ❓      | ❓               | ❓              | ❓        | ❓     | ❓       | ✅ likely    | ❓           | ❓            | ✅       |
| PNG private chunks (e.g. `stEg`)       | ✅               | ➖               | ➖               | ❓      | ❓               | ❓              | ❓        | ❓     | ❓       | ❓           | ❓           | ❓            | ✅       |
| PNG pseudo-EXIF (tEXt-hosted EXIF)     | ❌               | ➖               | ➖               | ❓      | ❓               | ❓              | ❓        | ❓     | ❓       | ❓           | ❓           | ❓            | ✅       |
| PNG trailing bytes (after IEND)        | ❌               | ➖               | ➖               | ❓      | ❓               | ❓              | ❓        | ❓     | ❓       | ❓           | ❓           | ❓            | ✅       |
| PNG matryoshka / SPECTER               | ✅               | ➖               | ➖               | ❓      | ❓               | ❓              | ❓        | ❓     | ❓       | ❓           | ❓           | ❓            | ✅       |
| JPEG DCT (medium/high robustness)      | ⚠ tuned only     | ➖               | ➖               | ❓      | ❓               | ❓              | ❓        | ❓     | ❓       | ❓           | ❓           | ✅ likely     | ✅       |
| JPEG F5 / JSteg                        | ❌               | ➖               | ➖               | ❓      | ⚠ likely recoded | ❓              | ❌ likely | ❓     | ❓       | ❓           | ❓           | ✅ likely     | ✅       |
| JPEG (any baseline/progressive)        | ⚠ recoded        | ➖               | ➖               | ❓      | ⚠ recoded        | ❓              | ❌ recoded| ❓     | ❓       | ✅ likely    | ❓           | ✅ likely     | ✅       |
| JPEG trailing bytes (after EOI)        | ❌               | ➖               | ➖               | ❓      | ❓               | ❓              | ❓        | ❓     | ❓       | ❓           | ❓           | ❓            | ✅       |
| WebP / TIFF (uploaded)                 | ⚠ recoded        | ➖               | ➖               | ❓      | ❓               | ❓              | ❓        | ❓     | ❓       | ❓           | ❓           | ❓            | ✅       |
| BMP / GIF (static) / SVG (uploaded)    | ✅ byte-id       | ➖               | ➖               | ❓      | ❓               | ❓              | ❓        | ❓     | ❓       | ❓           | ❓           | ❓            | ✅       |
| Text file upload (UTF-8, CRLF, nulls)  | ✅ byte-id       | ➖               | ➖               | ❓      | ❓               | ❓              | ❓        | ❓     | ❓       | ✅           | ➖           | ✅            | ✅       |
| Text zero-width                        | ➖               | ✅               | ✅               | ❓      | ➖ text only     | ❓              | ❓        | ❓     | ❓       | ✅           | ✅           | ✅            | ✅       |
| Text cyrillic homoglyph                | ➖               | ✅               | ✅               | ❓      | ➖ text only     | ❓              | ❓        | ❓     | ❓       | ✅           | ✅           | ✅            | ✅       |
| Text CJK homoglyph                     | ➖               | ✅               | ❓                | ❓      | ➖ text only     | ❓              | ❓        | ❓     | ❓       | ✅           | ✅           | ✅            | ✅       |
| Text variation selector                | ➖               | ✅               | ❓                | ❓      | ➖ text only     | ❓              | ❓        | ❓     | ❓       | ✅           | ✅           | ✅            | ✅       |
| Text combining CGJ                     | ➖               | ✅               | ❓                | ❓      | ➖ text only     | ❓              | ❓        | ❓     | ❓       | ✅           | ✅           | ✅            | ✅       |
| Text directional override (RLO/LRO)    | ➖               | ✅               | ✅               | ❓      | ➖ text only     | ❓              | ❓        | ❓     | ❓       | ✅           | ✅           | ✅            | ✅       |
| Text hangul filler                     | ➖               | ✅               | ❓                | ❓      | ➖ text only     | ❓              | ❓        | ❓     | ❓       | ✅           | ✅           | ✅            | ✅       |
| Text math bold                         | ➖               | ✅               | ❓                | ❓      | ➖ text only     | ❓              | ❓        | ❓     | ❓       | ✅           | ✅           | ✅            | ✅       |
| Text braille                           | ➖               | ✅               | ❓                | ❓      | ➖ text only     | ❓              | ❓        | ❓     | ❓       | ✅           | ✅           | ✅            | ✅       |
| Text capitalization                    | ➖               | ✅               | ❓                | ❓      | ➖ text only     | ❓              | ❓        | ❓     | ❓       | ✅           | ✅           | ✅            | ✅       |
| Text confusable whitespace             | ➖               | ✅               | ❓                | ❓      | ➖ text only     | ❓              | ❓        | ❓     | ❓       | ✅           | ⚠ maybe      | ✅            | ✅       |
| Text whitespace steg (SNOW-style)      | ➖               | ⚠ RECODED        | ✅               | ❓      | ➖ text only     | ❓              | ❓        | ❓     | ❓       | ✅           | ⚠ maybe      | ✅            | ✅       |
| Text invisible-ink (Unicode tag block) | ➖               | ⚠ RECODED        | ✅               | ❓      | ➖ text only     | ❓              | ❓        | ❓     | ❓       | ⚠ client-dep | ⚠ client-dep | ✅            | ✅       |
| Emoji substitution (🔴/🔵)             | ➖               | ✅               | ✅               | ❓      | ❓               | ❓              | ❓        | ❓     | ❓       | ✅           | ✅           | ✅            | ✅       |
| Emoji tag sequences (U+E0020–E007F)    | ➖               | ❌               | ✅ likely        | ❓      | ❓               | ❓              | ❓        | ❓     | ❓       | ⚠ client-dep | ⚠ client-dep | ✅            | ✅       |
| Emoji VS-16 modifier bits              | ➖               | ⚠ colon-form     | ✅               | ❓      | ❓               | ❓              | ❓        | ❓     | ❓       | ✅           | ✅           | ✅            | ✅       |
| Emoji skintone modifier bits           | ➖               | ⚠ colon-form     | ✅               | ❓      | ❓               | ❓              | ❓        | ❓     | ❓       | ✅           | ✅           | ✅            | ✅       |
| Text-transform: zalgo                  | ➖               | ✅               | ❓                | ❓      | ➖ text only     | ❓              | ❓        | ❓     | ❓       | ✅           | ✅           | ✅            | ✅       |
| Text-transform: leet                   | ➖               | ✅               | ❓                | ❓      | ➖ text only     | ❓              | ❓        | ❓     | ❓       | ✅           | ✅           | ✅            | ✅       |
| Polyglot (PNG-in-ZIP, etc.)            | ❓ untested      | ➖               | ❓ untested      | ❓      | ❓               | ❓              | ❓        | ❓     | ❓       | ❓           | ❓           | ❓            | ✅       |
| Audio LSB (PCM WAV/AIFF)               | ❓ untested      | ➖               | ➖               | ❓      | ❓               | ❓              | ❓        | ❓     | ❓       | ✅ likely    | ➖ inline    | ✅ likely     | ✅       |
| Audio spectrogram                      | ❓ untested      | ➖               | ➖               | ❓      | ❓               | ❓              | ❓        | ❓     | ❓       | ✅ likely    | ➖ inline    | ✅ likely     | ✅       |

### Slack: mechanism notes for surprising verdicts

Verdicts come from `TRANSPORT_RESULTS_SLACK.json` (60 cells, run 2026-07-25). Only the rows below need mechanism context beyond what the table already says.

**PNG private chunks (`stEg`) SURVIVE while `tEXt/iTXt/zTXt` are STRIPPED.** Slack's strip-list targets *named* ancillary text chunks, not "everything ancillary." Non-standard 4-char chunk types pass through. Working but fragile — Slack could tighten the strip-list.

**JPEG DCT (medium/high robustness) SURVIVED while F5/JSteg did not.** Slack re-quantizes JPEGs on the CDN. F5 and JSteg's DCT patterns don't survive that. The two generic DCT cells that did survive were sized to match Slack's re-encoder — read as "possible with careful tuning," not "reliable."

**Emoji tag sequences (U+E0020–E007F) STRIPPED on paste.** Slack canonicalizes emoji to `:colon_syntax:` on the wire; the receiver renders a fresh emoji with no trailing tag chars. Any payload riding an emoji is downstream of colon-form conversion (see the framing bullet above) — use snippet transport instead.

**Emoji VS-16 / skintone `⚠ colon-form` on paste.** Slack preserves the raw modifier codepoints inside `blocks`. A receiver that reads `msg.text` gets `:+1::skin-tone-3:` and loses the modifier bits. Verdict depends on which retrieval path the receiver takes; snippet transport avoids the ambiguity.

**Whitespace and invisible-ink RECODED on paste, SURVIVE as snippet.** Slack normalizes trailing/repeated whitespace and drops most Unicode tag characters from the message body. Snippet bytes bypass the renderer.

**PNG trailing-bytes STRIPPED, JPEG trailing-bytes effectively STRIPPED.** JPEG trailer bytes may attach in transit but the JPEG re-encode pass destroys them.

**Retrieval gotcha (applies to every paste-path consumer):** `conversations.history` returns a `.text` field that is (a) rendered in `:colon_form:` and (b) capped at 4000 chars. Do not compare against `.text` — walk `blocks[].rich_text_section.elements[]` and read the `unicode` field on emoji nodes to reproduce the on-the-wire content faithfully.

### Terminal stdout: canonical form is the visible glyph

Terminal windows render bytes to glyphs; the user's mouse selection copies the glyphs, not the bytes. Zero-width chars, VS, and combining marks may not survive that path — the terminal filters them from the copy buffer. Clipboard utilities (`pbcopy` on macOS, `xclip -sel clip` / `xsel --clipboard --input` on Linux, `clip.exe` on Windows) copy the byte stream directly and preserve everything. If a hide is dying between "prints in my terminal" and "pastes into my chat", suspect the terminal's glyph canonicalization and pipe through `pbcopy` instead. Same principle as Slack, different canonical layer.

## Test methodology (for adding rows/cells)

To add a confirmed cell, you need three things:

1. **A minimal test file** with a known payload embedded via the carrier technique.
2. **A byte-level diff or extraction check** on the transport-delivered copy.
3. **Evidence** — a row in a machine-readable results file (e.g. `TRANSPORT_RESULTS_SLACK.json`) so the cell is reproducible.

Standard test files ship in `st3ggmcp/tests/transport_probes/` (planned). Each test file has a known-good extractor that reports either "payload recovered" or "carrier mangled beyond recovery."

Rough procedure:

```
1. Take the seed file (e.g. png_lsb_probe.png with LSB payload "TRANSPORT_TEST_v1").
2. Upload through the transport under test.
3. Download the file the transport delivers (from a bot, from Save-As, etc.).
4. Byte-diff against the seed.
5. Run the carrier's extractor on the delivered copy.
6. Cell = ✅ if extractor recovered the payload, ❌ if it didn't, ⚠ if bytes changed but
   the extractor still works, ❓ if the test wasn't run.
```

Cells promoted from ❓ to ✅/❌/⚠ should link to the results-file row that confirmed them.

## Contributing

New rows: propose the carrier + its extractor.
New columns: propose the transport + how to feed test files through it programmatically.
Cell fills: run the seed file through the transport, record the result in the transport's results JSON, PR.

The `❓ likely X` cells are guesses based on documented transport behavior, not confirmed measurements. Treat them as testing priorities, not conclusions.
