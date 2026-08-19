# PDF steganography

PDF is an especially generous carrier: metadata streams, XMP, object
comments, post-`%%EOF` trailer bytes, and incremental updates all
carry arbitrary payloads. The dumbest smuggles land here.

## What ST3GG implements

`document-pdf-post-eof` — post-EOF trailer bytes. See
[[document-pdf-post-eof]]. Full PDF-object-level tooling is
`stegg[pdf]` optional-extra territory; capability-check before
relying on it.

## The PDF payload catalog

- **Post-`%%EOF` bytes** — readers scan for the LAST `%%EOF` and
  ignore trailing garbage. Simplest smuggle. See
  [[document-pdf-post-eof]].
- **XMP metadata packet** — RDF/XML embedded inline. Effectively
  unbounded capacity.
- **Info dictionary** — `Title`, `Author`, `Subject`, `Keywords`,
  `Creator`, `Producer`. Short capacity, easy to inspect.
- **Object streams** — every PDF object is a stream; comments
  (%-prefixed lines) inside object streams are ignored by parsers.
- **Incremental updates** — appended XRef sections. A single PDF
  file can contain multiple document revisions; older revisions are
  reachable via cross-reference chasing.
- **Free-object marks** — objects marked free in the XRef table can
  still contain byte content that's unreachable via normal object
  lookup but visible with `strings`.

## Where it survives

- **HTTP raw, GitHub, email attachment**: byte-identical.
- **Slack upload** (file attachment path): pass-through for PDFs
  (Slack doesn't re-serialize PDFs the way it does JPEGs).

## Where it dies

- **PDF re-serializers**: `qpdf --linearize`, `pdftk output`,
  Ghostscript re-render. Any of these rewrite the file structure
  and typically drop post-EOF garbage, comments, and free-object
  content.
- **PDF-to-PDF/A conversion**: strips extended metadata and
  compresses to a normalized form.

## Detection

- `pdfid` (Didier Stevens) — high-level object counts.
- `peepdf` — object-tree browser.
- `qpdf --json` — full structural dump.
- `strings` — catches ASCII payloads in any slot.

## The malware-doc connection

PDF steganography and PDF-borne malware overlap. `pdfid` and `peepdf`
were built for the latter and are equally useful for the former.

## Sources

- [[iso-32000-pdf]] — PDF spec (ISO 32000)
- [[st3gg-field-guide]] — ST3GG-specific tooling
- Didier Stevens's PDF-analysis posts (SANS ISC)
