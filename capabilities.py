"""Runtime capability detection for stegg.

Reports what the current Python process can actually do:

- Which optional Python packages are importable (`jpeglib`, `piexif`,
  `pyexiv2`, `pikepdf`, …).
- Which external binaries are on ``PATH`` (`exiftool`, `steghide`,
  `outguess`, `ffmpeg`).
- For each *technique key* used by the transport-survivability matrix,
  whether at least one backend is usable right now, which one is the
  default, and how to promote to a better one.

The persona is expected to call :func:`snapshot` (via the MCP
``stegg_capabilities`` tool) **once per session** and cache the result.
Every image/audio/metadata technique should be introduced with a check:
if the technique's status is ``missing`` the persona names the install
step instead of pretending it works.

Every probe is cached per-process — probes are cheap
(``importlib.util.find_spec`` + ``shutil.which``) but not free, and we
want repeated MCP calls to be O(dict lookup).
"""

from __future__ import annotations

import importlib
import importlib.util
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from typing import Callable, Dict, List, Literal, Optional

Status = Literal["available", "missing", "error"]
Kind = Literal["python", "binary"]
TechniqueStatus = Literal["available", "missing"]


@dataclass(frozen=True)
class Capability:
    """A single probe result: one package or one binary."""

    name: str
    kind: Kind
    status: Status
    version: Optional[str] = None
    path: Optional[str] = None
    detail: Optional[str] = None
    install_hint: Optional[str] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass(frozen=True)
class Technique:
    """How one technique maps onto the available backends.

    ``backend_menu`` is ordered — first entry whose capabilities are met
    wins. Each menu entry names either a Python package
    (``"pkg:jpeglib"``), a binary (``"bin:exiftool"``), or the sentinel
    ``"pure_python"`` (always available).
    """

    key: str
    family: str
    description: str
    backend_menu: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Probe registry
# ---------------------------------------------------------------------------

ProbeFn = Callable[[], Capability]
_PROBES: Dict[str, ProbeFn] = {}
_CACHE: Dict[str, Capability] = {}


def register_probe(name: str, fn: ProbeFn) -> None:
    """Register a probe. Idempotent — re-registering the same name replaces."""
    _PROBES[name] = fn


def clear_cache() -> None:
    """Drop the per-process probe cache. Tests use this; callers rarely need it."""
    _CACHE.clear()


def get(name: str) -> Capability:
    """Run one probe (cached). Raises ``KeyError`` for unknown names."""
    if name in _CACHE:
        return _CACHE[name]
    if name not in _PROBES:
        raise KeyError(f"no such probe: {name!r}")
    result = _PROBES[name]()
    _CACHE[name] = result
    return result


def probe_all() -> Dict[str, Capability]:
    """Run every registered probe. Cached per-process."""
    return {name: get(name) for name in _PROBES}


# ---------------------------------------------------------------------------
# Probe primitives
# ---------------------------------------------------------------------------

def _probe_python_package(
    name: str,
    *,
    install_hint: Optional[str] = None,
    version_attr: str = "__version__",
) -> Capability:
    spec = importlib.util.find_spec(name)
    if spec is None:
        return Capability(
            name=name,
            kind="python",
            status="missing",
            install_hint=install_hint,
        )
    try:
        module = importlib.import_module(name)
    except Exception as exc:
        return Capability(
            name=name,
            kind="python",
            status="error",
            detail=f"{type(exc).__name__}: {exc}",
            install_hint=install_hint,
        )
    version = getattr(module, version_attr, None)
    if version is not None:
        version = str(version)
    return Capability(
        name=name,
        kind="python",
        status="available",
        version=version,
    )


def _probe_binary(
    name: str,
    *,
    version_args: Optional[List[str]] = None,
    install_hint: Optional[str] = None,
    timeout: float = 2.0,
) -> Capability:
    path = shutil.which(name)
    if path is None:
        return Capability(
            name=name,
            kind="binary",
            status="missing",
            install_hint=install_hint,
        )
    version = None
    if version_args:
        try:
            proc = subprocess.run(
                [path, *version_args],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            out = (proc.stdout or proc.stderr or "").strip().splitlines()
            if out:
                version = out[0].strip()[:120]
        except Exception:
            version = None
    return Capability(
        name=name,
        kind="binary",
        status="available",
        path=path,
        version=version,
    )


# ---------------------------------------------------------------------------
# Seed probes
#
# Every probe below covers something the transport-survivability plan
# eventually wants to promote a matrix cell for. Missing tools always
# report `missing` with an install hint; nothing here throws on a fresh
# install.
# ---------------------------------------------------------------------------

# Python packages — optional, promotable backends
register_probe(
    "jpeglib",
    lambda: _probe_python_package(
        "jpeglib",
        install_hint="pip install 'stegg[jpeg]'",
    ),
)
register_probe(
    "piexif",
    lambda: _probe_python_package(
        "piexif",
        install_hint="pip install 'stegg[metadata]'",
    ),
)
register_probe(
    "pyexiv2",
    lambda: _probe_python_package(
        "pyexiv2",
        install_hint="pip install 'stegg[metadata]'",
    ),
)
register_probe(
    "pikepdf",
    lambda: _probe_python_package(
        "pikepdf",
        install_hint="pip install 'stegg[pdf]'",
    ),
)
register_probe(
    "pypdf",
    lambda: _probe_python_package(
        "pypdf",
        install_hint="pip install 'stegg[pdf]'",
    ),
)
register_probe(
    "apng",
    lambda: _probe_python_package(
        "apng",
        install_hint="pip install apng",
    ),
)

# Python packages that ship in the base install — probing them tells the
# persona what pure-Python fallbacks are available.
register_probe(
    "PIL",
    lambda: _probe_python_package(
        "PIL",
        version_attr="__version__",
    ),
)
register_probe(
    "numpy",
    lambda: _probe_python_package(
        "numpy",
        version_attr="__version__",
    ),
)
register_probe(
    "cryptography",
    lambda: _probe_python_package(
        "cryptography",
        install_hint="pip install 'stegg[crypto]'",
    ),
)

# External binaries — best-fidelity implementations for their domains
register_probe(
    "exiftool",
    lambda: _probe_binary(
        "exiftool",
        version_args=["-ver"],
        install_hint="brew install exiftool  # or: apt install libimage-exiftool-perl",
    ),
)
register_probe(
    "steghide",
    lambda: _probe_binary(
        "steghide",
        version_args=["--version"],
        install_hint="brew install steghide  # or: apt install steghide",
    ),
)
register_probe(
    "outguess",
    lambda: _probe_binary(
        "outguess",
        version_args=["-h"],
        install_hint="brew install outguess  # or: apt install outguess",
    ),
)
register_probe(
    "ffmpeg",
    lambda: _probe_binary(
        "ffmpeg",
        version_args=["-version"],
        install_hint="brew install ffmpeg  # or: apt install ffmpeg",
    ),
)
register_probe(
    "qpdf",
    lambda: _probe_binary(
        "qpdf",
        version_args=["--version"],
        install_hint="brew install qpdf  # or: apt install qpdf",
    ),
)


# ---------------------------------------------------------------------------
# Technique registry
#
# One entry per technique key the transport-survivability matrix wants to
# be able to reference. Every entry lists the ordered backend_menu; the
# resolver below picks the first available one.
# ---------------------------------------------------------------------------

TECHNIQUES: Dict[str, Technique] = {
    # ---- image: LSB family (base install, always available) ----
    "png_lsb_1bit": Technique(
        key="png_lsb_1bit",
        family="image",
        description="PNG LSB, 1 bit per channel. Highest-stealth LSB variant.",
        backend_menu=["pure_python"],
    ),
    "png_lsb_2bit": Technique(
        key="png_lsb_2bit",
        family="image",
        description="PNG LSB, 2 bits per channel. Double the capacity, still stealthy.",
        backend_menu=["pure_python"],
    ),
    "png_lsb_specter": Technique(
        key="png_lsb_specter",
        family="image",
        description="Specter LSB — password-driven cipher stack over LSB.",
        backend_menu=["pure_python"],
    ),
    "png_pvd": Technique(
        key="png_pvd",
        family="image",
        description="Pixel-value differencing. Harder to detect via histogram than LSB.",
        backend_menu=["pure_python"],
    ),
    # ---- image: PNG metadata (base install) ----
    "png_tEXt": Technique(
        key="png_tEXt",
        family="image",
        description="Plaintext PNG tEXt ancillary chunk.",
        backend_menu=["pure_python"],
    ),
    "png_zTXt": Technique(
        key="png_zTXt",
        family="image",
        description="Compressed PNG zTXt ancillary chunk.",
        backend_menu=["pure_python"],
    ),
    "png_iTXt": Technique(
        key="png_iTXt",
        family="image",
        description="International PNG iTXt ancillary chunk (UTF-8 keyword + text).",
        backend_menu=["pure_python"],
    ),
    "png_private_chunk": Technique(
        key="png_private_chunk",
        family="image",
        description="Caller-defined 4-char private PNG chunk.",
        backend_menu=["pure_python"],
    ),
    "png_trailing_bytes": Technique(
        key="png_trailing_bytes",
        family="image",
        description="Payload appended after the PNG IEND marker.",
        backend_menu=["pure_python"],
    ),
    # ---- image: JPEG DCT family (gap targets from the coverage plan) ----
    "jpeg_dct_f5": Technique(
        key="jpeg_dct_f5",
        family="image",
        description="F5 algorithm on JPEG DCT coefficients. Survives JPEG recompression.",
        backend_menu=["pkg:jpeglib", "pure_python"],
    ),
    "jpeg_dct_jsteg": Technique(
        key="jpeg_dct_jsteg",
        family="image",
        description="JSteg: LSB of nonzero DCT coefficients. Simple, detectable.",
        backend_menu=["pkg:jpeglib", "pure_python"],
    ),
    "jpeg_dct_specter": Technique(
        key="jpeg_dct_specter",
        family="image",
        description="Specter DCT — password-driven cipher stack over DCT coefficients.",
        backend_menu=["pure_python"],
    ),
    "jpeg_steghide": Technique(
        key="jpeg_steghide",
        family="image",
        description="steghide external tool. Separate algorithm, not an F5 backend.",
        backend_menu=["bin:steghide"],
    ),
    "jpeg_outguess": Technique(
        key="jpeg_outguess",
        family="image",
        description="OutGuess external tool. Separate algorithm.",
        backend_menu=["bin:outguess"],
    ),
    "jpeg_trailing_bytes": Technique(
        key="jpeg_trailing_bytes",
        family="image",
        description="Payload appended after the JPEG EOI marker.",
        backend_menu=["pure_python"],
    ),
    # ---- image: JPEG metadata write side ----
    "jpeg_exif": Technique(
        key="jpeg_exif",
        family="image",
        description="Write EXIF fields to a JPEG.",
        backend_menu=["pkg:pyexiv2", "bin:exiftool", "pkg:piexif"],
    ),
    "jpeg_xmp": Technique(
        key="jpeg_xmp",
        family="image",
        description="Write XMP metadata to a JPEG.",
        backend_menu=["pkg:pyexiv2", "bin:exiftool"],
    ),
    "jpeg_iptc": Technique(
        key="jpeg_iptc",
        family="image",
        description="Write IPTC metadata to a JPEG.",
        backend_menu=["pkg:pyexiv2", "bin:exiftool"],
    ),
    "icc_profile": Technique(
        key="icc_profile",
        family="image",
        description="Write or manipulate an ICC color profile chunk.",
        backend_menu=["pkg:pyexiv2", "bin:exiftool"],
    ),
    # ---- image: container smuggling ----
    "container_apng": Technique(
        key="container_apng",
        family="image",
        description="APNG multi-frame container smuggling.",
        backend_menu=["pkg:apng", "pure_python"],
    ),
    "container_gif": Technique(
        key="container_gif",
        family="image",
        description="GIF comment/application-extension smuggling.",
        backend_menu=["pure_python"],
    ),
    "container_pdf_multipage": Technique(
        key="container_pdf_multipage",
        family="image",
        description="Multi-page PDF authoring with payload smuggling.",
        backend_menu=["pkg:pikepdf", "pkg:pypdf", "bin:qpdf"],
    ),
    "polyglot_png_zip": Technique(
        key="polyglot_png_zip",
        family="image",
        description="PNG that is also a valid ZIP (concatenation polyglot).",
        backend_menu=["pure_python"],
    ),
    "polyglot_zip_png": Technique(
        key="polyglot_zip_png",
        family="image",
        description="ZIP that is also a valid PNG.",
        backend_menu=["pure_python"],
    ),
    # ---- audio ----
    "audio_lsb_wav": Technique(
        key="audio_lsb_wav",
        family="audio",
        description="LSB in PCM WAV samples.",
        backend_menu=["pure_python"],
    ),
    "container_multitrack_audio": Technique(
        key="container_multitrack_audio",
        family="audio",
        description="Multi-track audio container smuggling. Requires ffmpeg.",
        backend_menu=["bin:ffmpeg"],
    ),
}


# ---------------------------------------------------------------------------
# Backend resolution
# ---------------------------------------------------------------------------

def _menu_entry_available(entry: str) -> bool:
    if entry == "pure_python":
        return True
    kind, _, name = entry.partition(":")
    if kind not in ("pkg", "bin"):
        return False
    try:
        return get(name).status == "available"
    except KeyError:
        return False


def _menu_entry_status(entry: str) -> Optional[Capability]:
    if entry == "pure_python":
        return None
    _, _, name = entry.partition(":")
    try:
        return get(name)
    except KeyError:
        return None


def resolve_technique(key: str) -> dict:
    """Look up one technique's current status.

    Returns a JSON-shaped dict with keys:

    - ``status``: ``"available"`` if any backend in the menu is usable,
      else ``"missing"``.
    - ``backend``: the winning menu entry (or ``None`` if none matched).
    - ``promotable_to``: menu entries above the winner that would take
      over if installed.
    - ``requires_any_of``: for ``missing`` techniques, the human names of
      the menu entries and their install hints.
    """
    tech = TECHNIQUES.get(key)
    if tech is None:
        raise KeyError(f"no such technique: {key!r}")

    chosen: Optional[str] = None
    promotable_to: List[str] = []
    requires_any_of: List[dict] = []

    for entry in tech.backend_menu:
        if _menu_entry_available(entry):
            if chosen is None:
                chosen = entry
            else:
                # Earlier menu entries not yet chosen are promotions — but
                # by the time we hit a later winner, the earlier ones
                # weren't available. This branch is unreachable.
                pass
        else:
            cap = _menu_entry_status(entry)
            if cap is not None:
                requires_any_of.append({
                    "name": cap.name,
                    "kind": cap.kind,
                    "install_hint": cap.install_hint,
                })
            # When something above the winner is missing, it becomes a
            # promotion path — but only if we haven't chosen yet.
            if chosen is None:
                promotable_to.append(entry)

    if chosen is not None:
        # Anything ordered *earlier* than the winner and still missing is
        # a promotion path.
        winner_index = tech.backend_menu.index(chosen)
        promotable_to = [
            e for e in tech.backend_menu[:winner_index]
            if not _menu_entry_available(e)
        ]
        return {
            "status": "available",
            "backend": chosen,
            "promotable_to": promotable_to,
        }
    return {
        "status": "missing",
        "backend": None,
        "requires_any_of": requires_any_of,
    }


def techniques_supported() -> Dict[str, dict]:
    """Resolve every registered technique. Order is insertion order."""
    return {key: resolve_technique(key) for key in TECHNIQUES}


# ---------------------------------------------------------------------------
# Snapshot: what the MCP tool + persona consume
# ---------------------------------------------------------------------------

def snapshot() -> dict:
    """Full capability snapshot: packages, binaries, techniques, and a
    one-line summary suitable for the persona's session cache.
    """
    caps = probe_all()

    python_packages: Dict[str, dict] = {}
    binaries: Dict[str, dict] = {}
    for cap in caps.values():
        entry = cap.to_dict()
        entry.pop("name", None)
        entry.pop("kind", None)
        (python_packages if cap.kind == "python" else binaries)[cap.name] = entry

    techniques = techniques_supported()
    total = len(techniques)
    available = sum(1 for t in techniques.values() if t["status"] == "available")
    summary = (
        f"{available}/{total} techniques available; "
        f"{total - available} need optional installs."
    )

    return {
        "python_packages": python_packages,
        "binaries": binaries,
        "techniques": techniques,
        "summary": summary,
    }


__all__ = [
    "Capability",
    "Technique",
    "TECHNIQUES",
    "clear_cache",
    "get",
    "probe_all",
    "register_probe",
    "resolve_technique",
    "snapshot",
    "techniques_supported",
]
