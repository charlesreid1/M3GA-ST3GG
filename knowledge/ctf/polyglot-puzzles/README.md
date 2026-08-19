# CTF pattern: polyglot puzzles

A single file that parses as multiple formats simultaneously.
Sometimes both formats are used by the challenge; sometimes only
one contains the flag and the other is misdirection.

## The pattern

See [[image/polyglots]] for the technique. The CTF genre record is
[[ctf-polyglot-injection]].

Common polyglot pairs used in CTFs:

- **PNG + ZIP** — image opens; extracted zip has more content.
- **JPEG + ZIP** — same story, different image.
- **PDF + ZIP** — PDF opens as PDF, `unzip` reveals the archive.
- **PDF + Java class** — the file is a valid PDF AND a valid JAR.
- **HTML + JS + XSS-in-comment** — page renders + JS payload +
  attack vector.
- **PDF + ELF** — from PoC||GTFO 0x08.

## Solving

1. **`binwalk <file>`** — scans for embedded magic bytes. If binwalk
   finds a second-format signature inside the file, it's a polyglot.
2. **`stegg_carve <file>`** — tries every decoder ST3GG knows and
   reports which parsed.
3. **Try each parser on the same bytes**: `unzip`, `pdftk`, `file`,
   `xxd | head`, `hexdump -C | grep -E "PK|%PDF|JFIF"`, `identify`.
4. **Look at both parsers' output** — the flag might be in *either*
   format.

## Where the flag hides

- **The image content** of the visual half.
- **The archive contents** of the archive half.
- **The trailing bytes** between the two container boundaries.
- **The metadata slots** of both formats simultaneously.

## Ange Albertini's canon

The reference polyglot corpus is Ange Albertini's collection, cited
in [[albertini-polyglots]]. Each polyglot is a self-contained proof
that a specific format-pair combination is possible; each has been
used in CTFs since.

## PoC||GTFO

Every issue of the PoC||GTFO zine is itself a polyglot (each issue
is a PDF AND at least one other format). Read the intro of any issue
for the specific construction — those constructions get repurposed
in CTF challenges within months.

## Sources

- [[albertini-polyglots]] — Ange Albertini's polyglot catalog
- PoC||GTFO — the polyglot canon
- [[st3gg-field-guide]] — ST3GG-specific carve integration
