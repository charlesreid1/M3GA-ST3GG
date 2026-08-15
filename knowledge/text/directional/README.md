# Text directional-override steganography

Payload as runs of `RLO`/`LRO` overrides bracketed with `PDF` (pop
directional formatting). Same primitive as the IDN homograph filename
attack, repurposed as a payload channel.

## What the ST3GG implementation does

`text_core.encode_directional / text_core.decode_directional`. See
[[text-directional]].

Alphabet:

- `U+202E` RLO (RIGHT-TO-LEFT OVERRIDE) → open bit-1 run
- `U+202D` LRO (LEFT-TO-RIGHT OVERRIDE) → open bit-0 run
- `U+202C` PDF (POP DIRECTIONAL FORMATTING) → close run

Framing: 16-bit LE length prefix + RLO/LRO runs encoding bits.

## Where it dies

- **Any Bidi-aware renderer**: this is the point of the override
  characters — they flip text direction *visibly*. Unlike zero-width
  or invisible-ink, directional overrides have a visual effect,
  which makes the stego overt.
- **Aggressive sanitizers**: modern email clients, security-conscious
  editors, and GitHub/GitLab display all strip or warn on RLO/LRO
  after the 2021 "Trojan Source" disclosures.
- **NFKC**: passes through, but the visible flipping remains.

## Where it survives

- Raw UTF-8 (files, HTTP, git blobs — but with a big warning banner
  on GitHub since 2021 CVE-2021-42574).
- Slack paste ([[sv-directional-slack-paste]]) — Slack renders the
  overrides visibly, revealing the hide.

## The Trojan Source connection

CVE-2021-42574 (Boucher & Anderson 2021) was the same primitive
weaponized in source code — hide `//` comment terminators inside
RLO-bracketed runs so a compiler and a human reader disagree on what
the code says. Every editor and code-forge has flagged directional
overrides in code since; expect the same treatment in prose.

Because of that, directional-override steg is best treated as
**visibly-perturbed** (stealth_class in the record). The user sees
that text direction flipped; the payload survives, but the channel
is obvious.

## Detection

- Byte scan: `U+202A..U+202E`, `U+2066..U+2069`.
- `text_core.detect_unicode_steg` catches directional-override runs.
- Visual: text starts flipping mid-line.

## Sources

- [[unicode-tr36-security]] — UTS #36 on directional formatting abuse
- [[st3gg-field-guide]] — ST3GG-specific framing
