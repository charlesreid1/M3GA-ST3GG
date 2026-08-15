# Steganography vs digital watermarking

Two neighboring fields with different threat models. The ST3GG
bibliography includes both because the techniques cross-pollinate,
but the goals differ enough that a technique optimized for one is
often bad at the other.

## The threat models

**Steganography** hides *the fact of communication*.

- Adversary: a warden watching for hidden messages.
- Success = the adversary does not know a message is present.
- The message need not be recoverable by the adversary; the primary
  attack is *detection*.

**Watermarking** proves *authorship / ownership*.

- Adversary: a pirate trying to strip an ownership mark to
  redistribute the content.
- Success = the mark cannot be removed even under active attack
  (cropping, resizing, re-encoding).
- The mark's presence is often public; the mark's location and
  format may or may not be secret.

## Where the techniques diverge

Steganography:

- Prizes **undetectability** above capacity and robustness.
- Payload is *content* (a secret message).
- Failure mode: statistical detector flags "something is hidden."

Watermarking:

- Prizes **robustness** above stealth or capacity.
- Payload is *identity* (owner ID, license, timestamp).
- Failure mode: attacker removes the mark and redistributes.

## Where they overlap

- **Spread-spectrum audio watermarking** (see
  [[audio/spread-spectrum]]) is a robust-first technique that
  steganographers repurpose for undetectability by lowering the
  amplitude below perceptual threshold.
- **DCT-domain image watermarking** (Cox et al. 1997) inspired
  DCT-domain image steganography ([[image/dct]], [[image/f5]]).
- **Detection methods overlap**: chi-square, RS, SPA all work
  against both stego and weak watermarks.

## Why this matters for ST3GG

The ST3GG bibliography ([[bibliography]]) intentionally includes
Cox-style watermarking references (audio spread-spectrum work,
image DCT watermarking papers) alongside stego papers because the
underlying signal-processing techniques transfer. A pipeline
designer picking "how do I hide 32 bytes robustly against JPEG
recompression" is answering a watermarking-flavored question with
steg-flavored tools.

## Sources

- [[anderson-petitcolas-1998-survey]] — the survey that clarifies
  the split
- Cox, Miller, Bloom "Digital Watermarking" (2001) — the reference
  watermarking textbook
- [[kessler-primer]] — Kessler's primer touches on both
