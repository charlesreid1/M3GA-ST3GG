# Network timing covert channels

Bits encoded in the *timing* of packets rather than their contents.
Beats every content-inspecting DPI — nothing about the bytes is
anomalous. Vulnerable to inter-arrival-time statistical analysis.

## What ST3GG implements

`network_core.StegoMethod.COVERT_TIMING` — see
[[network-covert-timing]]. 1 bit per packet by choosing between two
inter-packet delay values.

## The concept

- Two agreed-upon delay values, `D0` (bit 0) and `D1` (bit 1).
- Sender emits packets with the delay corresponding to each payload
  bit.
- Receiver measures inter-arrival times and thresholds.

Robustness variants:

- **Direct-encoded** (as above): simplest, most detectable.
- **PPM (Pulse Position Modulation)**: encode within a slot.
- **Jitter-compensated**: interleave payload with dummy traffic to
  mask timing.

## Why it's stealthy

Deep-packet-inspection tools look at *bytes*. If your packet contents
are entirely legitimate (say, real HTTPS to a real service), timing
is the only signal — and it's data that most content filters throw
away.

## Where it dies

- **Jitter**: network jitter above (D1 - D0) destroys the signal.
- **Rate limits, ACK batching**: TCP's own timing can mask or
  distort the pattern.
- **Sophisticated timing-analysis detectors** (Cabuk & Brodley
  2004; Berk, Giani, Cybenko 2005): compute inter-arrival-time
  entropy, look for bimodality.

## Where it survives

- **Low-jitter networks** (LAN, dedicated links).
- **Any DPI-only monitoring** — timing is invisible to content
  inspection.

## Cabuk-Brodley detection

Cabuk and Brodley (2004) showed that timing covert channels create a
bimodal inter-arrival-time distribution — two peaks near `D0` and
`D1` — that's absent from normal traffic. Fit a mixture model to
IATs; if two Gaussians fit better than one, suspect a timing channel.

## Sources

- Cabuk, Brodley & Shields 2004, "IP Covert Timing Channels"
- Berk, Giani & Cybenko 2005, "Detection of Covert Channel Encoding
  in Network Packet Delays"
- [[anderson-petitcolas-1998-survey]] — the survey covering timing
  channels
- [[st3gg-field-guide]] — ST3GG-specific framing
