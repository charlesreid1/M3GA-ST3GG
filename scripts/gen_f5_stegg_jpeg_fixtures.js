/*
 * Generate pinned F5Stegg JPEG fixtures — embed known payloads into
 * clean.jpg using the JS reference implementation.  The Python test
 * suite then extracts them and asserts byte-equality.
 *
 * These fixtures are the acceptance bar for the stegg dialect port:
 * JS-embed → Python-extract must round-trip.
 *
 * Run once when the port lands (or when clean.jpg / f5stego-lib.js
 * changes):
 *
 *     node scripts/gen_f5_stegg_jpeg_fixtures.js
 *
 * Outputs go under tests/unit/fixtures/f5/jpeg/, alongside a manifest
 * that names each blob's key + payload for the test to iterate.
 */

'use strict';

const fs = require('fs');
const path = require('path');
const f5stego = require(path.join(__dirname, '..', 'f5stego-lib.js'));

const REPO = path.resolve(__dirname, '..');
const OUT_DIR = path.join(REPO, 'tests/unit/fixtures/f5/jpeg');
fs.mkdirSync(OUT_DIR, { recursive: true });

const CLEAN = fs.readFileSync(path.join(REPO, 'clean.jpg'));

// Fixture matrix.  Keep payload sizes small enough that k stays high
// (auto-selected) but varied enough to hit the 2- and 3-byte framing
// branches wouldn't fit in this JPEG's capacity anyway — that's fine,
// we hit the 3-byte branch via unit tests on _framing directly.
const CASES = [
    {
        label: 'short_ascii',
        key_hex: '00010203',
        payload_utf8: 'Hello from JS!',
    },
    {
        label: 'longer_ascii',
        key_hex: 'deadbeef',
        payload_utf8: 'The quick brown fox jumps over the lazy dog.  ' +
                      'This tests multi-byte extraction with a longer payload ' +
                      'that will exercise more of the coefficient array.',
    },
    {
        label: 'binary_payload',
        key_hex: 'a0b1c2d3e4',
        payload_hex: '0001020304ff7f80fe' + '00112233445566778899aabbccddeeff',
    },
    {
        label: 'single_byte',
        key_hex: '01',
        payload_hex: '42',
    },
];

const manifest = { source_jpeg: 'clean.jpg', cases: [] };

for (const c of CASES) {
    const codec = new f5stego(Uint8Array.from(Buffer.from(c.key_hex, 'hex')));
    codec.parse(new Uint8Array(CLEAN));

    let payload;
    if (c.payload_hex) payload = Buffer.from(c.payload_hex, 'hex');
    else payload = Buffer.from(c.payload_utf8, 'utf8');

    const stats = codec.f5put(Uint8Array.from(payload));
    const out = codec.pack();

    const outName = `stegg_${c.label}.jpg`;
    fs.writeFileSync(path.join(OUT_DIR, outName), Buffer.from(out));

    manifest.cases.push({
        label: c.label,
        blob: outName,
        key_hex: c.key_hex,
        payload_hex: payload.toString('hex'),
        payload_len: payload.length,
        k: stats.k,
        embedded: stats.embedded,
        changed: stats.changed,
    });
    console.log(`  wrote ${outName}  k=${stats.k}  payload=${payload.length}B`);
}

fs.writeFileSync(path.join(OUT_DIR, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
console.log(`  wrote manifest.json  cases=${manifest.cases.length}`);
