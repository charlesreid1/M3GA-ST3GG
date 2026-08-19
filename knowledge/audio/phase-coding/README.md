# Audio phase coding

Payload as modifications to the phase spectrum of a reference
segment. Perceptually inaudible (the human ear is insensitive to
absolute phase); robust against small time-domain distortions.

## The technique

See [[audio-phase-coding]]. Not implemented in this repo's
`audio_core`; documented for completeness.

## Algorithm

1. Split the cover audio into consecutive segments (typically
   1024 samples each).
2. Compute the DFT of the first ("anchor") segment.
3. Modify the anchor segment's phase spectrum to encode payload bits
   at chosen frequency bins.
4. For every subsequent segment, adjust its phase so that the
   *relative* phase between segments is preserved (this is what
   keeps the audio sounding natural despite the anchor phase
   change).

Receiver: DFT each segment, extract the phase at the payload-bearing
bins of the anchor segment.

## Where it dies

- **Sample-rate conversion**: rewrites the DFT bin structure.
- **Time-domain trimming**: the anchor-segment alignment is lost.
- **Aggressive perceptual codecs**: some codec's phase-modification
  passes destroy the encoded phase deltas.

## Where it survives

- **Byte-identical WAV/FLAC**.
- **Modest MP3 / AAC**: phase is often preserved better than amplitude
  by MDCT codecs.

## Detection

- **Inter-segment phase-difference analysis**: real audio has
  consistent phase relationships between adjacent segments; phase
  coding disrupts them at the anchor.

## Sources

- [[anderson-petitcolas-1998-survey]] — phase-coding survey
- [[st3gg-field-guide]] — reference only
