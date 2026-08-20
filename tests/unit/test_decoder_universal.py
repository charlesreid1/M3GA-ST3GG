"""Universal decoder: detector-gated auto-decode with priority ranking."""

from __future__ import annotations

import pytest

from m3gast3gg.core.decoder import universal_decode


def test_empty_input_returns_empty_list():
    assert universal_decode("") == []


def test_top_k_zero_returns_empty_list():
    assert universal_decode("SGVsbG8=", top_k=0) == []


def test_base64_decodes_at_top():
    candidates = universal_decode("SGVsbG8sIFdvcmxkIQ==")
    assert len(candidates) >= 1
    top = candidates[0]
    assert top.method == "Base64"
    assert top.slug == "base64"
    assert top.text == "Hello, World!"


def test_hex_decodes():
    # "Hello" -> hex -> priority 290 (higher than base64's 270)
    candidates = universal_decode("48656c6c6f")
    slugs = [c.slug for c in candidates]
    assert "hex" in slugs
    hex_candidate = next(c for c in candidates if c.slug == "hex")
    assert hex_candidate.text == "Hello"


def test_base32_decodes():
    # base32 of "hello"
    candidates = universal_decode("NBSWY3DP")
    slugs = [c.slug for c in candidates]
    assert "base32" in slugs
    b32 = next(c for c in candidates if c.slug == "base32")
    assert b32.text == "hello"


def test_binary_decodes():
    candidates = universal_decode("01001000 01101001")
    slugs = [c.slug for c in candidates]
    assert "binary" in slugs
    b = next(c for c in candidates if c.slug == "binary")
    assert b.text == "Hi"


def test_morse_decodes():
    # SOS
    candidates = universal_decode("... --- ...")
    slugs = [c.slug for c in candidates]
    assert "morse" in slugs
    m = next(c for c in candidates if c.slug == "morse")
    assert m.text == "SOS"


def test_url_decodes():
    candidates = universal_decode("Hello%20World")
    slugs = [c.slug for c in candidates]
    assert "url" in slugs


def test_ciphers_do_not_auto_fire():
    """Caesar / ROT13 / Atbash / Vigenere have detector=None; plain letters
    should not surface them from the auto-decoder."""
    candidates = universal_decode("Fyyfhp fy ifbs")
    slugs = [c.slug for c in candidates]
    assert "caesar" not in slugs
    assert "rot13" not in slugs
    assert "atbash" not in slugs
    assert "vigenere" not in slugs


def test_candidates_sorted_by_priority_desc():
    candidates = universal_decode("48656c6c6f")
    if len(candidates) < 2:
        pytest.skip("need multiple candidates")
    priorities = [c.priority for c in candidates]
    assert priorities == sorted(priorities, reverse=True)


def test_include_low_confidence_flag_filters():
    all_candidates = universal_decode("SGVsbG8=", include_low_confidence=True)
    filtered = universal_decode("SGVsbG8=", include_low_confidence=False)
    assert len(filtered) <= len(all_candidates)
    assert all(not c.low_confidence for c in filtered)


def test_no_op_reverse_not_returned():
    """A transform whose reverse is a no-op on the input should not appear —
    otherwise every candidate whose detector fires on ASCII would clutter."""
    candidates = universal_decode("plain english sentence")
    # Only detector-firing transforms fire; ciphers are gated out; nothing
    # should return the input verbatim.
    for c in candidates:
        assert c.text != "plain english sentence"


def test_homoglyph_decodes():
    """Cyrillic look-alike letters detected + reversed."""
    text = "Неllо"  # Cyrillic H, then Latin ell/ell/oh? actually mixed
    candidates = universal_decode(text)
    slugs = [c.slug for c in candidates]
    assert "homoglyph" in slugs
