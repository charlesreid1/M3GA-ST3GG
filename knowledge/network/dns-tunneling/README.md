# DNS tunneling (QNAME + TXT covert channels)

Payload embedded in DNS QNAMEs (base32) or DNS TXT record RDATA
(base64). The classic egress-bypass channel: DNS is almost always
allowed outbound.

## What ST3GG implements

Two network_core methods:

- `DNS_LABEL` → see [[network-dns-label]] (base32 in QNAME labels,
  ~48 raw bytes per label).
- `DNS_TXT` → see [[network-dns-txt]] (base64 in TXT record RDATA,
  up to 255 bytes per string).

## Why DNS

Every enterprise egress filter allows DNS to the org's resolver
(usually 53/UDP). That resolver forwards recursive queries to
authoritative servers. A covert authoritative server can respond
with payload-carrying TXT records to any query.

Two directions:

- **Uplink (client → server)**: encode payload as base32 in the
  QNAME (`payload-data-here.attacker.com`). Every query becomes
  a payload byte block.
- **Downlink (server → client)**: encode payload as base64 in TXT
  RDATA (SPF/DKIM already do this legitimately).

## Historical implementations

- **NSTX** (2000): the original DNS tunnel.
- **DNScat / DNScat2** (Ron Bowes, 2013): TCP-over-DNS.
- **iodine** (2006, still maintained): IPv4-over-DNS.
- **DoH-tunneling** (post-2018): DNS-over-HTTPS makes the whole
  thing invisible to plaintext DPI.

## Where it dies

- **DNS-anomaly detectors** (Splunk queries, Zeek dns.log): flag
  long labels (>30 chars), high-entropy labels, unusually many
  subdomains under one apex, and TXT records to hosts that shouldn't
  serve TXT.
- **DNS-over-HTTPS at the resolver**: your covert traffic goes
  through 8.8.8.8 or 1.1.1.1, which likely won't forward to your
  attacker DNS.
- **DNS query rate limits** (RRL).

## Where it survives

- **Any network with unmonitored recursive DNS**: home networks,
  small offices.
- **Networks with monitored-but-not-blocked DNS**: detection is a
  best-effort log query.

## Detection

- Query rate to a single apex.
- QNAME entropy (Shannon).
- QNAME length distribution.
- Repeated TXT queries with unusual answer patterns.

## Sources

- [[st3gg-field-guide]] — ST3GG-specific NETH framing
- iodine README
- DNScat2 README (Ron Bowes)
