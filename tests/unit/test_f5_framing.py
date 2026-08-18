"""Tests for :mod:`f5_core._framing`."""

from __future__ import annotations

import pytest

from m3gast3gg.core.f5._framing import MAX_PAYLOAD, stegg_frame, stegg_unframe


@pytest.mark.parametrize("size", [0, 1, 100, 32767, 32768, 32769, 100_000, MAX_PAYLOAD])
def test_frame_unframe_roundtrip(size):
    payload = bytes(range(size % 251)) * (size // (size % 251) if (size % 251) else 1)
    payload = payload[:size]
    framed = stegg_frame(payload)
    assert stegg_unframe(framed) == payload


def test_2byte_header_for_small_payload():
    framed = stegg_frame(b"HELLO")
    assert framed[:2] == bytes([5, 0])
    assert framed[2:] == b"HELLO"


def test_3byte_header_for_large_payload():
    payload = b"A" * 32768
    framed = stegg_frame(payload)
    # 32768 = 0x8000: lo=0, mid = ((0x80) & 0x7F) | 0x80 = 0x80, hi = 0x01
    assert framed[:3] == bytes([0x00, 0x80, 0x01])
    assert framed[3:] == payload


def test_boundary_at_32767():
    """32767 fits in the 2-byte form; 32768 does not."""
    framed_small = stegg_frame(b"x" * 32767)
    framed_big = stegg_frame(b"x" * 32768)
    assert len(framed_small) == 32767 + 2
    assert len(framed_big) == 32768 + 3


def test_reject_oversized():
    with pytest.raises(ValueError):
        stegg_frame(b"x" * (MAX_PAYLOAD + 1))


def test_unframe_rejects_short_input():
    with pytest.raises(ValueError):
        stegg_unframe(b"")
    with pytest.raises(ValueError):
        stegg_unframe(b"\x01")


def test_unframe_rejects_truncated_3byte_prefix():
    with pytest.raises(ValueError):
        stegg_unframe(b"\x00\x80")  # 3-byte marker but only 2 bytes


def test_unframe_rejects_overlong_length():
    # header says 100 bytes but only 5 follow
    with pytest.raises(ValueError):
        stegg_unframe(bytes([100, 0]) + b"short")
