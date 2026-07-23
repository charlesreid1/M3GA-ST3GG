/*
 * Pinned _f5write + f5get vectors for the F5Stegg matrix layer.
 *
 * We don't have easy JS-side access to a full JPEG round-trip in this
 * script, but we CAN call _f5write directly on a synthetic coefficient
 * array of the same shape the JS uses internally.  This isolates the
 * matrix encoder + shrinkage loop from the JPEG codec.
 *
 * For each (key, payload, k) triple we record:
 *   - the pre-embed coefficient array (deterministic)
 *   - the post-embed coefficient array (what _f5write mutated it to)
 *   - the stats dict _f5write returned
 *
 * The Python port must produce identical post-embed coefficients and
 * identical stats.
 *
 * Note: _f5write expects the caller to have already framed the payload
 * (length prefix + XOR gamma).  We hand it the raw "framed" bytes and
 * let it do its thing.
 *
 * Output: tests/unit/fixtures/f5/matrix_stegg_vectors.json
 */

'use strict';

const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '..');
const f5stego = require(path.join(REPO, 'f5stego-lib.js'));

const KEY = Uint8Array.from([0x10, 0x20, 0x30, 0x40, 0x50]);
// maxPixels must be >= N so randPool (maxPixels * 4.125 bytes) fits
// N u32 permutation words + gamma tail.
const MAX_PIXELS = 16384;

// Synthetic coefficient array — same distribution as the analyze fixture,
// but with a different seed so we don't overlap tests.
const SEED = 0x7f1122ff;
const N = 64 * 128;  // 128 blocks

function make_coeffs() {
    let s = SEED >>> 0;
    const buf = new Int16Array(N);
    for (let i = 0; i < N; i++) {
        s ^= s << 13; s >>>= 0;
        s ^= s >>> 17; s >>>= 0;
        s ^= s << 5;  s >>>= 0;
        if (i % 64 === 0) { buf[i] = ((s & 0xffff) - 0x8000) | 0; continue; }
        const roll = s % 100;
        let v;
        if (roll < 60) v = 0;
        else if (roll < 85) v = (s & 1) ? 1 : -1;
        else v = ((s & 0xffff) - 0x8000) >> 8;
        buf[i] = v;
    }
    return buf;
}

const cases = [];

for (const [label, payload_hex, kHint] of [
    ['k1_small', '48454c4c4f', 1],           // "HELLO"
    ['k2_small', '48454c4c4f', 2],
    ['k3_medium', '48454c4c4f5f5354454747', 3],  // "HELLO_STEGG"
    ['k4_medium', '48454c4c4f5f5354454747', 4],
]) {
    // Fresh codec (fresh PRNG buffer) per case.
    const codec = new f5stego(KEY, MAX_PIXELS);
    const coeffs = make_coeffs();
    const payload = Buffer.from(payload_hex, 'hex');

    // Deep copy so we can report pre and post.
    const pre = Array.from(coeffs);
    const stats = codec._f5write(coeffs, Uint8Array.from(payload), kHint);
    const post = Array.from(coeffs);

    // Extract: rebuild PRNG on the same key, run f5get-style extraction
    // on a fresh copy of the post-embed coefficients.  We *can't* just
    // call codec.f5get() because that needs a jpeg frame; instead, we
    // mimic the f5get algorithm inline against the coeff array to get
    // the raw bit-stream.  Simpler: rely on the Python round-trip test.
    // For the matrix fixture we only pin _f5write output.

    cases.push({
        label,
        payload_hex,
        k: kHint,
        pre_coeffs: pre,
        post_coeffs: post,
        stats: {
            k: stats.k,
            embedded: stats.embedded,
            examined: stats.examined,
            changed: stats.changed,
            thrown: stats.thrown,
            efficiency: stats.efficiency,
        },
    });
}

const out = {
    generator: 'scripts/gen_f5_stegg_matrix_vectors.js',
    source: 'f5stego-lib.js',
    key_hex: Buffer.from(KEY).toString('hex'),
    max_pixels: MAX_PIXELS,
    seed: SEED,
    n: N,
    cases,
};

const outPath = path.join(REPO, 'tests/unit/fixtures/f5/matrix_stegg_vectors.json');
fs.writeFileSync(outPath, JSON.stringify(out) + '\n');   // compact — one big blob
console.log(`wrote ${outPath}`);
for (const c of cases) {
    console.log(`  ${c.label}: k=${c.stats.k} embedded=${c.stats.embedded} changed=${c.stats.changed} thrown=${c.stats.thrown}`);
}
