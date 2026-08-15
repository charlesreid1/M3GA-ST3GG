# GitHub upload — repo blobs are byte-identical

GitHub stores repository blobs byte-identical (a commit is a Merkle
tree of exact bytes). Nothing is stripped from files added to a
repo; the raw file survives through `git push` and
`raw.githubusercontent.com`.

## What ST3GG calls it

[[transport-github-upload]] — file-bytes canonical form. See
[[myth-github-strips-exif]].

## Where things survive

- **Everything file-level**: LSB, PVD, DCT-domain hides, EXIF/XMP,
  PNG chunks, private chunks, trailing bytes, ZIP comments, PDF
  post-EOF.
- **The raw URL** (`raw.githubusercontent.com/<user>/<repo>/<sha>/<path>`)
  serves the exact bytes stored.

## The Camo image proxy caveat

GitHub's **image rendering** on issues, PRs, and README previews
goes through a proxy called Camo. Camo:

- Caches images by URL for privacy (referer stripping).
- Resizes very large images for view speed.
- Doesn't modify the bytes stored in the repo — Camo is a *rendering*
  proxy, not a repo blob rewriter.

If you serve steg through a README's `![img](path)` reference, the
displayed image may be a resized version. The source blob is still
untouched.

## Where things die

- **`git filter-branch` / BFG repo cleaner**: rewrites history and
  can drop / rewrite files. Applied intentionally.
- **`git lfs migrate`**: moves large files to LFS; the byte pointer
  changes but the underlying blob is preserved.
- **Repo-scanning bots** (Dependabot, code-scanning): may flag
  suspicious binary content but don't modify it.

## Comparison to consumer messengers

The consumer-messenger transports (Slack, WhatsApp, Signal, iMessage,
Discord) all strip metadata or re-encode media by default for
privacy. GitHub does not — repo blobs are a byte-identical channel.

## Detection

- Every file in a repo is directly accessible via `git show <sha>`
  or the raw URL.
- Repo-scanning tools (TruffleHog, gitleaks) scan file contents for
  secrets; they can also flag high-entropy blobs as suspicious.

## Sources

- Git internals docs (git-scm.com) — Merkle-tree blob storage
- [[st3gg-transport-matrix]] — GitHub cells
- [[st3gg-field-guide]] — canonicalization principle
