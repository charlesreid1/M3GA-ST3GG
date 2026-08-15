# IP identification (IPID) covert channel

Payload in the 16-bit IP identification field. 2 bytes per packet.
Historically monotonic on old stacks; randomized on modern Linux /
Windows, which makes covert traffic blend in — but the payload's
non-uniform entropy still fingerprints.

## What ST3GG implements

`network_core.StegoMethod.IP_ID` — see [[network-ip-id]].

## The IPID story

The IPv4 IP ID field (16 bits per packet) is used for fragment
reassembly. When a packet isn't fragmented, the value is ignored by
the receiver — a free 2-byte slot.

Stack behavior:

- **Old Linux (pre-3.16, ~2014)**: strictly monotonic global counter.
  Covert channel is trivial to detect (breaks monotonicity).
- **Modern Linux / Windows**: per-connection random or per-connection
  incrementing. High entropy. Covert channel blends.
- **BSD**: per-connection incrementing.

## Where it dies

- **NAT rewriting**: some NAT gateways rewrite IPIDs.
- **Middleboxes with fragment-reassembly**: rewrite IPIDs.

## Where it survives

- End-to-end IPv4 without NAT-side rewriting.

## Detection

- Entropy of IPID within a flow: payload has more distinct-value
  variety than real per-connection incrementing.
- Correlation between IPID and connection state.

## The Zalewski OS fingerprint angle

Michal Zalewski's *Silence on the Wire* (2005) documents how IPID
patterns fingerprint OS versions and can even leak inter-host
communication ("idle scanning" — nmap's `-sI`). A covert-channel
sender that gets the IPID sequence wrong for their claimed OS gives
themselves away.

## Sources

- Zalewski 2005, *Silence on the Wire*
- Rowland 1997 — TCP/IP covert channels
- [[st3gg-field-guide]] — ST3GG-specific framing
