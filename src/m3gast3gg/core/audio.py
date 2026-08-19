"""Audio steganography — WAV LSB encode and decode.

Pure-Python using stdlib ``wave`` and ``struct``.  No external dependencies.

All functions accept a file path (``str``) or raw WAV ``bytes``.
"""

from __future__ import annotations

import io
import struct
from pathlib import Path
from typing import Any, Dict


def _to_bytes(data: str | bytes) -> bytes:
    """Normalise *data* to ``bytes`` — accepts a file path or raw bytes."""
    if isinstance(data, str):
        return Path(data).read_bytes()
    if isinstance(data, bytes):
        return data
    raise TypeError(f"expected str (file path) or bytes, got {type(data).__name__}")


def audio_lsb_decode(data: str | bytes) -> Dict[str, Any]:
    """Decode LSB steganography from WAV audio files.

    *data* may be a file path (``str``) or raw WAV ``bytes``.

    Reads 16-bit PCM samples, extracts LSBs, parses a 32-bit big-endian
    length prefix, then extracts that many payload bytes.
    """
    import wave

    try:
        wav_bytes = _to_bytes(data)
        w = wave.open(io.BytesIO(wav_bytes))
        raw = w.readframes(w.getnframes())
        sampwidth = w.getsampwidth()
        w.close()
        if sampwidth != 2:
            return {"found": False, "reason": f"Sample width {sampwidth} not supported"}
        samples = struct.unpack(f"<{len(raw) // 2}h", raw)
        bits = [s & 1 for s in samples]
        if len(bits) < 32:
            return {"found": False}
        length = 0
        for i in range(32):
            length = (length << 1) | bits[i]
        if length <= 0 or length > min(10000, (len(bits) - 32) // 8):
            return {"found": False, "reason": f"Invalid length: {length}"}
        msg = bytearray()
        for i in range(0, length * 8, 8):
            v = 0
            for j in range(8):
                if 32 + i + j < len(bits):
                    v = (v << 1) | bits[32 + i + j]
            msg.append(v)
        decoded = msg.decode("utf-8", errors="replace")
        return {
            "found": True,
            "method": "audio_lsb",
            "length": length,
            "message": decoded[:200],
            "suspicious": True,
            "findings": [f"Audio LSB ({length} bytes): {decoded[:80]}"],
        }
    except Exception as e:
        return {"error": str(e), "found": False}


def audio_lsb_encode(data: str | bytes, payload: str | bytes) -> bytes:
    """Encode LSB steganography into WAV audio files.

    *data* may be a file path (``str``) or raw WAV ``bytes``.
    *payload* may be a ``str`` (UTF-8 encoded) or raw ``bytes``.

    Embeds *payload* into the least significant bits of 16-bit PCM samples
    in the WAV file *data*.  The payload is prefixed with a 32-bit
    big-endian length header (mirroring :func:`audio_lsb_decode`).
    Returns the modified WAV as ``bytes``.

    Raises :class:`ValueError` if *data* is not a valid WAV or has
    unsupported sample width, or if the payload exceeds the carrier
    capacity.
    """
    import wave

    if isinstance(payload, str):
        payload = payload.encode("utf-8")

    wav_bytes = _to_bytes(data)

    try:
        w = wave.open(io.BytesIO(wav_bytes))
    except Exception as e:
        raise ValueError(f"not a valid WAV file: {e}") from e

    sampwidth = w.getsampwidth()
    nchannels = w.getnchannels()
    framerate = w.getframerate()
    nframes = w.getnframes()
    raw = w.readframes(nframes)
    w.close()

    if sampwidth != 2:
        raise ValueError(
            f"sample width {sampwidth} not supported; only 16-bit WAV"
        )

    # Framed payload: 32-bit big-endian length + payload.
    payload_len = len(payload)
    if payload_len > (1 << 31) - 1:
        raise ValueError(f"payload too large: {payload_len} bytes")
    framed = struct.pack(">I", payload_len) + payload

    bits_needed = len(framed) * 8
    samples = list(struct.unpack(f"<{len(raw) // 2}h", raw))
    max_bits = len(samples)
    if bits_needed > max_bits:
        raise ValueError(
            f"payload needs {bits_needed} bits but WAV has only "
            f"{max_bits} samples"
        )

    # Flatten payload bits (MSB-first, matching the decoder).
    payload_bits = []
    for byte_val in framed:
        for shift in range(7, -1, -1):
            payload_bits.append((byte_val >> shift) & 1)

    # Replace LSBs.
    for i in range(bits_needed):
        s = samples[i]
        if (s & 1) != payload_bits[i]:
            if s < 0:
                s += 1  # -32768 → -32767 wraps; fine for LSB flip
            else:
                s ^= 1
        samples[i] = s

    out_raw = struct.pack(f"<{len(samples)}h", *samples)

    buf = io.BytesIO()
    w_out = wave.open(buf, "wb")
    w_out.setnchannels(nchannels)
    w_out.setsampwidth(sampwidth)
    w_out.setframerate(framerate)
    w_out.writeframes(out_raw)
    w_out.close()
    return buf.getvalue()
