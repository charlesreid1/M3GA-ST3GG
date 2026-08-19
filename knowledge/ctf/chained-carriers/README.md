# CTF pattern: chained carriers

A payload that requires unwrapping successive containers: an image
that contains a ZIP that contains an audio file that contains a
spectrogram-hidden image that contains the flag.

## The pattern

Each carrier at level `n` decodes to reveal the container at level
`n+1`. The chain terminates at the flag.

Common chain shapes:

- `image → trailing_zip → audio → spectrogram-hide → flag`
- `pdf_post_eof → tar → zip → text_zero_width → flag`
- `png_lsb → encrypted_zip → password_in_exif_of_inner_png → flag`
- `image → matryoshka_LSB × N → flag`

## Solving discipline

1. **Identify the outer carrier's family**. Image, audio, document,
   text. Reach for the corresponding triage tool.
2. **Extract what looks like an embedded artifact** — trailing
   bytes, tEXt chunks, LSB dump, whatever the outer layer surfaces.
3. **Re-classify the extracted artifact** as a new carrier and go
   back to step 1.
4. **Watch for the flag format** at every level. Some chains put
   the flag in an intermediate layer to trick solvers who assume
   deeper is always the answer.

## What ST3GG can do

The `stegg_carve` tool tries every internal decoder on a given byte
range — helpful for step 2 when the intermediate carrier's format
is unknown. `stegg_triage` re-runs at every level.

Recursive/nested cases are handled specifically by
[[image/matryoshka]] when every level is a ST3GG-format LSB hide.

## The record

See [[ctf-chained-carrier]] for the genre record.

## Sources

- Multi-year DEF CON badge tradition (AND!XOR, DEF CON hardware
  badge teams)
- [[st3gg-field-guide]] — ST3GG-specific chain-solving heuristics
