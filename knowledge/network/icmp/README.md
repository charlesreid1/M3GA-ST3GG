# ICMP echo covert channels

Payload in the data section of ICMP Echo Request/Reply. The
LOKI/Loki2 lineage. Highest per-packet capacity of the network
methods, lowest stealth — high-entropy ICMP payload rings every
DFIR alarm.

## What ST3GG implements

`network_core.StegoMethod.ICMP_PAYLOAD` — see
[[network-icmp-payload]].

## The trick

- ICMP echo (types 8 and 0) carries an arbitrary data section
  ("optional data") that endpoints echo back verbatim.
- Encode payload as raw bytes in that field.
- Bidirectional: request carries payload one way, reply carries the
  other.

## Historical

- **LOKI / LOKI2** (Phrack 49-51, 1996-97): the original ICMP
  covert channel; introduced the term.
- **ptunnel** (2004): a still-maintained ICMP tunnel that runs TCP
  over ICMP echo.

## Where it dies

- **Enterprise egress filters** block outbound ICMP echo by default
  in most modern deployments.
- **Every IDS in the last 20 years** watches for large ICMP payloads
  and high-entropy payload content.
- **Windows Defender / macOS firewall** default-deny outbound ICMP.

## Where it survives

- **Home networks** and **small-office** setups often allow ICMP
  outbound.
- **Some cloud VPCs** allow ICMP for reachability testing.

## Detection

- **ICMP packet size**: real echo defaults are 32 or 64 bytes;
  arbitrary sizes are suspicious.
- **Entropy of ICMP data**: real echo data is a fixed string
  (Windows: `abcdefghijklmnopqrstuvwabcdefghi`); random-looking data
  is a giveaway.
- **Bidirectional payload asymmetry**: real echo responses ARE the
  request payload; if request and response payloads differ, it's a
  covert channel.

## Sources

- Phrack 49 article 6 (daemon9, 1996) — Loki
- Phrack 51 article 6 (daemon9, 1997) — Loki2
- [[st3gg-field-guide]] — ST3GG-specific framing
