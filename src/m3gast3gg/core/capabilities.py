"""Runtime tool-capability detection for stegg.

Two levels:

- **Tool check** — is a specific Python package importable, or a specific
  binary on ``$PATH``? Yes/no, plus a version string if we can grab one.
- **Tool capability** — a high-level thing the caller wants to do (e.g.
  "write EXIF to a JPEG"), backed by an ordered list of tool checks.
  The first installed one wins.

Call :func:`snapshot` once per session (via the MCP ``stegg_capabilities``
tool) and cache it. Tool checks are cached per-process — they're cheap
but not free.
"""

from __future__ import annotations

import importlib
import importlib.util
import shutil
import subprocess
from dataclasses import asdict, dataclass
from typing import Dict, List, Literal, Optional

Status = Literal["available", "missing", "error"]
Kind = Literal["python", "binary"]


@dataclass(frozen=True)
class ToolCheck:
    """Result of checking one tool: one Python package or one binary."""

    name: str
    kind: Kind
    status: Status
    version: Optional[str] = None
    path: Optional[str] = None
    detail: Optional[str] = None
    install_hint: Optional[str] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


# ---------------------------------------------------------------------------
# Tool checks
# ---------------------------------------------------------------------------

def _check_python_package(name: str, install_hint: Optional[str] = None) -> ToolCheck:
    if importlib.util.find_spec(name) is None:
        return ToolCheck(name, "python", "missing", install_hint=install_hint)
    try:
        module = importlib.import_module(name)
    except Exception as exc:
        return ToolCheck(
            name, "python", "error",
            detail=f"{type(exc).__name__}: {exc}",
            install_hint=install_hint,
        )
    version = getattr(module, "__version__", None)
    return ToolCheck(name, "python", "available", version=str(version) if version else None)


def _check_binary(name: str, version_args: List[str], install_hint: Optional[str] = None) -> ToolCheck:
    path = shutil.which(name)
    if path is None:
        return ToolCheck(name, "binary", "missing", install_hint=install_hint)
    version = None
    try:
        proc = subprocess.run(
            [path, *version_args],
            capture_output=True, text=True, timeout=2.0, check=False,
        )
        first = (proc.stdout or proc.stderr or "").strip().splitlines()
        if first:
            version = first[0].strip()[:120]
    except Exception:
        pass
    return ToolCheck(name, "binary", "available", path=path, version=version)


# name -> install_hint (None = ships with the base install)
_PYTHON_PACKAGES: Dict[str, Optional[str]] = {
    "jpeglib":      "pip install 'stegg[jpeg]'",
    "piexif":       "pip install 'stegg[metadata]'",
    "pyexiv2":      "pip install 'stegg[metadata]'",
    "pikepdf":      "pip install 'stegg[pdf]'",
    "pypdf":        "pip install 'stegg[pdf]'",
    "apng":         "pip install apng",
    "cryptography": "pip install 'stegg[crypto]'",
    "PIL":          None,
    "numpy":        None,
}

# name -> (version_args, install_hint)
_BINARIES: Dict[str, tuple] = {
    "exiftool": (["-ver"],      "brew install exiftool  # or: apt install libimage-exiftool-perl"),
    "steghide": (["--version"], "brew install steghide  # or: apt install steghide"),
    "outguess": (["-h"],        "brew install outguess  # or: apt install outguess"),
    "ffmpeg":   (["-version"],  "brew install ffmpeg  # or: apt install ffmpeg"),
    "qpdf":     (["--version"], "brew install qpdf  # or: apt install qpdf"),
}

_TOOL_CHECK_CACHE: Dict[str, ToolCheck] = {}


def clear_cache() -> None:
    """Drop the per-process tool-check cache. For tests."""
    _TOOL_CHECK_CACHE.clear()


def check_tool(name: str) -> ToolCheck:
    """Run one tool check (cached). Raises ``KeyError`` for unknown names."""
    if name in _TOOL_CHECK_CACHE:
        return _TOOL_CHECK_CACHE[name]
    if name in _PYTHON_PACKAGES:
        result = _check_python_package(name, _PYTHON_PACKAGES[name])
    elif name in _BINARIES:
        args, hint = _BINARIES[name]
        result = _check_binary(name, args, hint)
    else:
        raise KeyError(f"no such tool check: {name!r}")
    _TOOL_CHECK_CACHE[name] = result
    return result


def check_all_tools() -> Dict[str, ToolCheck]:
    return {n: check_tool(n) for n in (*_PYTHON_PACKAGES, *_BINARIES)}


# ---------------------------------------------------------------------------
# Tool capabilities
#
# Each entry is (family, description, backend_menu). The menu is ordered:
# the first backend whose tool check passes wins. Menu entries name a
# Python package ("pkg:jpeglib"), a binary ("bin:exiftool"), or the
# sentinel "pure_python" (always available).
# ---------------------------------------------------------------------------

TOOL_CAPABILITIES: Dict[str, tuple] = {
    # image: LSB family (base install, always available)
    "png_lsb_1bit":       ("image", "PNG LSB, 1 bit per channel. Highest-stealth LSB variant.",              ["pure_python"]),
    "png_lsb_2bit":       ("image", "PNG LSB, 2 bits per channel. Double the capacity, still stealthy.",    ["pure_python"]),
    "png_lsb_specter":    ("image", "Specter LSB — password-driven cipher stack over LSB.",                 ["pure_python"]),
    "png_pvd":            ("image", "Pixel-value differencing. Harder to detect via histogram than LSB.",   ["pure_python"]),
    # image: PNG metadata (base install)
    "png_tEXt":           ("image", "Plaintext PNG tEXt ancillary chunk.",                                  ["pure_python"]),
    "png_zTXt":           ("image", "Compressed PNG zTXt ancillary chunk.",                                 ["pure_python"]),
    "png_iTXt":           ("image", "International PNG iTXt ancillary chunk (UTF-8 keyword + text).",       ["pure_python"]),
    "png_private_chunk":  ("image", "Caller-defined 4-char private PNG chunk.",                             ["pure_python"]),
    "png_trailing_bytes": ("image", "Payload appended after the PNG IEND marker.",                          ["pure_python"]),
    # image: JPEG DCT family
    "jpeg_dct_f5":        ("image", "F5 algorithm on JPEG DCT coefficients. Survives JPEG recompression.",  ["pkg:jpeglib", "pure_python"]),
    "jpeg_dct_jsteg":     ("image", "JSteg: LSB of nonzero DCT coefficients. Simple, detectable.",          ["pkg:jpeglib", "pure_python"]),
    "jpeg_dct_specter":   ("image", "Specter DCT — password-driven cipher stack over DCT coefficients.",    ["pure_python"]),
    "jpeg_steghide":      ("image", "steghide external tool. Separate algorithm, not an F5 backend.",       ["bin:steghide"]),
    "jpeg_outguess":      ("image", "OutGuess external tool. Separate algorithm.",                          ["bin:outguess"]),
    "jpeg_trailing_bytes":("image", "Payload appended after the JPEG EOI marker.",                          ["pure_python"]),
    # image: JPEG metadata write side
    "jpeg_exif":          ("image", "Write EXIF fields to a JPEG.",                                         ["pkg:pyexiv2", "bin:exiftool", "pkg:piexif"]),
    "jpeg_xmp":           ("image", "Write XMP metadata to a JPEG.",                                        ["pkg:pyexiv2", "bin:exiftool"]),
    "jpeg_iptc":          ("image", "Write IPTC metadata to a JPEG.",                                       ["pkg:pyexiv2", "bin:exiftool"]),
    "icc_profile":        ("image", "Write or manipulate an ICC color profile chunk.",                      ["pkg:pyexiv2", "bin:exiftool"]),
    # image: container smuggling
    "container_apng":         ("image", "APNG multi-frame container smuggling.",                            ["pkg:apng", "pure_python"]),
    "container_gif":          ("image", "GIF comment/application-extension smuggling.",                     ["pure_python"]),
    "container_pdf_multipage":("image", "Multi-page PDF authoring with payload smuggling.",                 ["pkg:pikepdf", "pkg:pypdf", "bin:qpdf"]),
    "polyglot_png_zip":       ("image", "PNG that is also a valid ZIP (concatenation polyglot).",           ["pure_python"]),
    "polyglot_zip_png":       ("image", "ZIP that is also a valid PNG.",                                    ["pure_python"]),
    # audio
    "audio_lsb_wav":              ("audio", "LSB in PCM WAV samples.",                                      ["pure_python"]),
    "container_multitrack_audio": ("audio", "Multi-track audio container smuggling. Requires ffmpeg.",      ["bin:ffmpeg"]),
}


def _backend_installed(entry: str) -> bool:
    if entry == "pure_python":
        return True
    try:
        return check_tool(entry.split(":", 1)[1]).status == "available"
    except (KeyError, IndexError):
        return False


def _backend_tool_check(entry: str) -> Optional[ToolCheck]:
    if entry == "pure_python":
        return None
    try:
        return check_tool(entry.split(":", 1)[1])
    except (KeyError, IndexError):
        return None


def resolve_capability(name: str) -> dict:
    """Resolve one tool capability against the current tool-check cache.

    Returns:
      - ``status``: "available" if any menu entry is usable, else "missing".
      - ``backend``: winning entry, or None.
      - ``promotable_to``: entries ordered *before* the winner (they'd take
        over if installed). Only present when status is "available".
      - ``requires_any_of``: entries that would satisfy the capability, with
        install hints. Only present when status is "missing".
    """
    try:
        _, _, menu = TOOL_CAPABILITIES[name]
    except KeyError:
        raise KeyError(f"no such tool capability: {name!r}")

    for i, entry in enumerate(menu):
        if _backend_installed(entry):
            return {
                "status": "available",
                "backend": entry,
                "promotable_to": menu[:i],
            }

    requires: List[dict] = []
    for entry in menu:
        tc = _backend_tool_check(entry)
        if tc is not None:
            requires.append({
                "name": tc.name,
                "kind": tc.kind,
                "install_hint": tc.install_hint,
            })
    return {"status": "missing", "backend": None, "requires_any_of": requires}


def resolve_all_capabilities() -> Dict[str, dict]:
    return {name: resolve_capability(name) for name in TOOL_CAPABILITIES}


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------

def snapshot() -> dict:
    """Full snapshot: tool checks, tool capabilities, and a one-line
    summary suitable for the persona's session cache.
    """
    python_packages: Dict[str, dict] = {}
    binaries: Dict[str, dict] = {}
    for tc in check_all_tools().values():
        entry = tc.to_dict()
        entry.pop("name", None)
        entry.pop("kind", None)
        (python_packages if tc.kind == "python" else binaries)[tc.name] = entry

    capabilities = resolve_all_capabilities()
    total = len(capabilities)
    available = sum(1 for c in capabilities.values() if c["status"] == "available")
    summary = f"{available}/{total} tool capabilities available; {total - available} need optional installs."

    return {
        "python_packages": python_packages,
        "binaries": binaries,
        "tool_capabilities": capabilities,
        "summary": summary,
    }


__all__ = [
    "ToolCheck",
    "TOOL_CAPABILITIES",
    "check_tool",
    "check_all_tools",
    "clear_cache",
    "resolve_capability",
    "resolve_all_capabilities",
    "snapshot",
]
