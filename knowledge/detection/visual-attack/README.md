# Visual attack (bit-plane visualization)

Render each bit-plane of an image as a grayscale image and look at
it. The dumbest steganalysis technique that still catches the most
CTF LSB hides.

## What ST3GG uses it for

`stegg_triage`'s image-family probes surface a bit-plane
visualization pointer for the "look at it with your eyes"
diagnostic step. `zsteg` uses the same technique as its default
scan.

## How to do it

For each channel (R, G, B, A) and each bit plane 0..7:

1. Extract bit `k` from every pixel value.
2. Render as a black/white image (bit=0 → black, bit=1 → white).
3. Look at it.

The high bit planes (5-7) look like the image itself, only quantized.
The low bit planes (0-1) look like noise on a clean image, but often
look like structured text/data on a payload-embedded image.

## Signals

- **LSB plane has visible text**: someone dumped ASCII into pixels.
- **LSB plane has a QR code, a small image, a logo**: embedded
  visual payload.
- **LSB plane is uniformly 0 or 1**: unusual clean image.
- **LSB plane matches high bit plane**: something copied high-bit
  data into low bits (or vice versa) — a fingerprint of a specific
  encoder.

## Tools

- **`zsteg -v` on PNG**: iterates channels and bit-planes automatically,
  scans each rendered plane for text.
- **StegSolve** (Caesum): interactive bit-plane browser (Java applet
  era; still works).
- **`stegg_triage`**: surfaces the visual-attack pointer as a suggested
  next step when statistical probes report anomalies.

## Why it works after 30 years

Human vision is exceptional at pattern recognition. A structured
payload in the LSB plane pops out to a human viewer where a
statistical test only reports "suspicious." Every CTF LSB hide
should be checked with this — it's the highest-signal cost-cheapest
probe.

## Sources

- [[fridrich-2001-rs]] — RS paper introduces the visual-attack
  framing
- [[zsteg]] — the reference tool
- [[st3gg-field-guide]] — ST3GG-specific triage integration
