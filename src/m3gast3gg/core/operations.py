"""Shared operation layer for steg CLI and MCP tools.

Each function takes plain Python types (paths as strings, payloads as bytes),
handles file I/O, validation, capacity checks, encryption, and error-wrapping,
and returns a dataclass. Callers format the result for their output channel
(Rich panels, JSON, MCP TextContent, etc.).

Design principles:
- Functions own file I/O — callers pass string paths, not open handles.
- Functions own validation — callers don't duplicate path-exists / capacity checks.
- Functions raise OperationError on user-facing failures (bad paths, payload too
  large, etc.). Callers catch and format for their protocol.
- Functions return dataclasses, never framework objects (no Rich markup, no MCP
  types, no argparse.Namespace).
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image

import m3gast3gg.core.img as img_core
import m3gast3gg.core.text as text_core


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class OperationError(Exception):
    """User-facing error from an operation (bad path, payload too large, etc.)."""


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class EncodeResult:
    """Returned by all encode operations."""

    output_path: str
    output_bytes: int
    payload_bytes: int
    capacity_human: str = ""
    capacity_bytes: int = 0
    encrypted: bool = False
    config: dict[str, Any] = field(default_factory=dict)
    carrier_dims: tuple[int, int] | None = None
    carrier_mode: str = ""


@dataclass
class DecodeResult:
    """Returned by all decode operations."""

    data: bytes
    payload_bytes: int
    auto_detected: bool = False
    config: dict[str, Any] | None = None
    text: str | None = None  # decoded UTF-8, if valid


@dataclass
class CapacityResult:
    """Returned by all capacity operations."""

    usable_bytes: int
    human: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalyzeResult:
    """Returned by image analysis operations."""

    dimensions: dict[str, int]
    mode: str
    total_pixels: int
    format_name: str
    channels: dict[str, Any]
    capacity_by_config: dict[str, str]
    max_chi_sq_indicator: float
    verdict: str


@dataclass
class MetadataResult:
    """Returned by metadata read operations."""

    pil_info: dict[str, Any]
    png_text_chunks: dict[str, str] | None = None
    mode: str = ""
    format_name: str = ""
    size: list[int] = field(default_factory=list)


@dataclass
class ChunkWriteResult:
    """Returned by chunk/metadata inject operations."""

    output_path: str
    input_bytes: int
    output_bytes: int
    chunk_type: str = ""
    keyword: str = ""
    value_bytes: int = 0


@dataclass
class ChunksResult:
    """Returned by PNG chunk read operations."""

    chunk_count: int
    chunks: list[dict[str, Any]]
    text_chunks: dict[str, str]


@dataclass
class DetectResult:
    """Returned by encoding-detection operations."""

    detected: bool
    config: dict[str, Any] | None = None
    payload_length: int | None = None
    original_length: int | None = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB


def _read_required(path: str) -> tuple[bytes, dict[str, Any]]:
    """Read a file that must exist. Returns (data, meta). Raises OperationError."""
    p = Path(path)
    if not p.exists():
        raise OperationError(f"file not found: {path}")
    if not p.is_file():
        raise OperationError(f"not a regular file: {path}")
    size = p.stat().st_size
    if size > _MAX_FILE_SIZE:
        raise OperationError(f"file too large: {size} bytes (max {_MAX_FILE_SIZE})")
    return p.read_bytes(), {"name": p.name, "path": str(p.resolve()), "size": size}


def _resolve_payload(
    text: str | None = None,
    file_path: str | None = None,
    payload_hex: str | None = None,
) -> bytes:
    """Resolve a payload from one of three sources. Raises OperationError."""
    sources = sum(1 for x in (text, file_path, payload_hex) if x is not None)
    if sources == 0:
        raise OperationError("no payload provided (need text, file_path, or payload_hex)")
    if sources > 1:
        raise OperationError("provide exactly one of text, file_path, or payload_hex")

    if payload_hex is not None:
        try:
            return bytes.fromhex(payload_hex)
        except (ValueError, TypeError) as exc:
            raise OperationError(f"invalid payload_hex: {exc}") from exc

    if file_path is not None:
        p = Path(file_path)
        if not p.exists():
            raise OperationError(f"payload file not found: {file_path}")
        return p.read_bytes()

    # text
    return text.encode("utf-8")  # type: ignore[union-attr]


def _open_image(data: bytes) -> Image.Image:
    """Open an image from bytes. Raises OperationError on failure."""
    try:
        return Image.open(io.BytesIO(data))
    except Exception as exc:
        raise OperationError(f"failed to open image: {exc}") from exc


def _write_output(data: bytes, output_path: str | None, default_path: str) -> str:
    """Write output bytes, return the path written."""
    out = output_path or default_path
    Path(out).write_bytes(data)
    return out


def _try_decode_utf8(data: bytes) -> str | None:
    """Return UTF-8 decoded text, or None if binary."""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


# ---------------------------------------------------------------------------
# LSB image operations
# ---------------------------------------------------------------------------


def op_lsb_encode(
    *,
    input_path: str,
    text: str | None = None,
    file_path: str | None = None,
    payload_hex: str | None = None,
    payload: bytes | None = None,
    output_path: str | None = None,
    channels: str = "RGB",
    bits: int = 1,
    strategy: str = "interleaved",
    seed: int | None = None,
    compress: bool = True,
    password: str | None = None,
) -> EncodeResult:
    """Encode a payload into an image via LSB steganography.

    Payload is taken from exactly one of *text*, *file_path*, *payload_hex*,
    or the raw *payload* bytes arg.

    If *password* is provided the payload is AES-256-GCM encrypted before
    embedding (requires the ``crypto`` extra).
    """
    # Resolve payload
    if payload is not None:
        payload_bytes = payload
    else:
        payload_bytes = _resolve_payload(text=text, file_path=file_path, payload_hex=payload_hex)

    # Read carrier
    data, meta = _read_required(input_path)
    img = _open_image(data)

    # Config
    config = img_core.create_config(
        channels=channels,
        bits=bits,
        compress=compress,
        strategy=strategy,
        seed=seed,
    )

    # Capacity check
    cap = img_core.calculate_capacity(img, config)
    if len(payload_bytes) > cap["usable_bytes"]:
        raise OperationError(
            f"payload too large: {len(payload_bytes):,} bytes > "
            f"{cap['usable_bytes']:,} available"
        )

    # Encrypt
    encrypted = False
    if password:
        try:
            from m3gast3gg.core.crypto import encrypt as _encrypt
        except ImportError as exc:
            raise OperationError(
                "encryption requires the 'crypto' extra: pip install stegg[crypto]"
            ) from exc
        payload_bytes = _encrypt(payload_bytes, password)
        encrypted = True

    # Encode
    try:
        result_img = img_core.encode(img, payload_bytes, config)
    except Exception as exc:
        raise OperationError(f"LSB encode failed: {exc}") from exc

    # Write output
    default_out = str(Path(input_path).with_name(f"steg_{Path(input_path).stem}.png"))
    out_path = _write_output(_pil_to_png_bytes(result_img), output_path, default_out)

    return EncodeResult(
        output_path=out_path,
        output_bytes=Path(out_path).stat().st_size,
        payload_bytes=len(payload_bytes),
        capacity_human=str(cap["human"]),
        capacity_bytes=cap["usable_bytes"],
        encrypted=encrypted,
        config={
            "method": "LSB",
            "channels": channels,
            "bits_per_channel": bits,
            "strategy": strategy,
            "compress": compress,
        },
        carrier_dims=(img.width, img.height),
        carrier_mode=img.mode,
    )


def op_lsb_decode(
    *,
    input_path: str,
    auto_detect: bool = True,
    channels: str = "RGB",
    bits: int = 1,
    strategy: str = "interleaved",
    seed: int | None = None,
    password: str | None = None,
    verify_checksum: bool = True,
) -> DecodeResult:
    """Decode a payload from an LSB-encoded image.

    With *auto_detect* (default), reads the ST3GG v3 header to determine the
    encoding config. Falls back to the explicit *channels*/*bits*/*strategy*
    when no header is found.
    """
    data, meta = _read_required(input_path)
    img = _open_image(data)

    config = None
    detected = False

    if auto_detect:
        detection = img_core.detect_encoding(img)
        if detection:
            detected = True
        else:
            config = img_core.create_config(
                channels=channels, bits=bits, strategy=strategy, seed=seed
            )
    else:
        config = img_core.create_config(
            channels=channels, bits=bits, strategy=strategy, seed=seed
        )

    # Decode
    try:
        payload = img_core.decode(img, config, verify_checksum=verify_checksum)
    except Exception as exc:
        raise OperationError(f"LSB decode failed: {exc}") from exc

    # Decrypt
    if password and payload:
        try:
            from m3gast3gg.core.crypto import decrypt as _decrypt
        except ImportError as exc:
            raise OperationError(
                "decryption requires the 'crypto' extra: pip install stegg[crypto]"
            ) from exc
        try:
            payload = _decrypt(payload, password)
        except Exception as exc:
            raise OperationError(f"decryption failed: {exc}") from exc

    return DecodeResult(
        data=payload,
        payload_bytes=len(payload),
        auto_detected=detected,
        config=None,
        text=_try_decode_utf8(payload),
    )


def op_lsb_capacity(
    *,
    input_path: str,
    channels: str = "RGB",
    bits: int = 1,
    strategy: str = "interleaved",
) -> CapacityResult:
    """Report LSB payload capacity for an image."""
    data, meta = _read_required(input_path)
    img = _open_image(data)
    config = img_core.create_config(channels=channels, bits=bits, strategy=strategy)
    cap = img_core.calculate_capacity(img, config)
    return CapacityResult(
        usable_bytes=cap["usable_bytes"],
        human=str(cap["human"]),
        details={
            "channels": channels,
            "bits_per_channel": bits,
            "strategy": strategy,
            "pixels": img.width * img.height,
            "dimensions": {"width": img.width, "height": img.height},
        },
    )


def op_image_analyze(*, input_path: str) -> AnalyzeResult:
    """Run full statistical analysis on an image."""
    data, meta = _read_required(input_path)
    img = _open_image(data)
    analysis = img_core.analyze_image(img)

    max_indicator = max(
        ch["chi_square_indicator"] for ch in analysis["channels"].values()
    )

    if max_indicator > 0.3:
        verdict = "HIGH PROBABILITY"
    elif max_indicator > 0.1:
        verdict = "Possible"
    else:
        verdict = "No indicators"

    return AnalyzeResult(
        dimensions=analysis["dimensions"],
        mode=analysis["mode"],
        total_pixels=analysis["total_pixels"],
        format_name=str(analysis.get("format", "")),
        channels=analysis["channels"],
        capacity_by_config=analysis["capacity_by_config"],
        max_chi_sq_indicator=max_indicator,
        verdict=verdict,
    )


def op_detect_encoding(*, input_path: str) -> DetectResult:
    """Quick ST3GG v3 header detection check."""
    data, meta = _read_required(input_path)
    img = _open_image(data)
    det = img_core.detect_encoding(img)
    if det:
        return DetectResult(
            detected=True,
            config=det.get("config"),
            payload_length=det.get("payload_length"),
            original_length=det.get("original_length"),
        )
    return DetectResult(detected=False)


# ---------------------------------------------------------------------------
# DCT operations
# ---------------------------------------------------------------------------


def op_dct_encode(
    *,
    input_path: str,
    text: str | None = None,
    file_path: str | None = None,
    payload_hex: str | None = None,
    output_path: str | None = None,
    robustness: str = "medium",
    block_size: int = 8,
) -> EncodeResult:
    """Encode a payload into an image via DCT (frequency-domain) steganography."""
    payload_bytes = _resolve_payload(text=text, file_path=file_path, payload_hex=payload_hex)
    data, meta = _read_required(input_path)
    img = _open_image(data)

    cap = img_core.dct_capacity(img, block_size=block_size)
    if len(payload_bytes) > cap["usable_bytes"]:
        raise OperationError(
            f"payload too large: {len(payload_bytes):,} bytes > "
            f"{cap['usable_bytes']:,} available"
        )

    try:
        result_img = img_core.dct_encode(img, payload_bytes, robustness=robustness, block_size=block_size)
    except Exception as exc:
        raise OperationError(f"DCT encode failed: {exc}") from exc

    default_out = str(Path(input_path).with_name(f"steg_dct_{Path(input_path).stem}.png"))
    out_path = _write_output(_pil_to_png_bytes(result_img), output_path, default_out)

    return EncodeResult(
        output_path=out_path,
        output_bytes=Path(out_path).stat().st_size,
        payload_bytes=len(payload_bytes),
        capacity_human=str(cap["human"]),
        capacity_bytes=cap["usable_bytes"],
        config={
            "method": "DCT",
            "robustness": robustness,
            "block_size": block_size,
            "strength": img_core.DCT_STRENGTHS.get(robustness, 50),
        },
        carrier_dims=(img.width, img.height),
        carrier_mode=img.mode,
    )


def op_dct_decode(
    *,
    input_path: str,
    block_size: int = 8,
) -> DecodeResult:
    """Decode a DCT-encoded payload from an image."""
    data, meta = _read_required(input_path)
    img = _open_image(data)

    try:
        payload = img_core.dct_decode(img, block_size=block_size)
    except Exception as exc:
        raise OperationError(f"DCT decode failed: {exc}") from exc

    return DecodeResult(
        data=payload,
        payload_bytes=len(payload),
        text=_try_decode_utf8(payload),
    )


def op_dct_capacity(
    *,
    input_path: str,
    block_size: int = 8,
) -> CapacityResult:
    """Report DCT payload capacity for an image."""
    data, meta = _read_required(input_path)
    img = _open_image(data)
    cap = img_core.dct_capacity(img, block_size=block_size)
    return CapacityResult(
        usable_bytes=cap["usable_bytes"],
        human=str(cap["human"]),
        details={"block_size": block_size, **{k: v for k, v in cap.items() if k not in ("usable_bytes", "human")}},
    )


# ---------------------------------------------------------------------------
# F5 operations (JPEG DCT coefficient steganography)
# ---------------------------------------------------------------------------


def op_f5_encode(
    *,
    input_path: str,
    text: str | None = None,
    file_path: str | None = None,
    payload_hex: str | None = None,
    output_path: str | None = None,
    password: str = "",
) -> EncodeResult:
    """Encode a payload into a JPEG via the F5 algorithm (Westfeld 2001)."""
    payload_bytes = _resolve_payload(text=text, file_path=file_path, payload_hex=payload_hex)
    jpeg_bytes, meta = _read_required(input_path)

    # Validate JPEG
    if jpeg_bytes[:3] != b"\xff\xd8\xff":
        raise OperationError(f"not a JPEG file: {input_path}")

    cap = img_core.f5_capacity_bytes(jpeg_bytes)
    if len(payload_bytes) > cap:
        raise OperationError(
            f"payload too large: {len(payload_bytes):,} bytes > {cap:,} available"
        )

    try:
        encoded = img_core.f5_encode(jpeg_bytes, payload_bytes, password=password)
    except Exception as exc:
        raise OperationError(f"F5 encode failed: {exc}") from exc

    default_out = str(Path(input_path).with_name(f"steg_f5_{Path(input_path).stem}.jpg"))
    out_path = _write_output(encoded, output_path, default_out)

    return EncodeResult(
        output_path=out_path,
        output_bytes=len(encoded),
        payload_bytes=len(payload_bytes),
        capacity_bytes=cap,
        config={"method": "F5"},
    )


def op_f5_decode(
    *,
    input_path: str,
    password: str = "",
) -> DecodeResult:
    """Decode an F5-encoded payload from a JPEG."""
    jpeg_bytes, meta = _read_required(input_path)

    if jpeg_bytes[:3] != b"\xff\xd8\xff":
        raise OperationError(f"not a JPEG file: {input_path}")

    try:
        payload = img_core.f5_decode(jpeg_bytes, password=password)
    except Exception as exc:
        raise OperationError(f"F5 decode failed: {exc}") from exc

    return DecodeResult(
        data=payload,
        payload_bytes=len(payload),
        text=_try_decode_utf8(payload),
    )


def op_f5_capacity(*, input_path: str) -> CapacityResult:
    """Report F5 payload capacity for a JPEG."""
    jpeg_bytes, meta = _read_required(input_path)

    if jpeg_bytes[:3] != b"\xff\xd8\xff":
        raise OperationError(f"not a JPEG file: {input_path}")

    cap = img_core.f5_capacity(jpeg_bytes)
    return CapacityResult(
        usable_bytes=img_core.f5_capacity_bytes(jpeg_bytes),
        human=f"{img_core.f5_capacity_bytes(jpeg_bytes):,} bytes",
        details=cap,
    )


# ---------------------------------------------------------------------------
# JSteg operations
# ---------------------------------------------------------------------------


def op_jsteg_encode(
    *,
    input_path: str,
    text: str | None = None,
    file_path: str | None = None,
    payload_hex: str | None = None,
    output_path: str | None = None,
) -> EncodeResult:
    """Encode a payload into a JPEG via JSteg."""
    payload_bytes = _resolve_payload(text=text, file_path=file_path, payload_hex=payload_hex)
    jpeg_bytes, meta = _read_required(input_path)

    if jpeg_bytes[:3] != b"\xff\xd8\xff":
        raise OperationError(f"not a JPEG file: {input_path}")

    cap = img_core.jsteg_capacity_bytes(jpeg_bytes)
    if len(payload_bytes) > cap:
        raise OperationError(
            f"payload too large: {len(payload_bytes):,} bytes > {cap:,} available"
        )

    try:
        encoded = img_core.jsteg_encode(jpeg_bytes, payload_bytes)
    except Exception as exc:
        raise OperationError(f"JSteg encode failed: {exc}") from exc

    default_out = str(Path(input_path).with_name(f"steg_jsteg_{Path(input_path).stem}.jpg"))
    out_path = _write_output(encoded, output_path, default_out)

    return EncodeResult(
        output_path=out_path,
        output_bytes=len(encoded),
        payload_bytes=len(payload_bytes),
        capacity_bytes=cap,
        config={"method": "JSteg"},
    )


def op_jsteg_decode(*, input_path: str) -> DecodeResult:
    """Decode a JSteg-encoded payload from a JPEG."""
    jpeg_bytes, meta = _read_required(input_path)

    if jpeg_bytes[:3] != b"\xff\xd8\xff":
        raise OperationError(f"not a JPEG file: {input_path}")

    try:
        payload = img_core.jsteg_decode(jpeg_bytes)
    except Exception as exc:
        raise OperationError(f"JSteg decode failed: {exc}") from exc

    return DecodeResult(
        data=payload,
        payload_bytes=len(payload),
        text=_try_decode_utf8(payload),
    )


def op_jsteg_capacity(*, input_path: str) -> CapacityResult:
    """Report JSteg payload capacity for a JPEG."""
    jpeg_bytes, meta = _read_required(input_path)

    if jpeg_bytes[:3] != b"\xff\xd8\xff":
        raise OperationError(f"not a JPEG file: {input_path}")

    cap = img_core.jsteg_capacity(jpeg_bytes)
    return CapacityResult(
        usable_bytes=cap.get("capacity_bytes", 0),
        human=str(cap.get("human", "")),
        details=cap,
    )


# ---------------------------------------------------------------------------
# Metadata / PNG chunk operations
# ---------------------------------------------------------------------------


def op_read_metadata(*, input_path: str) -> MetadataResult:
    """Read image metadata: PIL info, PNG text chunks, dimensions."""
    data, meta = _read_required(input_path)
    img = _open_image(data)

    pil_info = {k: str(v)[:500] for k, v in (img.info or {}).items()}
    png_text: dict[str, str] | None = None

    try:
        chunks = img_core.extract_text_chunks(data)
        if chunks:
            png_text = chunks
    except Exception:
        pass

    return MetadataResult(
        pil_info=pil_info,
        png_text_chunks=png_text,
        mode=img.mode,
        format_name=img.format or "",
        size=list(img.size),
    )


def op_read_png_chunks(*, input_path: str) -> ChunksResult:
    """Full PNG chunk dump."""
    data, meta = _read_required(input_path)
    chunks = img_core.read_png_chunks(data)
    text_chunks = img_core.extract_text_chunks(data)

    summary = []
    for c in chunks:
        entry: dict[str, Any] = {
            "type": c.get("type"),
            "length": c.get("length"),
            "offset": c.get("offset"),
        }
        raw = c.get("data")
        if isinstance(raw, (bytes, bytearray)):
            if c.get("type") in {"tEXt", "iTXt", "zTXt"}:
                try:
                    entry["text"] = raw.decode("utf-8", errors="replace")[:500]
                except Exception:
                    entry["hex_head"] = raw[:32].hex()
            else:
                entry["hex_head"] = raw[:32].hex()
        elif raw is not None:
            entry["value"] = str(raw)[:500]
        summary.append(entry)

    return ChunksResult(
        chunk_count=len(summary),
        chunks=summary,
        text_chunks=text_chunks or {},
    )


def op_inject_chunk(
    *,
    input_path: str,
    output_path: str,
    chunk_type: str = "tEXt",
    keyword: str = "Comment",
    text: str = "",
    compressed: bool = False,
) -> ChunkWriteResult:
    """Inject a PNG text or private chunk. Writes modified PNG to *output_path*."""
    data, meta = _read_required(input_path)

    ct = chunk_type
    if ct == "iTXt":
        modified = img_core.inject_itxt_chunk(data, keyword, text)
    elif len(ct) == 4 and ct not in ("tEXt", "zTXt", "iTXt"):
        modified = img_core.inject_private_chunk(data, ct, text.encode("utf-8"))
    else:
        modified = img_core.inject_text_chunk(data, keyword, text, compressed=compressed)

    _write_output(modified, output_path, output_path)
    return ChunkWriteResult(
        output_path=output_path,
        input_bytes=len(data),
        output_bytes=len(modified),
        chunk_type=ct,
        keyword=keyword,
        value_bytes=len(text),
    )


def op_inject_metadata_pil(
    *,
    input_path: str,
    output_path: str,
    metadata: dict[str, str],
) -> ChunkWriteResult:
    """Inject multiple tEXt key/value pairs via PIL PngInfo."""
    data, meta = _read_required(input_path)
    img = _open_image(data)
    _, png_bytes = img_core.inject_metadata_pil(img, metadata)
    _write_output(png_bytes, output_path, output_path)

    return ChunkWriteResult(
        output_path=output_path,
        input_bytes=len(data),
        output_bytes=len(png_bytes),
        chunk_type="tEXt(bulk)",
        keyword=", ".join(sorted(metadata.keys())),
        value_bytes=sum(len(v) for v in metadata.values()),
    )


# ---------------------------------------------------------------------------
# Text steg operations
# ---------------------------------------------------------------------------


def op_text_encode(
    *,
    method: str,
    secret: str,
    cover_path: str | None = None,
    cover_text: str | None = None,
    output_path: str | None = None,
) -> dict[str, Any]:
    """Hide a secret string in cover text via a text-steg method.

    Returns a dict because the return shape varies (may include inline stego
    or output path, but not both).
    """
    if method not in text_core.METHODS:
        raise OperationError(
            f"unknown method '{method}'. Try one of: {', '.join(sorted(text_core.METHODS))}"
        )

    # Resolve cover
    if cover_text is not None:
        cover = cover_text
    elif cover_path is not None:
        cover = Path(cover_path).read_text(encoding="utf-8")
    else:
        raise OperationError("provide cover_text or cover_path")

    try:
        stego = text_core.encode(cover, secret, method)
    except text_core.TextStegCapacityError as exc:
        raise OperationError(str(exc)) from exc

    result: dict[str, Any] = {
        "method": method,
        "cover_chars": len(cover),
        "stego_chars": len(stego),
        "stego_bytes_utf8": len(stego.encode("utf-8")),
        "payload_bytes": len(secret.encode("utf-8")),
    }

    if output_path:
        Path(output_path).write_text(stego, encoding="utf-8")
        result["output_path"] = str(Path(output_path).resolve())
    else:
        result["stego"] = stego

    return result


def op_text_decode(
    *,
    method: str,
    stego_path: str | None = None,
    stego_text: str | None = None,
) -> str:
    """Recover a hidden secret from a stego text."""
    if method not in text_core.METHODS:
        raise OperationError(
            f"unknown method '{method}'. Try one of: {', '.join(sorted(text_core.METHODS))}"
        )

    if stego_text is not None:
        stego = stego_text
    elif stego_path is not None:
        stego = Path(stego_path).read_text(encoding="utf-8")
    else:
        raise OperationError("provide stego_text or stego_path")

    return text_core.decode(stego, method)


def op_text_capacity(
    *,
    method: str,
    cover_path: str | None = None,
    cover_text: str | None = None,
) -> dict[str, Any]:
    """Report how many bytes a cover can carry under a text-steg method."""
    if method not in text_core.METHODS:
        raise OperationError(
            f"unknown method '{method}'. Try one of: {', '.join(sorted(text_core.METHODS))}"
        )

    if cover_text is not None:
        cover = cover_text
    elif cover_path is not None:
        cover = Path(cover_path).read_text(encoding="utf-8")
    else:
        raise OperationError("provide cover_text or cover_path")

    return text_core.capacity(cover, method)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pil_to_png_bytes(img: Image.Image) -> bytes:
    """Save a PIL image as PNG bytes."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
