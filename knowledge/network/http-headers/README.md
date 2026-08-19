# HTTP custom-header covert channels

Hex-encoded payload in custom `X-*` HTTP headers. Single-packet
high capacity. Blend in as `X-Request-Id`, `X-Amz-*`, `X-Datadog-*`,
etc.

## What ST3GG implements

`network_core.StegoMethod.HTTP_HEADER` — see [[network-http-header]].

## The trick

Every HTTP request and response can carry arbitrary `X-*` headers
that servers and clients pass through. Encode payload as hex (or
base64) in one or more headers:

```
X-Request-Id: 7061796c6f61644865726521
X-Trace-Id:   636f7665727463 68616e6e656c
```

Server proxies vary in behavior:

- **Some proxies pass unknown X- headers through untouched.**
- **Some strip unknown X- headers** as a security default.
- **Some WAFs log all headers** — silence isn't the same as
  invisibility.

## Where it dies

- **Aggressive WAFs**: some strip unknown headers or the entire
  request if a header exceeds a length threshold.
- **TLS termination**: the intermediary can inspect all headers,
  including X-* ones.
- **HTTP/2 header compression (HPACK)** doesn't hide the plaintext
  from anything terminating TLS.

## Where it survives

- **Direct HTTP without WAF**: byte-perfect.
- **Most CDNs**: pass X-Request-Id, X-Forwarded-For, and similar
  through.

## Detection

- **Header name entropy**: real X-* headers use a small set of
  standard names. Random-looking ones stand out.
- **Header value entropy**: real X- values are UUIDs, IPs, JWTs,
  short strings. Long hex/base64 blobs are unusual.
- Any Zeek `http.log` or Splunk `stream:http` sourcetype captures
  them for later analysis.

## Sources

- [[st3gg-field-guide]] — ST3GG-specific framing
- RFC 6648 — deprecating the "X-" convention (but it survived)
