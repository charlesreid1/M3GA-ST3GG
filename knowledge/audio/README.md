# Audio steganography

Payload hidden inside audio. The one implemented technique is
[[audio-lsb]] over PCM samples in [[fmt-wav]] / AIFF; the other
methods below live in the field guide as roadmap.

## Techniques

- **[[audio-lsb]]** — LSB in PCM samples (1-3 bits per sample
  tolerable before audible hiss). Survives byte-identical audio
  transfers, dies to any lossy re-encode.
- **Echo hiding** *(roadmap)* — payload as echoed delays.
- **Phase coding** *(roadmap)* — bits in relative phase between
  segments.
- **Spread spectrum** *(roadmap)* — payload spread across frequency
  bands with a PN sequence.
- **Spectrogram hides** *(CTF-common)* — image encoded into the
  audio's frequency domain. Reveal in Sonic Visualiser or
  Audacity's spectrum view — the "Aphex Twin face" pattern.
- **MP3Stego** *(external)* — unused frame bits, VBR gaps.

## Transport survival

Bit-perfect only. Lossy transports (any codec change) destroy LSB.
For messaging apps, send-as-file mode (Telegram file, WhatsApp
document, Signal attachment) preserves bytes; photo/voice-note mode
does not. See [[transport/README]].
