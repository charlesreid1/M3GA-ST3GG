# Known unknowns

This file is the honesty signal that separates a real KB from a Wikipedia
paraphrase. Every claim listed below is something ST3GG *acts on* in the
field guide, the record layer, or the tool schemas, **without** having
tied it to a primary source or a first-party ST3GG measurement. Some are
folklore, some are half-tested, some are extrapolated from a related fact
we do have. Fix by (a) running a probe and adding a survival record, or
(b) finding a primary citation and adding it to `bibliography.json`.

Format: one bullet per claim, followed by why it's unresolved and what
would resolve it.

## Transport survival — measured cells vs extrapolated cells

- **Discord upload / paste / snippet**. `transports.json` carries entries
  for Discord upload and paste with `confidence: community`, but there is
  no first-party survival cell — every Discord column in the matrix is
  `❓`. Resolve by running the same probe set we used for Slack
  (`TRANSPORT_RESULTS_SLACK.json` pattern) against a Discord bot and
  landing the results in `survival.json`.
- **Telegram photo vs file recode behavior**. We rate `telegram_photo` as
  perceptual-approximation and `telegram_file` as file-bytes based on
  documented behavior, not first-party probes. Corner cases (e.g. does
  photo mode preserve PNG when the client detects PNG?) are unresolved.
  Resolve with a Telegram bot round-trip on each carrier family.
- **WhatsApp photo destruction of LSB**. `sv-lsb-whatsapp-photo` cites
  "WhatsApp photo mode re-encodes JPEGs and destroys pixel-level payload"
  with `tested_at: null`. The claim is well-known but we haven't run our
  own probe. Resolve with an SMTP-attached round-trip test through
  WhatsApp Business API.
- **iMessage HEIC transcode behavior**. `transport-imessage-photo` notes
  "HEIC transcode on some device pairs" — we don't know the exact
  triggering conditions (iOS version pairing? file size?). Resolve with a
  device-pair matrix.
- **Signal EXIF strip behavior**. `transport-signal-attachment` claims
  EXIF is stripped from images-as-attachment as a privacy default. Signal
  changed this behavior at some point; we don't have the version.
  Resolve by chasing Signal changelog.
- **Gmail inline vs attachment recompression thresholds**. `transport-gmail-inline`
  hand-waves about "large inline images may be re-encoded for size". Size
  threshold, format triggers, and CDN caching behavior all unresolved.

## Technique survival details

- **PVD survives / dies on Slack upload**. We have no survival record for
  `image-pvd × transport-slack-upload`. Predicted survival based on
  "Slack IDAT byte-identical → any pixel-domain hide survives" but not
  probed. Resolve with a PVD round-trip through the Slack test harness.
- **PNG matryoshka survives deep nesting on any recoding transport**.
  Depth-11 is tested on Slack upload (`sv-matryoshka-slack-upload`) but
  we haven't asked what happens if any intermediate layer's image gets
  recompressed. Resolve with a mixed-transport chain.
- **Emoji tag sequences via `slack_snippet`**.
  `sv-emoji-tag-slack-snippet` is marked `confidence: community` because
  it's predicted from the snippet-preserves-text pattern, not directly
  probed. Resolve with a direct snippet round-trip.
- **Terminal survival of variation selectors / combining marks / hangul**.
  `transport-terminal-stdout` claims these die but we only have a
  first-party record for zero-width (`sv-zero-width-terminal-stdout`).
  Resolve with a per-technique terminal round-trip on macOS Terminal,
  iTerm2, gnome-terminal, and Windows Terminal.
- **Whitespace steg on `slack_snippet` vs `slack_paste`**. We have both
  cells confirmed. But we haven't tested what happens if the snippet is
  copy-pasted out of the Slack UI (does the UI collapse trailing
  whitespace on select-copy?). Resolve with a UI-level probe.

## Detectors

- **StegExpose false-positive rate on Alaska2 images**. We claim
  StegExpose is an ensemble scanner suitable for triage; we don't cite a
  quantitative FPR against a known-clean corpus. Resolve by running
  StegExpose over Alaska2's clean cover set and recording the base rate.
- **F5 detector calibration on modern JPEG toolchains**. `stegdetect`
  and Aletheia both target F5; we don't know how well either performs
  against JPEGs re-encoded by modern (post-2020) libjpeg-turbo settings.
  Resolve by running both against a mod-2024 encoder corpus.
- **Bit-plane entropy thresholds**. The field guide's signature records
  cite "~2-4" for uncompressed ASCII and "~7.9-8.0" for encrypted /
  compressed. These are ST3GG-lore ranges; not tied to a controlled
  measurement across cover images. **Partial resolution (2026-08):** the
  two signature records now downgrade `strength` from `strong` to
  `moderate`, add a `threshold_provenance` field explaining the range's
  heuristic origin, and cross-reference this file. Actual measurement
  still pending.

## Technique claims

- **Blue-channel LSB stealth argument**. `field_guide.md` cites BT.601
  luminance weights (0.11 for blue vs 0.30 red / 0.59 green) as the
  reason blue is the stealth default. BT.601 is real; the direct
  application to LSB stealth ("blue LSB is hardest to see") is an
  extrapolation, not a controlled psychophysical result on this exact
  scheme. Resolve by citing a study that measured LSB detectability
  vs channel choice (Fridrich lab has some in this space).
  **Partial resolution (2026-08):** the `image-lsb` record's notes now
  distinguish the perceptual argument (defensible, cites BT.601) from
  the statistical-detectability argument (chi-square/RS/SPA attack all
  three channels regardless of perceptual weighting). Controlled
  psychophysical study still uncited.
- **"Slack could tighten the strip list at any time"**.
  `sv-png-private-chunk-slack-upload` carries this caveat. We don't have
  a specific date or Slack changelog entry justifying it — it's a
  precautionary framing, not a documented incident. Keep the caveat but
  note the provenance.
- **F5 shrinkage overhead of ~5-10%**. Cited in
  `capacity_models.json::cap-image-f5`. This is a textbook ballpark
  (Westfeld 2001 discusses it qualitatively); we haven't measured it on
  a representative cover set with our F5 implementation.
- **DCT robustness=medium survives 10 usable coefs per block**. ~~Also in
  `cap-image-dct`. The coefficient count per block is implementation-
  specific to `img_core.dct_encode`; not a spec claim.~~ **Resolved
  (2026-08).** Direct code inspection of `img_core.dct_encode` showed the
  encoder embeds one bit per 8×8 block at coefficient position (0,1) —
  a single position, invariant across all three robustness settings.
  `cap-image-dct` and `image-dct` records updated: capacity is now
  correctly `(W/8) * (H/8) / 8 - 9` bytes; robustness controls the
  quantization step (10/25/50) of that one coefficient, not the number
  of coefficients used.

## Historical / provenance claims

- **"F5 → nsF5 → HUGO → S-UNIWARD academic lineage"**. ~~Referenced in
  the plan and mentioned in `tool-aletheia`; not explicitly modeled as
  a history record.~~ **Resolved (2026-08).** Written as
  `knowledge/history/f5-lineage.md` with the four-generation arc and
  the "each generation defeats the prior generation's canonical
  attack" pattern.
- **Ange Albertini polyglot catalog**. ~~Cited as `albertini-polyglots`
  in bibliography with a generic URL; not a specific paper reference.
  The polyglot canon is a maintained corpus, not a single paper.~~
  **Resolved (2026-08).** The bibliography record now carries an
  `anchor_artifacts` list pointing at the specific artifacts to cite
  when claims depend on exact bytes: corkami/pocs/mini/polyglots (the
  minimal polyglot suite), Albertini's *Abusing file formats* article
  in PoC||GTFO 0x07 (2015), and *Binary art: byte-level construction*
  in PoC||GTFO 0x08 (2015).
- **Aphex Twin spectrogram anecdote**. ~~`ctf-spectrogram-hide` mentions
  Windowlicker containing his face as a spectrogram in the last minutes.
  This is folklore-adjacent; we should cite either the Aphex Twin
  interview or an audio-forensics writeup.~~ **Resolved (2026-08).** The
  worked_example now names the specific track ("ΔMi−1 = −α ∑n=1N Di[n]"
  from the 1999 Windowlicker EP — the track title is literally the
  delta-modulation equation) and adds a `provenance` field explaining
  the claim is directly reproducible from released audio: any Audacity
  or sox spectrogram view of that track shows the rendered image. No
  longer folklore-adjacent.

## Mode-gate heuristics

- **The five-mode gate at Layer 4**. This taxonomy is authored (ST3GG
  design decision), not cited. It's not wrong, just not backed by an
  external reference — the "known unknown" here is whether the
  observability of the five modes on real user requests matches ST3GG's
  routing. Resolve by logging real request classifications for a period
  and re-checking the buckets.
- **"~75/25 seasoning calibration"** (Layer 6). The exact ratio is a
  design number, not measured. Resolve by A/B on real replies.

## Gaps to fill (things we know we should know)

- **A survival record per technique × transport where it survives.**
  Currently 38 records; ~55 techniques × ~18 transports = ~990 possible
  cells. Umbrella records (`sv-text-http-raw` with `applies_to`) cover a
  swath but not the full grid. The transport matrix legend already
  distinguishes `❓ untested` from real verdicts.
- **Deep per-technique splits.** The full README + reference + walkthrough
  + recognition split now covers 10 techniques: `image/lsb/`,
  `image/f5/`, `image/dct/`, `image/pvd/`, `image/matryoshka/`,
  `text/zero-width/`, `text/homoglyph-cyrillic/`, `text/invisible-ink/`,
  `text/whitespace/`, and `network/dns-tunneling/`. The remaining ~35
  subtopics still only carry an orient README. Next tier for the deep
  split: `image/png-chunks/`, `image/polyglots/`, `image/gif/`,
  `text/variation-selectors/`, `emoji/tag-sequences/`,
  `detection/chi-square/`, `detection/rs-analysis/`,
  `transport/canonicalization/`.

---

Adding to this list is *good*. It's the running audit trail for what
ST3GG doesn't know it doesn't know. If you find a claim in the field
guide or the KR that isn't tied to a citation, add it here first, then
fix it.
