# Audio silence-interval steganography

Encode bits into the duration of silent gaps between spoken (or
audio) segments. Short gap = 0, long gap = 1. Especially useful over
telephone / VoIP where silence-suppression codecs already re-time
gaps.

## The technique

See [[audio-silence-interval]]. Documented; not implemented in this
repo's `audio_core`.

## Algorithm

1. Voice-activity-detect the cover to find silent gaps.
2. For each gap, decide a bit assignment:
   - Short gap (≤ X ms) → bit 0
   - Long gap (> X ms) → bit 1
3. Modify each gap's duration to match the payload bit, keeping the
   *content* segments unchanged.

Framing: delimiter-based (start / end marker inserted at known
positions) or a length prefix in the first N gaps.

## Where it dies

- **Voice-activity detectors that re-time gaps aggressively**
  (silence suppression on modern VoIP): may re-normalize gap
  durations.
- **Recording with a reference source available**: if the attacker
  has both the "original" audio and the stego, they can spot the
  differing gap durations.

## Where it survives

- **VoIP without silence suppression** or with fixed gap padding.
- **Broadcast audio** where gap durations are naturalistic.
- **File transports**: WAV byte-identical.

## Historical use

Silence-interval steg was proposed in the late 1990s / early 2000s
for smuggling data through phone-line voice channels. Rare in
modern practice because phone lines themselves are rare.

## Sources

- [[st3gg-field-guide]] — reference only
