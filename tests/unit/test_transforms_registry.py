"""Registry integrity: no duplicates, priorities in range, categories known."""

from __future__ import annotations

import pytest

from m3gast3gg.core.transforms import registry
from m3gast3gg.core.transforms.base import VALID_CATEGORIES, VALID_INPUT_KINDS


ALL = registry.all()


def test_registry_is_nonempty():
    assert len(ALL) > 0


def test_no_duplicate_slugs():
    slugs = [t.slug for t in ALL]
    assert len(slugs) == len(set(slugs))


def test_no_duplicate_names():
    names = [t.name for t in ALL]
    assert len(names) == len(set(names))


@pytest.mark.parametrize("t", ALL, ids=lambda t: f"{t.category}/{t.slug}")
def test_priority_range(t):
    assert 0 <= t.priority <= 310


@pytest.mark.parametrize("t", ALL, ids=lambda t: f"{t.category}/{t.slug}")
def test_category_known(t):
    assert t.category in VALID_CATEGORIES


@pytest.mark.parametrize("t", ALL, ids=lambda t: f"{t.category}/{t.slug}")
def test_input_kind_known(t):
    assert t.input_kind in VALID_INPUT_KINDS


@pytest.mark.parametrize("t", ALL, ids=lambda t: f"{t.category}/{t.slug}")
def test_can_decode_implies_reverse_or_map(t):
    if t.can_decode:
        assert t.reverse is not None or t.map is not None


@pytest.mark.parametrize("t", ALL, ids=lambda t: f"{t.category}/{t.slug}")
def test_detector_never_raises(t):
    if t.detector is None:
        return
    for sample in ["", "abc", "\x00\x01\x02", "日本語 🎉", "AAAA=" * 10]:
        try:
            result = t.detector(sample)
        except Exception as exc:  # pragma: no cover — test failure body
            pytest.fail(f"{t.name} detector raised on {sample!r}: {exc!r}")
        assert isinstance(result, bool)


def test_lookup_by_slug_and_name():
    fw = registry.get("fullwidth")
    assert fw.name == "Fullwidth"
    same = registry.get("Fullwidth")
    assert same is fw


def test_unknown_lookup_raises():
    with pytest.raises(KeyError):
        registry.get("does-not-exist-transform")


def test_by_category_returns_subset():
    encoding = registry.by_category("encoding")
    assert len(encoding) > 0
    assert all(t.category == "encoding" for t in encoding)
