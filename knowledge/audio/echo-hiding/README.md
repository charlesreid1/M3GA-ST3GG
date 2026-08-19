# Audio echo hiding

Payload as short-delay echoes below the perceptual threshold. Robust
against modest processing; survives some lossy codecs at low
bitrate cost.

## The technique

The technique record is [[audio-echo-hiding]]. **Not implemented in
this repo's `audio_core`** — documented for completeness and for
KB users who need to reach for it.

## Algorithm

1. Split the cover audio into segments of ~500 ms.
2. For each segment, add a short delay (~1 ms) echo at low amplitude
   (typically -12 to -20 dB).
3. Encode bit 0 vs bit 1 by choosing between two echo delays
   (say 0.8 ms for 0, 1.2 ms for 1).
4. Optionally add a decay-and-mixer envelope to spread the echo's
   energy across the segment.

Receiver: apply cepstral analysis on each segment. The autocorrelation
peak at the echo-delay lag reveals which bit was sent.

## Where it dies

- **Heavy amplitude compression** (radio broadcast, phone-line
  companders).
- **Steep low-pass filtering** below 4 kHz.
- **Aggressive noise reduction** (RNNoise, spectral gating).

## Where it survives

- **Byte-identical WAV/FLAC transports** trivially.
- **MP3 at ≥128 kbps** — often survives (verify per codec).
- **AAC at ≥96 kbps** — often survives.
- **Voice codecs** (Opus, AMR) — mixed; some retain enough of the
  time-domain echoes.

## Detection

- **Cepstral analysis** on suspect audio: an artificial echo at fixed
  delay shows up as a spike in the cepstrum.
- Compare "clean" and "echoed" versions of the same source if
  available.

## Sources

- [[anderson-petitcolas-1998-survey]] — the survey covering echo
  hiding
- [[st3gg-field-guide]] — reference documentation only (no encoder
  in this repo)
