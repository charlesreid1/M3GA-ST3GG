"""JPEG and PNG metadata writers.

Provides write support for JPEG metadata formats that the toolkit can
currently only read:

* **EXIF** — via ``piexif`` (optional dependency).
* **XMP** — hand-rolled XML writer in APP1 segment.
* **IPTC** — hand-rolled IIM binary record in APP13 segment.
* **ICC** — opaque bytes in APP2 segment.
* **PNG text** — PIL PngInfo fallback (already in img_core, re-exported).

JPEG segment layout
-------------------

All APPn markers sit between SOI (FFD8) and the first SOF (FFC0-FFCF)
or SOS (FFDA).  New segments are inserted immediately after any existing
APP0 (JFIF) marker, preserving APP0's position as the first marker after
SOI per the JFIF spec.
"""

from __future__ import annotations

import io
import struct
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from PIL import Image

# ---------------------------------------------------------------------------
# JPEG segment helpers
# ---------------------------------------------------------------------------

_SOI = b"\xff\xd8"
_EOI = b"\xff\xd9"
_SOS_MARKERS = {0xDA}  # SOS
_SOF_MARKERS = {
    0xC0, 0xC1, 0xC2, 0xC3,
    0xC5, 0xC6, 0xC7,
    0xC9, 0xCA, 0xCB,
    0xCD, 0xCE, 0xCF,
}
# Any marker that comes before SOS.
_PRE_SCAN_MARKERS = _SOF_MARKERS | {
    0xE0,  # APP0 / JFIF
    0xE1,  # APP1 / EXIF or XMP
    0xE2,  # APP2 / ICC
    0xED,  # APP13 / IPTC
    0xEE,  # APP14 / Adobe
    0xDB,  # DQT
    0xC4,  # DHT
    0xDD,  # DRI
    0xFE,  # COM
}


def _find_insertion_point(jpeg_bytes: bytes) -> int:
    """Return the byte offset where new APPn markers should be inserted.

    Inserts after the last pre-SOS marker (APP0..APPn, DQT, DHT, etc.),
    but before the SOS marker (FFDA).  If the JPEG has no pre-SOS
    markers between SOI and SOS, inserts right after SOI.
    """
    n = len(jpeg_bytes)
    if n < 4 or jpeg_bytes[:2] != _SOI:
        raise ValueError("not a valid JPEG (missing SOI)")

    last_app = 2  # default: right after SOI
    i = 2
    while i < n - 1:
        if jpeg_bytes[i] != 0xFF:
            break
        marker = jpeg_bytes[i + 1]
        if marker == 0xFF:
            i += 1
            continue
        # Standalone markers.
        if marker in (0x00, 0x01, 0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5,
                      0xD6, 0xD7, 0xD8, 0xD9):
            i += 2
            continue
        # SOS — stop here, insert before scan data.
        if marker == 0xDA:
            break
        # Length-prefixed segment.
        if i + 4 > n:
            break
        seg_len = (jpeg_bytes[i + 2] << 8) | jpeg_bytes[i + 3]
        seg_end = i + 2 + seg_len
        if seg_end > n:
            break
        last_app = seg_end
        i = seg_end
    return last_app


def _make_app_segment(marker: int, payload: bytes) -> bytes:
    """Build an APPn segment: FF<marker> <2-byte BE length> <payload>."""
    # Length includes the 2 length bytes but NOT the FF<marker> prefix.
    length = 2 + len(payload)
    return struct.pack(">BBH", 0xFF, marker, length) + payload


# ---------------------------------------------------------------------------
# EXIF (via piexif)
# ---------------------------------------------------------------------------

def inject_exif(jpeg_bytes: bytes, exif_dict: dict) -> bytes:
    """Embed EXIF metadata into a JPEG via ``piexif``.

    *exif_dict* uses the piexif dictionary format (keys like ``"0th"``,
    ``"Exif"``, ``"GPS"``, ``"1st"``).  Returns the modified JPEG as
    ``bytes``.

    Requires ``piexif`` to be installed (``pip install piexif``).
    """
    try:
        import piexif
    except ImportError as exc:
        raise ImportError(
            "EXIF write requires piexif. Install with `pip install piexif`."
        ) from exc

    exif_bytes = piexif.dump(exif_dict)
    return _insert_app_segment(jpeg_bytes, 0xE1, exif_bytes)


def read_exif(jpeg_bytes: bytes) -> Optional[dict]:
    """Read EXIF data from a JPEG as a piexif-style dict, or *None*."""
    try:
        import piexif
    except ImportError:
        return None
    try:
        return piexif.load(jpeg_bytes)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# XMP (hand-rolled XML in APP1)
# ---------------------------------------------------------------------------


def inject_xmp(jpeg_bytes: bytes, xmp_xml: str) -> bytes:
    """Embed an XMP XML string into a JPEG's APP1 segment.

    The XMP packet must be a valid XML string (it will be wrapped in the
    XMP namespace packet header if not already).  Returns the modified
    JPEG as ``bytes``.
    """
    # XMP APP1 marker has a null-terminated namespace URI prefix.
    ns = b"http://ns.adobe.com/xap/1.0/\x00"
    payload = ns + xmp_xml.encode("utf-8")
    return _insert_app_segment(jpeg_bytes, 0xE1, payload)


def _insert_app_segment(jpeg_bytes: bytes, marker: int, data: bytes) -> bytes:
    """Insert or replace an APPn segment in a JPEG.

    If a segment with the given *marker* already exists, it is replaced.
    Otherwise the new segment is inserted at the standard insertion point.
    """
    # Check if this APPn marker already exists — if so, replace it.
    removed = _remove_app_segment(jpeg_bytes, marker)
    # Insert new segment after SOI / pre-SOS markers.
    ins = _find_insertion_point(removed)
    return removed[:ins] + _make_app_segment(marker, data) + removed[ins:]


def _remove_app_segment(jpeg_bytes: bytes, marker: int) -> bytes:
    """Return JPEG bytes with the first occurrence of APPn *marker* stripped."""
    n = len(jpeg_bytes)
    if n < 4 or jpeg_bytes[:2] != _SOI:
        return jpeg_bytes

    i = 2
    while i < n - 1:
        if jpeg_bytes[i] != 0xFF:
            break
        m = jpeg_bytes[i + 1]
        if m == 0xFF:
            i += 1
            continue
        if m in (0x00, 0x01) or (0xD0 <= m <= 0xD9):
            i += 2
            continue
        if i + 4 > n:
            break
        seg_len = (jpeg_bytes[i + 2] << 8) | jpeg_bytes[i + 3]
        seg_end = i + 2 + seg_len
        if seg_end > n:
            break
        if m == marker:
            return jpeg_bytes[:i] + jpeg_bytes[seg_end:]
        i = seg_end
    return jpeg_bytes


# ---------------------------------------------------------------------------
# IPTC (hand-rolled IIM in APP13)
# ---------------------------------------------------------------------------

# IPTC/IIM record types we support writing.
_IPTC_RECORD_TAGS = {
    # Record 2: Application records
    "ObjectName": (2, 5),
    "Caption/Abstract": (2, 120),
    "Caption": (2, 120),  # alias
    "Keywords": (2, 25),
    "CopyrightNotice": (2, 116),
    "By-line": (2, 80),
    "By-lineTitle": (2, 85),
    "Credit": (2, 110),
    "Source": (2, 115),
    "Headline": (2, 105),
    "SpecialInstructions": (2, 40),
    "City": (2, 90),
    "Province/State": (2, 95),
    "Country/PrimaryLocationName": (2, 101),
    "Country": (2, 101),  # alias
    "OriginalTransmissionReference": (2, 103),
}

# IPTC/IIM envelope: "Photoshop 3.0\0" prefix + IIM records.
_IPTC_SIG = b"Photoshop 3.0\x00"


def inject_iptc(jpeg_bytes: bytes, iptc_tags: dict[str, str]) -> bytes:
    """Embed IPTC/IIM tags into a JPEG's APP13 segment.

    *iptc_tags* is a dict mapping IPTC tag names (e.g. ``"Keywords"``,
    ``"CopyrightNotice"``) to string values.  Returns the modified JPEG
    as ``bytes``.
    """
    records = bytearray()
    for tag_name, value in iptc_tags.items():
        tag_info = _IPTC_RECORD_TAGS.get(tag_name)
        if tag_info is None:
            raise ValueError(
                f"unknown IPTC tag: {tag_name!r}. "
                f"Known tags: {', '.join(sorted(_IPTC_RECORD_TAGS))}"
            )
        record_num, dataset_num = tag_info
        val_bytes = value.encode("utf-8", errors="replace")
        # IIM record structure:
        #   1c xx  (record number, dataset number)
        #   2 bytes big-endian length
        #   data
        records.append(0x1C)
        records.append(record_num)
        records.append(dataset_num)
        records.extend(struct.pack(">H", len(val_bytes)))
        records.extend(val_bytes)

    payload = _IPTC_SIG + bytes(records)
    return _insert_app_segment(jpeg_bytes, 0xED, payload)


# ---------------------------------------------------------------------------
# ICC profile (hand-rolled APP2)
# ---------------------------------------------------------------------------


def inject_icc(jpeg_bytes: bytes, icc_profile: bytes) -> bytes:
    """Embed an ICC color profile into a JPEG's APP2 segment.

    *icc_profile* is the raw ICC profile bytes (e.g. read from a .icc
    file).  Returns the modified JPEG as ``bytes``.
    """
    # ICC in APP2: sequence number (1 byte) + total chunks (1 byte) + data.
    # For a single-chunk profile: seq=1, total=1.
    header = bytes([1, 1])
    return _insert_app_segment(jpeg_bytes, 0xE2, header + icc_profile)


# ---------------------------------------------------------------------------
# PNG metadata (PIL PngInfo)
# ---------------------------------------------------------------------------


def inject_png_text(png_bytes: bytes, metadata: dict[str, str]) -> bytes:
    """Inject PNG tEXt chunks via PIL PngInfo.

    *metadata* is a dict mapping keyword → value strings.  Returns the
    modified PNG as ``bytes``.
    """
    img = Image.open(io.BytesIO(png_bytes))
    # We delegate to img_core's existing PIL metadata injection.
    from m3gast3gg.core.img import inject_metadata_pil as _pil_inject

    _, out = _pil_inject(img, metadata)
    return out


# ---------------------------------------------------------------------------
# Convenience: write any metadata format
# ---------------------------------------------------------------------------

_METADATA_FORMATS = {"exif", "xmp", "iptc", "icc", "png_text"}


def _to_bytes(data: str | bytes) -> bytes:
    """Normalise *data* to ``bytes`` — accepts a file path or raw bytes."""
    if isinstance(data, str):
        return Path(data).read_bytes()
    if isinstance(data, bytes):
        return data
    raise TypeError(f"expected str (file path) or bytes, got {type(data).__name__}")


def write_metadata(
    data: str | bytes,
    fmt: str,
    content: str | bytes | dict,
) -> bytes:
    """Write metadata to a JPEG or PNG.

    Parameters
    ----------
    data
        File path (``str``) or JPEG/PNG file ``bytes``.
    fmt
        One of ``"exif"``, ``"xmp"``, ``"iptc"``, ``"icc"``, ``"png_text"``.
    content
        Format-dependent:
        - ``"exif"``: piexif-style dict.
        - ``"xmp"``: XML string.
        - ``"iptc"``: dict of tag name → value.
        - ``"icc"``: raw ICC profile bytes.
        - ``"png_text"``: dict of keyword → text.

    Returns
    -------
    bytes
        The modified file.
    """
    data = _to_bytes(data)
    if fmt not in _METADATA_FORMATS:
        raise ValueError(
            f"unknown metadata format {fmt!r}. "
            f"Use one of: {', '.join(sorted(_METADATA_FORMATS))}"
        )
    if fmt == "exif":
        if not isinstance(content, dict):
            raise TypeError("exif requires a dict of piexif tags")
        return inject_exif(data, content)
    if fmt == "xmp":
        if not isinstance(content, str):
            raise TypeError("xmp requires an XML string")
        return inject_xmp(data, content)
    if fmt == "iptc":
        if not isinstance(content, dict):
            raise TypeError("iptc requires a dict of tag name → value")
        return inject_iptc(data, content)
    if fmt == "icc":
        if not isinstance(content, (bytes, bytearray)):
            raise TypeError("icc requires raw profile bytes")
        return inject_icc(data, bytes(content))
    if fmt == "png_text":
        if not isinstance(content, dict):
            raise TypeError("png_text requires a dict of keyword → text")
        return inject_png_text(data, content)
    raise AssertionError("unreachable")
