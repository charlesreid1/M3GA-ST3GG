"""Runtime tool-capability detection: tool checks, capability resolution, snapshot shape."""

from __future__ import annotations

import pytest

import capabilities as caps


@pytest.fixture(autouse=True)
def _fresh_cache():
    caps.clear_cache()
    yield
    caps.clear_cache()


def test_check_all_tools_covers_known_tools():
    result = caps.check_all_tools()
    expected = {"jpeglib", "piexif", "pyexiv2", "pikepdf", "pypdf", "apng",
                "PIL", "numpy", "cryptography",
                "exiftool", "steghide", "outguess", "ffmpeg", "qpdf"}
    assert expected.issubset(result.keys())


def test_check_all_tools_returns_toolcheck_instances():
    for name, tc in caps.check_all_tools().items():
        assert isinstance(tc, caps.ToolCheck)
        assert tc.name == name
        assert tc.kind in ("python", "binary")
        assert tc.status in ("available", "missing", "error")


def test_check_tool_unknown_raises_keyerror():
    with pytest.raises(KeyError):
        caps.check_tool("definitely-not-a-real-tool-name")


def test_check_tool_caches_result():
    # Second call returns the same object identity — cache hit, not a re-check.
    first = caps.check_tool("PIL")
    second = caps.check_tool("PIL")
    assert first is second


def test_pil_and_numpy_are_available():
    assert caps.check_tool("PIL").status == "available"
    assert caps.check_tool("numpy").status == "available"


def test_missing_package_carries_install_hint():
    tc = caps.check_tool("jpeglib")
    if tc.status == "missing":
        assert tc.install_hint and "stegg[jpeg]" in tc.install_hint


def test_missing_binary_carries_install_hint():
    tc = caps.check_tool("steghide")
    if tc.status == "missing":
        assert tc.install_hint and ("brew" in tc.install_hint or "apt" in tc.install_hint)


def test_pure_python_capabilities_are_available():
    resolved = caps.resolve_capability("png_lsb_1bit")
    assert resolved["status"] == "available"
    assert resolved["backend"] == "pure_python"


def test_resolve_unknown_capability_raises():
    with pytest.raises(KeyError):
        caps.resolve_capability("no_such_capability_key")


def test_jpeg_dct_f5_falls_back_to_pure_python():
    resolved = caps.resolve_capability("jpeg_dct_f5")
    assert resolved["status"] == "available"
    if caps.check_tool("jpeglib").status == "available":
        assert resolved["backend"] == "pkg:jpeglib"
    else:
        assert resolved["backend"] == "pure_python"
        assert "pkg:jpeglib" in resolved["promotable_to"]


def test_binary_only_capability_missing_when_binary_missing():
    resolved = caps.resolve_capability("jpeg_steghide")
    if caps.check_tool("steghide").status == "available":
        assert resolved["status"] == "available"
    else:
        assert resolved["status"] == "missing"
        assert resolved["backend"] is None
        names = [r["name"] for r in resolved["requires_any_of"]]
        assert "steghide" in names


def test_resolve_all_capabilities_covers_registry():
    result = caps.resolve_all_capabilities()
    assert set(result.keys()) == set(caps.TOOL_CAPABILITIES.keys())
    for entry in result.values():
        assert entry["status"] in ("available", "missing")


def test_snapshot_shape():
    snap = caps.snapshot()
    assert set(snap.keys()) == {"python_packages", "binaries", "tool_capabilities", "summary"}
    assert isinstance(snap["summary"], str)
    assert set(snap["tool_capabilities"].keys()) == set(caps.TOOL_CAPABILITIES.keys())
    assert "PIL" in snap["python_packages"]
    assert "numpy" in snap["python_packages"]
    assert "steghide" in snap["binaries"]
    assert "exiftool" in snap["binaries"]


def test_snapshot_summary_counts_match_capabilities():
    snap = caps.snapshot()
    total = len(snap["tool_capabilities"])
    available = sum(1 for c in snap["tool_capabilities"].values() if c["status"] == "available")
    assert f"{available}/{total}" in snap["summary"]
