/*
 * Regenerate pinned _analyze parity vectors for the F5Stegg matrix
 * layer, computed against a small synthetic coefficient array (so the
 * fixture doesn't depend on jpeglib's block ordering).
 *
 * We build a deterministic int16 array of length N whose distribution
 * of zeros, ones, and larger coefficients exercises the analyze loop,
 * then run _analyze on it via a bare f5stego instance.
 *
 * Output: tests/unit/fixtures/f5/analyze_stegg_vectors.json
 */

'use strict';

const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '..');
const f5stego = require(path.join(REPO, 'f5stego-lib.js'));

// Same seed-driven synthetic array used on the Python side of the test.
// N must be a multiple of 64 so the DC-block guard fires cleanly.
const N = 64 * 100;  // 100 blocks
const SEED = 0x2b3c4d5e;

function make_coeffs() {
    // Xorshift32 PRNG so the fixture is deterministic and easily
    // replayable in Python.  Yields an int16 in a plausible F5 range.
    let s = SEED >>> 0;
    const buf = new Int16Array(N);
    for (let i = 0; i < N; i++) {
        s ^= s << 13; s >>>= 0;
        s ^= s >>> 17; s >>>= 0;
        s ^= s << 5;  s >>>= 0;
        // DCs (i % 64 === 0) can be any int16 — analyze skips them.
        if (i % 64 === 0) { buf[i] = ((s & 0xffff) - 0x8000) | 0; continue; }
        // AC: mostly zeros, some +/-1, some larger.
        const roll = s % 100;
        let v;
        if (roll < 60) v = 0;
        else if (roll < 85) v = (s & 1) ? 1 : -1;
        else v = ((s & 0xffff) - 0x8000) >> 8;
        buf[i] = v;
    }
    return buf;
}

const KEY = Uint8Array.from([0xaa, 0xbb, 0xcc]);
const codec = new f5stego(KEY, 4096);
const coeffs = make_coeffs();

const result = codec._analyze(coeffs);

const out = {
    generator: 'scripts/gen_f5_stegg_analyze_vectors.js',
    source: 'f5stego-lib.js',
    key_hex: Buffer.from(KEY).toString('hex'),
    seed: SEED,
    n: N,
    coeff_first_bytes: Array.from(coeffs.slice(0, 32)),
    analyze: {
        capacity: Array.from(result.capacity),
        coeff_total: result.coeff_total,
        coeff_large: result.coeff_large,
        coeff_zero: result.coeff_zero,
        coeff_one: result.coeff_one,
        coeff_one_ratio: result.coeff_one_ratio,
    },
};

const outPath = path.join(REPO, 'tests/unit/fixtures/f5/analyze_stegg_vectors.json');
fs.writeFileSync(outPath, JSON.stringify(out, null, 2) + '\n');
console.log(`wrote ${outPath}`);
console.log(`  capacity[0..5] = ${result.capacity.slice(0, 5).join(' ')}`);
console.log(`  coeff_zero=${result.coeff_zero} coeff_one=${result.coeff_one} coeff_large=${result.coeff_large}`);
