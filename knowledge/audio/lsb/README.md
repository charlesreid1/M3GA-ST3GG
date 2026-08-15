# PCM audio LSB steganography

The audio analog of image LSB: replace the low-order bits of PCM
audio samples with payload bits. Survives byte-identical audio
transfer; dies to any lossy re-encode.

## What the ST3GG implementation does

`audio_core.audio_lsb_encode / audio_lsb_decode`. See [[audio-lsb]].

Algorithm:

1. Read the PCM audio (WAV, AIFF).
2. For each sample (int16 or int24), replace the low N bits with N
   payload bits.
3. Re-serialize as PCM.

Framing: 16-bit length prefix, then raw payload bits.
Capacity: `bits_per_channel * channels * sample_rate * duration / 8`
bytes minus header. A 1 bpc mono 44.1 kHz 60-sec WAV holds about
330 KB.

## Where it dies

- **Any lossy codec**: MP3, AAC, Opus, Ogg Vorbis re-encode via
  perceptual DCT/MDCT and quantize away sub-perceptual detail.
  Pixel-domain LSB dies to the first re-encode. See
  [[myth-audio-lsb-mp3]].
- **Sample-rate conversion**: 44.1 kHz → 48 kHz resampling rewrites
  every sample.
- **Dynamic range compression / normalization**: audio processing
  that rescales sample values.

## Where it survives

- **Byte-identical PCM transports**: WAV/AIFF over HTTP raw, GitHub,
  email attachment.
- **FLAC** (lossless): survives the compress + decompress cycle
  because FLAC preserves exact PCM samples.

## Stealth trade-off

- 1 bpc: perceptually inaudible, low capacity.
- 2 bpc: still usually inaudible for a general listener.
- ≥3 bpc: audible hiss on quiet passages.

## Detection

- **Bit-plane analysis**: the LSB plane of clean audio is
  perceptually-driven noise; the LSB plane of steg audio is
  compressed/encrypted data → statistically distinguishable.
- **Chi-square on sample-pair values**: audio analog of the JPEG
  DCT chi-square attack.

## Alternatives for lossy-transport survival

If the audio must survive an MP3 pipeline, don't LSB — reach for:

- [[audio/echo-hiding]] — bit encoded as short-delay echoes.
- [[audio/phase-coding]] — bit encoded as phase-spectrum modification.
- [[audio/spread-spectrum]] — bit as a PRN-modulated addition.

Each is per-codec-tunable; none survives arbitrary re-encodes.

## Sources

- [[anderson-petitcolas-1998-survey]] — Anderson & Petitcolas survey
- [[st3gg-field-guide]] — ST3GG-specific framing
