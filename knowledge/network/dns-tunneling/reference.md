# DNS tunneling — reference

Exact numeric spec of ST3GG's two DNS covert channels — `DNS_LABEL`
and `DNS_TXT` — as implemented in `network_core`.

## The two methods

Both live under the same NETH framing envelope; the difference is
which DNS field carries the payload chunks.

| Method      | Field                    | Encoding | Chunk size |
|-------------|--------------------------|----------|------------|
| `DNS_LABEL` | QNAME left-most label    | base32   | 48 raw bytes → 60-char label |
| `DNS_TXT`   | TXT record RDATA         | base64   | 255 bytes per string |

## NETH framing (both methods)

12-byte header prepended to every payload before per-method
encoding:

```
Bytes 0-3:   b'NETH' magic
Byte  4:     StegoMethod enum value (uint8)
Byte  5:     WireFormat enum value (uint8)
Bytes 6-7:   payload length (uint16 BE, max 65535)
Bytes 8-11:  CRC32 of payload (uint32 BE)
```

Payload max: 64 KB (limited by the uint16 length field). Small
enough to fit through most DNS pipelines without triggering
rate-limit anomalies for reasonable use.

## DNS_LABEL encoding

Encoder pipeline:

1. Concatenate `NETH_header + payload`.
2. `encoded = base32(...).lower().rstrip('=')` — base32 gets 5 raw
   bytes → 8 encoded chars.
3. Split into 60-char chunks (DNS label limit is 63; ST3GG leaves
   3 chars of headroom).
4. For each chunk `L`, emit a DNS A-record query with
   QNAME=`L.<cover_domain>` (e.g. `mzxw6ytboi.attacker.com`).
5. UDP source port: `config.sport + chunk_index` (chunk ordering).

Wire result: a series of A queries to `<label>.<cover_domain>`,
each carrying up to 48 raw payload bytes.

Decoder pipeline:

1. Extract left-most label from each QNAME.
2. Re-pad base32 (`label + "=" * ((8 - len(label) % 8) % 8)`).
3. Base32-decode.
4. Concatenate chunk outputs in packet arrival order.
5. Read NETH header from first 12 bytes; verify magic + CRC32 +
   length.
6. Return payload bytes.

## DNS_TXT encoding

Encoder pipeline:

1. `encoded = base64(NETH_header + payload)`.
2. Split into 255-byte chunks (DNS TXT single-string length limit).
3. For each chunk, emit a DNS RESPONSE packet with:
   - Transaction ID `0x0001`, flags `0x8180` (response, no error)
   - QDCOUNT=1: QNAME=`<cover_domain>`, QTYPE=TXT, QCLASS=IN
   - ANCOUNT=1: pointer to QNAME + TYPE=TXT + CLASS=IN + TTL=300
   - RDLENGTH = `chunk_len + 1`
   - RDATA = `<len_byte><chunk_bytes>` — TXT strings are
     length-prefixed
4. UDP source port: `config.sport + chunk_index`.

Wire result: a series of DNS TXT responses appearing to answer
queries about the cover domain.

Decoder pipeline:

1. Parse each TXT record's RDATA.
2. Concatenate all length-prefixed TXT strings.
3. Base64-decode.
4. Read NETH header from first 12 bytes; verify.
5. Return payload bytes.

## Capacity

Both methods bound by NETH's 64 KB payload cap; per-packet chunk
sizes:

| Method      | Bytes per packet | Packets for 64 KB payload |
|-------------|------------------|---------------------------|
| `DNS_LABEL` | 48               | ~1400 queries             |
| `DNS_TXT`   | 255              | ~260 responses            |

DNS_TXT is ~5× more per-packet efficient. DNS_LABEL scales further
horizontally (more distinct subdomains → more parallel bandwidth)
because responses can be cached separately per QNAME.

## Direction asymmetry

- **DNS_LABEL is uplink-shaped**: the payload rides on QUERIES
  (client → server). Natural for exfiltration.
- **DNS_TXT is downlink-shaped**: the payload rides on RESPONSES
  (server → client). Natural for command-and-control from a
  covert authoritative server.

A full bidirectional tunnel (iodine / dnscat2) chains both — QNAME
labels carry uplink, TXT responses carry downlink.

## Cover domain

`config.cover_domain` — a DNS name the attacker controls. Real
queries hit the recursive resolver, get forwarded to the
authoritative for `cover_domain`, which is the covert endpoint.

Legit domains that look like this: `<data>.<subdomain>.example.com`
patterns are common for CDN health checks, ad-tech ID
attribution, and telemetry — the tunneling traffic blends unless
the domain itself is suspicious.

## Sources

- [[network-dns-label]] / [[network-dns-txt]] — the technique
  records
- iodine README — the reference IPv4-over-DNS tool
- DNScat2 (Ron Bowes) — TCP-over-DNS with a modern C2 layer
- [[st3gg-field-guide]] — ST3GG-specific NETH framing
