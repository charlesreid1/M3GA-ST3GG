# Audio spread-spectrum steganography

Payload times a pseudo-random-noise (PRN) sequence, added to the
cover at low amplitude. Direct audio analog of DSSS radio; the
historical basis for commercial audio watermarking.

## The technique

See [[audio-spread-spectrum]]. Not implemented in this repo's
`audio_core`; documented for completeness.

## Algorithm

1. Both sender and receiver share a PRN sequence — a pseudo-random
   ±1 signal at high chip rate.
2. Encoder: for each payload bit, multiply the PRN by ±1 (bit
   choice) and add the result (scaled to low amplitude, typically
   -30 dB below cover) to the cover audio.
3. Decoder: correlate the received audio against the PRN. The sign
   of the correlation gives the payload bit.

Capacity: `chip_rate / spreading_factor` bits per second. Typical
values: 44.1 kHz chip rate, 1000-sample spreading factor → 44 bits
per second.

## Why it's robust

- The signal is spread across a wide frequency range; narrow-band
  attacks (bandpass filters, EQ) don't destroy it.
- Adding low-amplitude PRN-shaped noise is inaudible unless the
  amplitude gets high.
- Correlation with the PRN concentrates the signal energy and
  averages away uncorrelated interference (real audio, added noise).

## Where it survives

- **MP3, AAC** at moderate bitrates.
- **Amplitude compression, normalization**.
- **Low-pass and band-pass filtering** (if the PRN energy sits within
  the pass band).

## Where it dies

- **PRN mismatch**: without the shared PRN, decoding is
  impossible — this is the security property.
- **Very heavy noise reduction** aimed at the PRN's frequency band.

## The watermarking connection

Every commercial audio watermark from Verance (VCMS, Cinavia) to
Digimarc uses a variant of spread-spectrum. The steg version and the
watermark version differ mainly in the target: watermark = "prove
authorship," steg = "hide payload."

## Sources

- [[anderson-petitcolas-1998-survey]] — spread-spectrum audio survey
- [[kessler-primer]] — Kessler primer chapter on audio steg
- [[st3gg-field-guide]] — reference only
