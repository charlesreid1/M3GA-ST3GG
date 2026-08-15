# GIF steganography

GIF 89a is an underrated carrier: comment extensions carry arbitrary
bytes, the global color table is LSB-modifiable, disposal-method
frames are a covert timing channel. Slack keeps GIFs byte-identical
on upload — a rare survival channel for consumer messengers.

## What the ST3GG implementation does

Two GIF techniques ship in `img_core`:

- **Comment extension** — `gif_comment_encode / gif_comment_decode`.
  See [[image-gif-comment]].
- **Palette LSB** — `gif_palette_lsb_encode / gif_palette_lsb_decode`.
  See [[image-gif-palette-lsb]].

Frame timing and disposal-method channels are documented but not
shipped as encoders in `img_core`.

## GIF structure recap

```
Header (GIF89a)
Logical Screen Descriptor
[Global Color Table]        ← palette LSB target
[Comment Extension]         ← comment payload target
[Application Extension]     ← NETSCAPE2.0 loop counter, etc.
Image Descriptor 1
  [Local Color Table]
  Image Data (LZW-compressed indices)
Graphic Control Extension   ← disposal method, delay, transparent index
Image Descriptor 2 ...
...
Trailer (0x3B)
```

## The three GIF channels

### Comment extension (`0x21 0xFE ...`)

Sub-block chain, each sub-block up to 255 bytes, arbitrary count.
The entire payload can go in one comment. Decoders ignore comment
extensions when rendering.

Where it dies: GIF re-encoders that drop non-render extensions
(some webapp thumbnailers). Where it survives: everywhere the raw
GIF bytes survive.

### Palette LSB

Global color table (up to 256 entries × 3 bytes RGB). Modify the
LSB of each palette byte. Because pixels are palette-indexed (not
RGB directly), the LSB modification changes color, not pixel index —
so the visual perturbation is a slight color shift per palette
entry, not a per-pixel effect. See [[image-gif-palette-lsb]].

### Timing / disposal channels

Each frame has a `graphic control extension` with `disposal method`
(0-3), `delay time` (1/100 sec), and `transparent color index`.
Frame-level payload channels — modulate disposal choice or delay
value to encode bits. Not currently shipped as `img_core` builders.

## Where it survives

- **Slack upload** ✅ (see [[sv-gif-comment-slack-upload]]).
- **HTTP raw / GitHub / email attachment**.

## Where it dies

- Any GIF-to-video or GIF-to-WebP conversion (Twitter, some Slack
  workflows, Discord's animated-emoji pipeline).

## Detection

- Comment extensions: `stegg_read_metadata` + `identify -verbose`
  (ImageMagick) list all extensions.
- Palette LSB: bit-plane visualization on the global color table
  shows structure vs noise.
- Timing/disposal: extract per-frame delay/disposal sequences.

## Sources

- GIF 89a specification (CompuServe, 1990)
- [[st3gg-field-guide]] — ST3GG-specific GIF tooling
