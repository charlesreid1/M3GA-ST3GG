"""Runtime capability detection: probe registry, backend resolution, snapshot shape."""

from __future__ import annotations

import pytest

import capabilities as caps


@pytest.fixture(autouse=True)
def _fresh_cache():
    caps.clear_cache()
    yield
    caps.clear_cache()


def test_probe_all_covers_registered_probes():
    result = caps.probe_all()
    # A handful of known probes must show up. Names are stable public
    # API — renaming any of these is a breaking change.
    expected = {"jpeglib", "piexif", "pyexiv2", "pikepdf", "pypdf", "apng",
                "PIL", "numpy", "cryptography",
                "exiftool", "steghide", "outguess", "ffmpeg", "qpdf"}
    assert expected.issubset(result.keys())


def test_probe_all_returns_capability_instances():
    for name, cap in caps.probe_all().items():
        assert isinstance(cap, caps.Capability)
        assert cap.name == name
        assert cap.kind in ("python", "binary")
        assert cap.status in ("available", "missing", "error")


def test_get_unknown_probe_raises_keyerror():
    with pytest.raises(KeyError):
        caps.get("definitely-not-a-real-probe-name")


def test_get_caches_result():
    calls = {"n": 0}

    def probe():
        calls["n"] += 1
        return caps.Capability(name="tst", kind="python", status="missing")

    caps.register_probe("tst_cache", probe)
    try:
        assert caps.get("tst_cache").name == "tst"
        assert caps.get("tst_cache").name == "tst"
        assert calls["n"] == 1
    finally:
        # Registry has no unregister; leaving the probe registered but
        # cache is cleared between tests by the fixture.
        pass


def test_pil_and_numpy_are_available():
    # These are hard base-install deps; if a test env doesn't have them,
    # the whole suite is broken anyway.
    assert caps.get("PIL").status == "available"
    assert caps.get("numpy").status == "available"


def test_missing_package_carries_install_hint():
    # This probe is registered with an install hint; whether the package
    # is actually installed depends on the env, but the *hint* must be
    # present as a static attribute of the probe result when missing.
    cap = caps.get("jpeglib")
    if cap.status == "missing":
        assert cap.install_hint and "stegg[jpeg]" in cap.install_hint


def test_missing_binary_carries_install_hint():
    cap = caps.get("steghide")
    if cap.status == "missing":
        assert cap.install_hint and ("brew" in cap.install_hint or "apt" in cap.install_hint)


def test_pure_python_techniques_are_available():
    # png_lsb_1bit uses only stdlib+numpy+Pillow and must always resolve.
    resolved = caps.resolve_technique("png_lsb_1bit")
    assert resolved["status"] == "available"
    assert resolved["backend"] == "pure_python"


def test_resolve_unknown_technique_raises():
    with pytest.raises(KeyError):
        caps.resolve_technique("no_such_technique_key")


def test_jpeg_dct_f5_falls_back_to_pure_python():
    # When jpeglib is missing (the default on a bare install), F5 should
    # still resolve to pure_python with jpeglib listed as a promotion.
    resolved = caps.resolve_technique("jpeg_dct_f5")
    assert resolved["status"] == "available"
    if caps.get("jpeglib").status == "available":
        assert resolved["backend"] == "pkg:jpeglib"
    else:
        assert resolved["backend"] == "pure_python"
        assert "pkg:jpeglib" in resolved["promotable_to"]


def test_binary_only_technique_missing_when_binary_missing():
    # jpeg_steghide has no pure-Python fallback. When the binary is
    # missing, resolve_technique must report status=missing with a
    # requires_any_of pointer.
    resolved = caps.resolve_technique("jpeg_steghide")
    if caps.get("steghide").status == "available":
        assert resolved["status"] == "available"
    else:
        assert resolved["status"] == "missing"
        assert resolved["backend"] is None
        names = [r["name"] for r in resolved["requires_any_of"]]
        assert "steghide" in names


def test_techniques_supported_covers_all_registered():
    result = caps.techniques_supported()
    assert set(result.keys()) == set(caps.TECHNIQUES.keys())
    for entry in result.values():
        assert entry["status"] in ("available", "missing")


def test_snapshot_shape():
    snap = caps.snapshot()
    assert set(snap.keys()) == {"python_packages", "binaries", "techniques", "summary"}
    assert isinstance(snap["summary"], str)
    # Every technique in TECHNIQUES must appear in the snapshot.
    assert set(snap["techniques"].keys()) == set(caps.TECHNIQUES.keys())
    # PIL / numpy classified as python packages.
    assert "PIL" in snap["python_packages"]
    assert "numpy" in snap["python_packages"]
    # Binaries land in binaries even when missing.
    assert "steghide" in snap["binaries"]
    assert "exiftool" in snap["binaries"]


def test_snapshot_summary_counts_match_techniques():
    snap = caps.snapshot()
    total = len(snap["techniques"])
    available = sum(1 for t in snap["techniques"].values() if t["status"] == "available")
    assert f"{available}/{total}" in snap["summary"]
