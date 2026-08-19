# DNS tunneling — 15-second triage

"Is this DNS traffic a covert channel?"

## The two-second discriminators

Run these against a PCAP or `dns.log`:

1. **Label length**: any subdomain label over 20-30 characters is
   unusual. Real service names are short. Tunneling labels are
   often 40-63 characters.
2. **Entropy of labels**: real subdomains use dictionary-shaped
   names. Base32 / base64 output looks like random letters and
   digits.
3. **Query volume to a single apex**: real traffic to a domain
   plateaus. Tunneling traffic can spike to hundreds of queries
   per second per apex.
4. **TXT record answer ratio**: most domains rarely serve TXT
   records; a domain serving mostly TXT is suspicious.

## Signal cheat sheet

| Signal | Diagnosis |
|--------|-----------|
| Subdomains ≥40 chars, all-alphanumeric, high entropy | Base32/base64 label — likely DNS_LABEL tunneling |
| Repeated TXT queries to one apex, TXT answer sizes near 255 bytes | DNS_TXT downlink |
| Many distinct subdomains under one apex in a short window | DNS_LABEL exfiltration |
| Query rate to one apex >> baseline | Any DNS tunnel |
| TXT records used for SPF/DKIM/DMARC | Legitimate TXT use; not tunneling by itself |
| TXT records with base64-shaped RDATA not matching any RFC standard | Suspicious; try DNS_TXT decoder |

## Practical decode flow

```python
from stegg import network_core

# Try both methods on a captured PCAP:
try:
    result = network_core.decode(pcap_bytes)
    print(f"Method: {result['method']}, payload: {result['payload']}")
except Exception as e:
    print(f"Not a NETH-framed DNS tunnel: {e}")
```

If the PCAP contains NETH-framed data, `network_core.decode`
auto-detects the method from the NETH header's method_id byte.
Any NETH match with a valid CRC32 is a confirmed hit.

## Detection at scale

For real-world monitoring rather than CTF triage:

- **Zeek `dns.log`** — has fields `query`, `qtype`, `answers`.
  Filter for `query.len > 40` or `answers.len > 200`.
- **Splunk `stream:dns`** — same idea, different tool.
- **DNS query rate** per apex per minute is the coarsest and often
  most useful metric.
- **Shannon entropy** of subdomain labels is more precise but
  requires post-processing.

## When the tunnel is hidden inside legitimate-looking traffic

Modern tunnels blend by:

- Emulating a plausible CDN pattern (many short-lived subdomains
  under one apex, e.g. `cdn.example.com` style).
- Using low query rates spread over hours (below any single-window
  threshold).
- Using DoH at the client, DoT at the resolver, or both — the
  wire is encrypted, only the recursive-to-authoritative segment
  is visible to the defender.

For those, statistical monitoring (query counts over time by
domain) beats content inspection. See the parent
[[network/dns-tunneling]] README for the wider architectural view.

## Sources

- [[network-dns-label]] / [[network-dns-txt]]
- Zeek `dns.log` documentation
- Farsight DNS observability writeups
- [[st3gg-field-guide]]
