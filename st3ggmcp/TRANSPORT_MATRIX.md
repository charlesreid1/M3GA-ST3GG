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

The table below is generated from `knowledge/records/survival.json` by
`scripts/render_transport_matrix.py`. Every non-`❓`/non-`➖` cell corresponds
to exactly one survival record — look one up with `stegg_verify_survival(technique, transport)`,
or grep the record id under the table.

<!-- BEGIN autogen: transport matrix -->
<!-- Generated by scripts/render_transport_matrix.py — do not edit by hand. -->

| Technique | Slack (upload) | Slack (paste) | Slack (snip) | Discord (up) | Discord (paste) | TG (photo) | TG (file) | WA (photo) | WA (doc) | Signal | iMsg (photo) | iMsg (attach) | Email | Gmail inline | GitHub | HTTP raw | Terminal | pbcopy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `image-lsb` | ✅ | ➖ | ➖ | ❓ | ➖ | ❓ | ❓ | ❌ | ❓ | ❓ | ❓ | ❓ | ✅ likely | ❓ | ✅ likely | ✅ | ➖ | ➖ |
| `image-matryoshka` | ✅ | ➖ | ➖ | ❓ | ➖ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ➖ | ➖ |
| `image-dct` | ⚠ tuned only | ➖ | ➖ | ❓ | ➖ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ➖ | ➖ |
| `image-f5` | ❌ | ➖ | ➖ | ❓ | ➖ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ➖ | ➖ |
| `image-jsteg` | ❌ | ➖ | ➖ | ❓ | ➖ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ➖ | ➖ |
| `image-gif-comment` | ✅ | ➖ | ➖ | ❓ | ➖ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ➖ | ➖ |
| `image-png-private-chunk` | ✅ | ➖ | ➖ | ❓ | ➖ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ➖ | ➖ |
| `image-png-text-chunk` | ❌ | ➖ | ➖ | ❓ | ➖ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ➖ | ➖ |
| `image-trailing-bytes` | ❌ | ➖ | ➖ | ❓ | ➖ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ➖ | ➖ |
| `text-braille` | ❓ | ✅ | ❓ | ❓ | ❓ | ➖ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ✅ | ❓ | ❓ |
| `text-cjk-homoglyph` | ❓ | ✅ | ❓ | ❓ | ❓ | ➖ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ✅ | ❓ | ❓ |
| `text-combining` | ❓ | ✅ | ❓ | ❓ | ❓ | ➖ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ✅ | ❓ | ❓ |
| `text-confusable` | ❓ | ✅ | ❓ | ❓ | ❓ | ➖ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ✅ | ❓ | ❓ |
| `text-cyrillic-homoglyph` | ❓ | ✅ | ✅ | ❓ | ❓ | ➖ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ✅ | ❓ | ❓ |
| `text-directional` | ❓ | ✅ | ✅ | ❓ | ❓ | ➖ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ✅ | ❓ | ❓ |
| `text-hangul` | ❓ | ✅ | ❓ | ❓ | ❓ | ➖ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ✅ | ❓ | ❓ |
| `text-invisible-ink` | ❓ | ❌ recoded | ✅ | ❓ | ❓ | ➖ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ✅ | ❓ | ❓ |
| `text-mathbold` | ❓ | ✅ | ❓ | ❓ | ❓ | ➖ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ✅ | ❓ | ❓ |
| `text-variation` | ❓ | ✅ | ❓ | ❓ | ❓ | ➖ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ✅ | ❓ | ❓ |
| `text-zero-width` | ❓ | ✅ | ✅ | ❓ | ❓ | ➖ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ✅ | ⚠ terminal-dependent | ❓ |
| `text-capitalization` | ❓ | ✅ | ❓ | ❓ | ❓ | ➖ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ✅ | ❓ | ❓ |
| `text-whitespace` | ❓ | ❌ recoded | ✅ | ❓ | ❓ | ➖ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ✅ | ❓ | ❓ |
| `emoji-skintone` | ❓ | ⚠ colon-form-lossy | ❓ | ❓ | ❓ | ➖ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ✅ | ❓ | ❓ |
| `emoji-tag-sequence` | ❓ | ❌ | ✅ likely | ❓ | ❓ | ➖ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ✅ | ❓ | ❓ |
| `text-emoji-substitution` | ❓ | ✅ | ✅ | ❓ | ❓ | ➖ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ❓ | ➖ | ❓ | ✅ | ❓ | ❓ |

Legend: `✅` survives · `❌` stripped/destroyed · `⚠` conditional (see caveat) · `❓` untested · `➖` nonsensical combination.

### Cell provenance

Every non-`❓`/non-`➖` cell above maps to a survival record — look up with `stegg_verify_survival(technique, transport)`, or find the record id below.

- `sv-braille-slack-paste` — text-braille × transport-slack-paste · tested 2026-07-25
- `sv-capitalization-slack-paste` — text-capitalization × transport-slack-paste · tested 2026-07-25
- `sv-cjk-slack-paste` — text-cjk-homoglyph × transport-slack-paste · tested 2026-07-25
- `sv-combining-slack-paste` — text-combining × transport-slack-paste · tested 2026-07-25
- `sv-confusable-slack-paste` — text-confusable × transport-slack-paste · tested 2026-07-25
- `sv-cyrillic-slack-paste` — text-cyrillic-homoglyph × transport-slack-paste · tested 2026-07-25
- `sv-cyrillic-slack-snippet` — text-cyrillic-homoglyph × transport-slack-snippet · tested 2026-07-25
- `sv-dct-slack-upload` — image-dct × transport-slack-upload · tested 2026-07-25
- `sv-directional-slack-paste` — text-directional × transport-slack-paste · tested 2026-07-25
- `sv-directional-slack-snippet` — text-directional × transport-slack-snippet · tested 2026-07-25
- `sv-emoji-slack-paste` — text-emoji-substitution × transport-slack-paste · tested 2026-07-25
- `sv-emoji-slack-snippet` — text-emoji-substitution × transport-slack-snippet · tested 2026-07-25
- `sv-emoji-tag-slack-paste` — emoji-tag-sequence × transport-slack-paste · tested 2026-07-25
- `sv-emoji-tag-slack-snippet` — emoji-tag-sequence × transport-slack-snippet · tested 2026-07-25
- `sv-f5-slack-upload` — image-f5 × transport-slack-upload · tested 2026-07-25
- `sv-gif-comment-slack-upload` — image-gif-comment × transport-slack-upload · tested 2026-07-25
- `sv-hangul-slack-paste` — text-hangul × transport-slack-paste · tested 2026-07-25
- `sv-invisible-ink-slack-paste` — text-invisible-ink × transport-slack-paste · tested 2026-07-25
- `sv-invisible-ink-slack-snippet` — text-invisible-ink × transport-slack-snippet · tested 2026-07-25
- `sv-jsteg-slack-upload` — image-jsteg × transport-slack-upload · tested 2026-07-25
- `sv-lsb-email-attachment` — image-lsb × transport-email-attachment · tested —
- `sv-lsb-github-upload` — image-lsb × transport-github-upload · tested —
- `sv-lsb-http-raw` — image-lsb × transport-http-raw · tested —
- `sv-lsb-slack-upload` — image-lsb × transport-slack-upload · tested 2026-07-25
- `sv-lsb-whatsapp-photo` — image-lsb × transport-whatsapp-photo · tested —
- `sv-mathbold-slack-paste` — text-mathbold × transport-slack-paste · tested 2026-07-25
- `sv-matryoshka-slack-upload` — image-matryoshka × transport-slack-upload · tested 2026-07-25
- `sv-png-private-chunk-slack-upload` — image-png-private-chunk × transport-slack-upload · tested 2026-07-25
- `sv-png-textchunk-slack-upload` — image-png-text-chunk × transport-slack-upload · tested 2026-07-25
- `sv-skintone-slack-paste` — emoji-skintone × transport-slack-paste · tested 2026-07-25
- `sv-text-http-raw` — text (family) × transport-http-raw · tested —
- `sv-trailing-bytes-slack-upload` — image-trailing-bytes × transport-slack-upload · tested 2026-07-25
- `sv-variation-slack-paste` — text-variation × transport-slack-paste · tested 2026-07-25
- `sv-whitespace-slack-paste` — text-whitespace × transport-slack-paste · tested 2026-07-25
- `sv-whitespace-slack-snippet` — text-whitespace × transport-slack-snippet · tested 2026-07-25
- `sv-zero-width-slack-paste` — text-zero-width × transport-slack-paste · tested 2026-07-25
- `sv-zero-width-slack-snippet` — text-zero-width × transport-slack-snippet · tested 2026-07-25
- `sv-zero-width-terminal-stdout` — text-zero-width × transport-terminal-stdout · tested —

<!-- END autogen: transport matrix -->

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
