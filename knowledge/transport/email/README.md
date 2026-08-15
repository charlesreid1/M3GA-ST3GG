# Email — attachment vs inline

Two distinct email sub-transports: attachments (byte-identical) and
inline images (may be recoded).

## The two sub-transports

- **`email_attachment`** ([[transport-email-attachment]]) —
  file attached as MIME multipart. Canonical form: file bytes.
  Byte-identical for both source and destination MTAs that don't
  re-encode attachments (essentially all of them for arbitrary
  files).
- **`gmail_inline`** ([[transport-gmail-inline]]) — image embedded
  inline in the message body. Canonical form: perceptual
  approximation (Gmail resizes / re-encodes large inline images
  for view speed).

## Where things survive

- **Email attachment**: everything. LSB, PVD, DCT-domain hides,
  trailing bytes, EXIF, private chunks — all pass through.
  Byte-identical delivery.
- **Gmail inline** for small images (below some undocumented size
  threshold): byte-identical.

## Where things die

- **Gmail inline** for large images: re-encoded, resized. Kills LSB,
  metadata, trailing bytes.
- **Some MTAs with content-scanning gateways** (enterprise anti-
  malware) may modify attachments — usually just add scanning
  metadata, but occasionally re-serialize archives.

## The `Content-Transfer-Encoding: 7bit` gotcha

Old-school email transfer encodings (base64, quoted-printable) are
lossless as long as the MTA handles them correctly. Modern SMTP
extensions (`8BITMIME`, `BINARYMIME`) allow raw 8-bit bodies. The
byte-identity claim assumes conforming MTAs; some legacy relays
still line-wrap or rewrite headers.

## Detection

- Email forensics tools (Autopsy, MailXaminer) walk MIME structure
  and every part is inspectable.
- Attached-file steganalysis proceeds as if the file arrived directly.

## Sources

- RFC 5321 — SMTP
- RFC 2045 — MIME
- [[st3gg-transport-matrix]] — matrix cells
- [[st3gg-field-guide]] — canonicalization principle
