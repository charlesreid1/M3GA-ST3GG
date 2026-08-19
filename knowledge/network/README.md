# Network steganography

Payload hidden in packet-header fields or inter-packet timing.
Every field the RFC doesn't nail down to a single value is a
potential carrier.

## Techniques ([[network-covert-channel]])

network_core exposes 11 methods, each with different bytes-per-packet
capacity:

- **IP_TTL** (1 B/pkt) — modulate the TTL of every packet.
- **IP_ID** (2 B/pkt) — the IP identification field.
- **TCP_ISN** (4 B/pkt) — initial sequence number.
- **TCP_TIMESTAMP** (4 B/pkt) — the timestamp option.
- **TCP_WINDOW** (2 B/pkt).
- **TCP_URGENT** (2 B/pkt).
- **ICMP_PAYLOAD** (32 B/pkt) — free-form ICMP echo payload bytes.
- **DNS_LABEL** (48 B/pkt) — encode into DNS query labels.
- **DNS_TXT** (255 B/pkt) — DNS TXT record bodies.
- **HTTP_HEADER** (single-packet unlimited).
- **COVERT_TIMING** (1 bit/pkt) — inter-packet delay modulation,
  stealthiest but slowest.

## Carrier format

[[fmt-pcap]] — PCAP frame layout, magic bytes, per-packet grammar.

## Detection

Statistical shape analysis on the modulated field, timing-entropy
analysis for [[network-covert-channel]] variants that ride
COVERT_TIMING. Not covered by the current signals field guide.

## Transport survival

Trivially: the transport IS the network. Cross-Internet delivery
usually preserves the fields network_core writes (though NAT / PAT
mangles TCP_ISN, and public DNS resolvers may cache DNS_TXT). No
survival records seeded yet.
