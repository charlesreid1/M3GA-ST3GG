# TCP options covert channels

The TCP options field (Timestamp, Window Scale, MSS, SACK, and
others) offers several payload-carrying slots per packet.

## What ST3GG implements

Two TCP-option-adjacent channels from `network_core.StegoMethod`:

- **`TCP_TIMESTAMP`** — 4 bytes/packet in TSval. See
  [[network-tcp-timestamp]].
- **`TCP_WINDOW`** — 2 bytes/packet in the advertised window field
  (technically not an *option*, but header-adjacent). See
  [[network-tcp-window]].
- **`TCP_URGENT`** — 2 bytes/packet in the urgent pointer.
  See [[network-tcp-urgent]].

Not implemented but well-documented:

- **MSS option (kind 2, 2 bytes)**: only present on SYN. 2 bytes
  per handshake.
- **Window Scale (kind 3, 1 byte)**: only present on SYN, restricted
  0-14. Extremely limited.
- **SACK Permitted (kind 4, 0 bytes)**: presence/absence = 1 bit
  per SYN.
- **SACK blocks (kind 5, 8-32 bytes)**: appear on data packets, per-
  connection.

## Why timestamp is the good one

TCP timestamps are present on EVERY data packet on modern connections
(RFC 1323, ubiquitous since ~2000). 4 bytes each. Modern OSes
initialize TSval to a per-connection random offset then tick at 1 kHz;
a covert TSval that matches the ticks-per-packet rate is invisible
to bulk inspection.

## Where it dies

- **Timestamp reversal / rewriting**: some middleboxes rewrite
  timestamps (rare but real; e.g. some load balancers).
- **Statistical clock-rate detection**: if the sender's real clock
  ticks at ~1000/s but covert timestamps advance faster or slower,
  the anomaly is measurable.

## Where it survives

- **End-to-end TCP without timestamp rewriting**: essentially
  everywhere.

## Detection

- Timestamp increment vs wall-clock rate.
- Timestamp entropy per connection.

## Sources

- RFC 1323 — TCP Extensions for High Performance (timestamps + window
  scale)
- Rowland 1997 — TCP/IP covert channels
- [[st3gg-field-guide]] — ST3GG-specific framing
