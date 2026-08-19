# Audio spectrogram hiding (Aphex Twin style)

Render a hidden image in the frequency domain; IFFT to audio;
distribute as a normal audio file. Audible as a harsh chirp; visible
only in a spectrogram viewer.

## The technique

See [[audio-spectrogram]] and the CTF genre [[ctf-spectrogram-hide]].

## Algorithm

1. Take a source image (text, logo, a face, whatever).
2. For each pixel `(t, f)` at time `t` and frequency `f`, set the
   corresponding spectrogram bin's magnitude to the pixel's
   brightness.
3. Randomize or match phase to nearby cells for continuity.
4. Inverse STFT to reconstruct time-domain audio.

The result: the audio sounds like a rasping chirp (the image's
frequency structure IS the audio's frequency structure at each time
step). But run it through a spectrogram viewer (Audacity, Sonic
Visualiser, matplotlib) and the image appears.

## The Aphex Twin canon

Richard James's 1999 track "ΔMi-1 = -αΣn=1NDi[n]" on the *Windowlicker*
EP contains his own face rendered as a spectrogram in the last ~40
seconds. A generation of steg-curious kids discovered the technique
by watching that in Winamp's visualization mode. Every DEF CON badge
in the last decade has had at least one spectrogram-hide challenge —
see [[ctf-spectrogram-hide]].

## Where it survives

- **Any audio transport that preserves the frequency content** — MP3
  at 128 kbps is usually enough. WAV/FLAC is safest.
- The image is a spectrogram *shape*, not a byte-exact reproduction,
  so a moderately lossy codec preserves the hide.

## Where it dies

- **Extreme bitrate reduction** (below ~64 kbps): the codec's
  psychoacoustic model may prune the "background" high-frequency
  content that carries the image detail.
- **Aggressive noise reduction**: strips the chirp back to silence.

## Detection

- Open the audio in **Audacity → Spectrogram view** (`Ctrl+Shift+G`),
  or **Sonic Visualiser** with a windowed STFT view (FFT window
  1024-4096, log-frequency scale).
- The hidden image is directly visible.
- `sox <file>.wav -n spectrogram` writes a PNG.

## Sources

- [[st3gg-field-guide]] — ST3GG-specific tooling
- Aphex Twin, "ΔMi-1 = -αΣn=1NDi[n]" (1999, *Windowlicker*)
