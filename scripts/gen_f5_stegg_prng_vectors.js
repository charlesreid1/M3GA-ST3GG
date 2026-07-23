/*
 * Regenerate the pinned F5Stegg PRNG parity vectors used by
 * tests/unit/test_f5_prng_stegg.py.
 *
 * Loads f5stego-lib.js, instantiates the codec with a fixed key, and
 * dumps:
 *   - the first N bytes of the raw randPool (RC4 keystream), which
 *     covers both the permutation-word region and the start of the
 *     gamma region;
 *   - a Fisher-Yates permutation of an int32 array of length L, using
 *     the same shuffle the F5 embed/extract paths use;
 *   - the first M bytes of the gamma tail that immediately follows the
 *     L*4 permutation-word bytes.
 *
 * Run once:   node scripts/gen_f5_stegg_prng_vectors.js
 * Output:     tests/unit/fixtures/f5/prng_stegg_vectors.json
 *
 * We intentionally use a small maxPixels so the fixture file stays
 * small.  The Python port must match byte-for-byte at these parameters.
 */

'use strict';

const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '..');
const f5stego = require(path.join(REPO, 'f5stego-lib.js'));

// --- fixture parameters -----------------------------------------------------

// Fixed key: 4 bytes.  Small enough to hand-verify KSA, but not degenerate.
const KEY = Uint8Array.from([0x00, 0x01, 0x02, 0x03]);

// A tiny maxPixels so randPool is small.  4.125 * MAX_PIXELS bytes total.
// 4096 -> randPool of 16896 bytes.  Plenty to cover our vector sizes without
// bloating the fixture.
const MAX_PIXELS = 4096;

// How many keystream bytes to pin.
const KEYSTREAM_BYTES = 128;

// Length of the permutation vector.  Must be small enough that we can pin
// the whole permutation in the fixture, but big enough to exercise the
// Fisher-Yates loop past its first few iterations.
const PERM_LEN = 64;

// How many post-permutation gamma bytes to pin.  These are the bytes at
// randPool offset PERM_LEN * 4.
const GAMMA_BYTES = 64;

// ---------------------------------------------------------------------------

const codec = new f5stego(KEY, MAX_PIXELS);

// Snapshot the raw keystream before stegShuffle is called on it.
// randPool is on the instance; grab its first bytes.
const keystream = Array.from(new Uint8Array(codec.randPool).slice(0, KEYSTREAM_BYTES));

// Fisher-Yates over an int32 array of length PERM_LEN.  This matches the
// "typeof pm == 'number'" branch of stegShuffle, which is what f5put uses
// on the coefficient count.
const shuffled = codec.stegShuffle(PERM_LEN);
const permutation = Array.from(shuffled.pm);

// Gamma tail: bytes that would be consumed by embed/extract for XOR-masking
// header + payload bytes.  These live at offset PERM_LEN * 4 in randPool.
const gamma = Array.from(shuffled.gamma.slice(0, GAMMA_BYTES));

const out = {
    generator: 'scripts/gen_f5_stegg_prng_vectors.js',
    source: 'f5stego-lib.js',
    key_hex: Buffer.from(KEY).toString('hex'),
    max_pixels: MAX_PIXELS,
    keystream_first_bytes: keystream,
    perm_len: PERM_LEN,
    permutation: permutation,
    gamma_first_bytes: gamma,
};

const outPath = path.join(REPO, 'tests/unit/fixtures/f5/prng_stegg_vectors.json');
fs.writeFileSync(outPath, JSON.stringify(out, null, 2) + '\n');
console.log(`wrote ${outPath}`);
console.log(`  keystream[0..8] = ${keystream.slice(0, 8).map(b => b.toString(16).padStart(2, '0')).join(' ')}`);
console.log(`  permutation[0..8] = ${permutation.slice(0, 8).join(' ')}`);
console.log(`  gamma[0..8] = ${gamma.slice(0, 8).map(b => b.toString(16).padStart(2, '0')).join(' ')}`);
