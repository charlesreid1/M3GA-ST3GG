# TCP Initial Sequence Number covert channel

Payload as the 32-bit TCP ISN on each SYN packet. 4 bytes per
handshake. Works only on TCP handshake initiators.

## What ST3GG implements

`network_core.StegoMethod.TCP_ISN` — see [[network-tcp-isn]].

## The trick

- Every TCP connection starts with a SYN carrying a 32-bit ISN.
- Real stacks pick ISN via RFC 6528 hash of `(src_addr, dst_addr,
  src_port, dst_port, secret)`.
- A covert sender replaces its ISN with 4 payload bytes.

## Where it dies

- **RFC 6528 verification**: a smart detector recomputes what the
  ISN "should" be and flags mismatches. Requires either the sender's
  secret or a large enough sample to statistically fingerprint
  divergence from RFC 6528 hash properties.
- **NAT rewriting**: some NAT boxes rewrite ISNs during
  translation (rare, but happens).

## Where it survives

- **Direct TCP connections** without NAT-based ISN rewriting.
- **Anywhere the destination isn't verifying ISN provenance** (most
  places).

## Detection

- **Statistical**: a stream of TCP SYNs with ISNs that don't share the
  expected structure (or with too many high-entropy bytes when real
  RFC 6528 ISNs vary slightly).
- **Rate**: excessive SYNs from one host may trip SYN-flood detectors.

## Related channels

Other TCP-header fields carry the same idea at different offsets:

- [[network-tcp-timestamp]] — TCP timestamp option (TSval, 4 B/pkt)
- [[network-tcp-window]] — advertised window (2 B/pkt)
- [[network-tcp-urgent]] — urgent pointer (2 B/pkt)

TCP timestamps and windows are steadier channels than ISNs (every
packet, not just SYNs).

## Sources

- Rowland 1997, "Covert channels in the TCP/IP protocol suite"
- [[st3gg-field-guide]] — ST3GG-specific framing
