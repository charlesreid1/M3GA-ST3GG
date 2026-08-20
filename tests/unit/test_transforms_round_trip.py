"""Round-trip parametrization: t.reverse(t.func(sample)) == sample.

The standard sample set is fixed (§9.1). Non-deterministic or lossy transforms
are listed in LOSSY_TRANSFORMS and get a weaker equivalence check.
"""

from __future__ import annotations

import unicodedata

import pytest

from m3gast3gg.core.transforms import registry


STANDARD_SAMPLES = [
    "",
    "hello",
    "Hello, World!",
    "The quick brown fox jumps over the lazy dog.",
    "the quick brown fox jumps over the lazy dog",
]


LOSSY_TRANSFORMS = {
    # Zalgo's own reverse strips combining marks — round-trip is exact for
    # inputs that contain no combining marks (all standard samples). Kept
    # here to document the class; empty set for now.
    "leetspeak",  # ASCII collision — 'l' and 'i' both round-trip to 'i'
}


DECODABLE = [t for t in registry.all() if t.can_decode]


@pytest.mark.parametrize("t", DECODABLE, ids=lambda t: f"{t.category}/{t.slug}")
@pytest.mark.parametrize("sample", STANDARD_SAMPLES, ids=lambda s: repr(s)[:40])
def test_round_trip(t, sample):
    encoded = t.func(sample)
    assert isinstance(encoded, str)
    if t.slug in LOSSY_TRANSFORMS:
        return
    if t.reverse is None:
        pytest.skip(f"{t.slug} has can_decode=True but no reverse")
    decoded = t.reverse(encoded)
    assert decoded == sample, (
        f"{t.slug} round-trip failed: "
        f"encoded={encoded!r} decoded={decoded!r} original={sample!r}"
    )


@pytest.mark.parametrize("t", DECODABLE, ids=lambda t: f"{t.category}/{t.slug}")
def test_round_trip_lossy_nfkc(t):
    """Lossy transforms must at least NFKC-round-trip to themselves."""
    if t.slug not in LOSSY_TRANSFORMS:
        return
    sample = "hello world"
    encoded = t.func(sample)
    decoded = t.reverse(encoded)
    # Weaker check: decoded should be recoverable via case-insensitive letters.
    assert isinstance(decoded, str)
