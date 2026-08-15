# CTF pattern: spectrogram hides

An audio file that renders an image (usually the flag itself as ASCII
art or a QR code) when viewed as a spectrogram. The audio sounds
like chirps or a rasping tone; the visual is only visible in a
frequency-domain view.

## The pattern

See [[audio/spectrogram]] for the technique. The CTF genre record is
[[ctf-spectrogram-hide]].

## Solving

If a CTF hands you an audio file and no LSB hits fire, spectrogram
is the second thing to try:

1. Open in **Audacity** → **Spectrogram view** (`Ctrl+Shift+G`), or
   **Sonic Visualiser** with an FFT window (1024-4096, log scale).
2. Look for structure. Text, QR codes, a face.
3. If nothing appears, try different window sizes and scales — some
   hides use logarithmic frequency, some use linear.

Alternative CLI:
```
sox <file>.wav -n spectrogram -o out.png
```

## The Aphex Twin canon

Richard James's 1999 track on the *Windowlicker* EP contains his
own face rendered as a spectrogram in the last ~40 seconds. Every
DEF CON badge in the last decade has repeated the pattern with
different images. It is the single audio-steg trick that always
shows up in CTFs.

## Frequently seen variants

- **QR code as spectrogram**: solver phone-scans the frequency-
  domain view. Especially cruel.
- **ASCII text as spectrogram**: text painted at ~2000-4000 Hz.
- **Multi-image collage**: different images at different time
  ranges, each hiding part of the flag.

## Sources

- [[st3gg-field-guide]] — ST3GG audio-triage integration
- Aphex Twin, "ΔMi-1 = -αΣn=1NDi[n]" (1999)
- Multi-year DEF CON badge tradition
