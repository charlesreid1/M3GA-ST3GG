# Typed record repository (KR)

JSON arrays, one file per category. Every record is typed, dated,
family-bound, and cited. Load-time validation is strict: empty
`citations[]` or an unresolved bibliography id raises `RecordError` and
the server won't boot.

## Files

- `bibliography.json` — every source anything else cites. Primary
  papers, RFCs, existing repo docs, and community sources with
  provenance.
- `techniques.json` — one record per encode/decode method. Numeric
  `technical_body` (bits per carrier unit, header, prefix scheme,
  capacity formula, stealth class).
- `carrier_formats.json` — file-format specs: PNG chunk grammar, JPEG
  DCT block structure, WAV RIFF, PCAP frame layout.
- `layers.json` — the five canonical steg layers (bit / coefficient /
  character / container / semantic) plus their normalization behavior.
- `transports.json` — messaging / file channels. Each has a
  `canonical_layer`, `known_strips[]`, `known_recodes[]`.
- `survival.json` — (technique, transport) cross-product with
  `status ∈ {✅, ❌, ⚠, ❓}`, `evidence`, `tested_at`.
- `detectors.json` — chi-square, RS, sample-pairs, bit-plane entropy,
  F5 signature scan, StegDetect, PVD detector.
- `signatures.json` — "if you see X, technique is probably Y"
  pattern-diagnosis records, mirroring the field guide's field-guide
  section.
- `capacity_models.json` — numeric formulas per technique, so
  `stegg_capacity(technique, shape)` answers without invoking the
  encoder.
- `external_tools.json` — steghide, jsteg, outguess, StegExpose,
  Aletheia, zsteg, binwalk, foremost, with interop notes.
- `ctf_genres.json` — compound-technique catalog: chained challenges,
  matryoshka, polyglot puzzles, spectrogram hides.
- `myths.json` — explicit false claims to refute
  ("LSB survives JPEG at Q99", "Cyrillic homoglyph survives NFKC").
  Powers `stegg_verify_claim`.

## Envelope (every record)

```json
{
  "id": "kebab-case-unique",
  "name": "human name",
  "aliases": ["other names"],
  "category": "technique | carrier_format | transport | survival | detector | ...",
  "carrier_family": "image | text | emoji | audio | network | document | universal",
  "layer": "bit | coefficient | character | container | semantic | universal",
  "era_bounds": ["YYYY-MM-DD", "YYYY-MM-DD" | null],
  "confidence": "primary | secondary | community | folklore",
  "citations": ["bib-id", "..."],
  "see_also": ["other-record-id"],
  "disputed": { "field": "why it's disputed + competing values" },
  "technical_body": { ... category-specific numeric fields ... }
}
```

Bibliography records themselves omit `citations[]` (they *are* the
citations). Every other record must cite at least one bibliography id.
