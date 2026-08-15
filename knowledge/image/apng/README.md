# APNG (Animated PNG) steganography

Animated PNGs extend the PNG spec with three new chunks: `acTL`
(animation control), `fcTL` (frame control), and `fdAT` (frame data).
Static-PNG viewers see only the first `IDAT`; APNG-aware viewers
render the animation. Payload channels in every APNG-specific chunk.

## What the ST3GG implementation does

`img_core.apng_fdat_encode / img_core.apng_fdat_decode`. See
[[image-apng-fdat]].

## APNG chunk layout

```
IHDR
acTL (num_frames, num_plays)
[fcTL 1] [IDAT ...]              ← first frame + static-PNG fallback
[fcTL 2] [fdAT 1 ...]            ← second frame
[fcTL 3] [fdAT 2 ...] ...
IEND
```

The critical trick: the *first* frame is a real `IDAT` (compatible
with old readers), and subsequent frames are `fdAT` chunks. Static-
PNG viewers stop at the first `IDAT` and render only the fallback
image; APNG-aware viewers walk the whole chain.

## The payload channels

- **`fdAT` frame data**: raw compressed pixel data. LSB, coefficient,
  or payload-as-frame-data all work. ST3GG's `apng_fdat_encode`
  hides a payload inside the sequence numbers + data of `fdAT`
  chunks.
- **`fcTL` sequences**: each frame carries a delay numerator/
  denominator (16-bit each). Modulate delays for bit payloads.
- **Frame count discrepancy**: `acTL` declares `num_frames`; a
  discrepancy between declared and actual is a private smuggle slot.
- **`fcTL` disposal / blend ops**: 3 bits per frame, semantically
  meaningful — encoders that use rare combinations are fingerprintable.

## Where it dies

- **PNG re-encoders that strip APNG chunks**: some image processors
  keep only the first frame and drop `acTL` / `fcTL` / `fdAT`.
- **Slack upload**: preserves the raw bytes (PNG IDAT byte-identical),
  so APNG survives byte-identical → the extra chunks come through.
  Test per-payload before claiming survival.

## Where it survives

- **Byte-identical transports**: HTTP raw, GitHub, email attachment.
- **Modern browsers** all render APNG animations (Firefox since
  2007, Chrome/Edge since 2018, Safari since 2019).

## The static-PNG fallback trick

APNG's most steg-relevant feature: the first frame is a valid static
PNG. A viewer that reads only through the first `IDAT` sees a
completely legitimate image; the *actual* payload can live entirely
in the `fdAT` chunks that only APNG-aware readers touch. This is
close to a two-face-file effect without being a true polyglot.

## Detection

- `stegg_read_png_chunks` shows every chunk including APNG-specific.
- `pngcheck` recognizes APNG extensions.
- Frame count from `acTL` vs actual frame data mismatch is a strong
  signal.

## Sources

- [[rfc-2083-png]] — base PNG spec
- APNG specification (Mozilla, 2008)
- [[st3gg-field-guide]] — ST3GG-specific APNG tooling
