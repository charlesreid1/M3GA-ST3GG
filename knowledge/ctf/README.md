# CTF steg genres

Compound-technique catalog — the kinds of hides that show up in
puzzles rather than production usage. These aren't single techniques
but *pipelines*: image-contains-ZIP-contains-audio-contains-
spectrogram-contains-flag.

## Common genres

- **Chained carriers** — the classic. Extract carrier A, discover
  carrier B inside, repeat until you hit the flag. See
  [[image-matryoshka]] (encoded recursion via ST3GG's SPECTER).
- **Polyglot puzzles** — one file that parses as N formats. See
  [[image-polyglot]] and [[albertini-polyglots]].
- **Spectrogram hides** — image encoded into audio frequency domain
  (roadmap in [[audio/README]]).
- **Prompt-injection genres** — hidden LLM instructions via
  [[text-invisible-ink]] or [[emoji-tag-sequence]]. The 2024–2026
  wave documented in [[greenberg-2024-tag-injection]].
- **Matryoshka depth-N** — nested LSB. Depth-11 tested in the
  repo's SPECTER example.
- **Header-signature bait** — file that fires every scanner (F5 sig,
  chi-square, StegDetect) but has no payload. Reading
  [[detection/README]] carefully is how you avoid burning time on
  bait.

## The generic CTF pipeline (from the field guide)

1. Identify carrier — magic bytes, filename hints.
2. Check metadata — cheap, high-yield.
3. Check trailing bytes past IEND / EOI / GIF trailer / PDF %%EOF.
4. Check LSB across common configs.
5. Check palette / DCT.
6. Check for polyglots.
7. Check for text steg in the prompt itself.

Not every step every time — cost order matters. `stegg_triage`
executes this as a composed sweep.
