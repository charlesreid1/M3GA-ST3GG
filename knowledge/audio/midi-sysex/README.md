# MIDI SysEx steganography

Hide payload bytes inside MIDI System Exclusive (`F0 ... F7`)
messages. Most MIDI playback software ignores unknown SysEx; a hex
dump reveals every byte.

## The technique

See [[audio-midi-sysex]]. Not implemented in this repo's
`audio_core`; documented for completeness.

## MIDI SysEx recap

Every MIDI event is a stream of bytes; the SysEx message is
`F0 [manufacturer_id] [payload_bytes] F7`. `F0` and `F7` are the
start/end markers; `manufacturer_id` is one or three bytes; payload
is any 7-bit-per-byte sequence (bit 8 of each payload byte must be
zero — MIDI's status-byte encoding).

That 7-bit-per-byte constraint means an 8-bit payload requires
9-of-8 encoding (add a leading nibble; several encodings exist,
Yamaha and Roland's are the most common).

## Where it survives

- **Byte-identical MIDI file (.mid) transports**: HTTP, GitHub,
  email attachment.
- Most DAW software (Ableton, Logic, Reaper) preserves unknown
  SysEx on file save.

## Where it dies

- **MIDI → audio rendering**: converting the MIDI to a WAV of the
  performance loses everything not in the note-on/note-off stream.
- **General MIDI stripping**: some transcoders discard SysEx as
  "non-GM."

## Detection

- Any MIDI file parser (`mido`, `python-midi`, `mid2asm`) lists
  SysEx events.
- `strings` on the .mid file catches ASCII payloads in SysEx.

## Comparison to network channels

MIDI SysEx is basically [[network/http-headers]] for MIDI: an
application-defined ignored field. The pattern (spec-defined
"ignore this if you don't understand it" slot) recurs in every
format — HTTP `X-` headers, PNG private chunks, ZIP extra fields,
JPEG APPn segments, MIDI SysEx.

## Sources

- MIDI 1.0 Specification (MMA, 1996)
- [[st3gg-field-guide]] — reference only
