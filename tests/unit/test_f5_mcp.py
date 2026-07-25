"""Pipeline test: F5 encode/decode/capacity through the MCP executor surface."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from st3ggmcp.tools import TOOL_EXECUTORS, TOOL_SCHEMAS
from st3ggmcp.tools.image import (
    execute_f5_encode,
    execute_f5_decode,
    execute_f5_capacity,
)

F5_TOOLS = [
    "stegg_f5_encode",
    "stegg_f5_decode",
    "stegg_f5_capacity",
]


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Registry wiring
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", F5_TOOLS)
def test_f5_tools_registered(name):
    assert name in TOOL_EXECUTORS, f"{name} not in TOOL_EXECUTORS"
    assert name in TOOL_SCHEMAS, f"{name} not in TOOL_SCHEMAS"
    schema = TOOL_SCHEMAS[name]
    assert "description" in schema
    assert "path" in schema["inputSchema"]["required"]


# ---------------------------------------------------------------------------
# Fixture: a real JPEG from the F5 fixture set
# ---------------------------------------------------------------------------


@pytest.fixture
def carrier_jpg():
    fixtures = sorted((Path(__file__).resolve().parent / "fixtures" / "f5" / "jpeg").glob("*.jpg"))
    jpeg_path = next((p for p in fixtures if p.name == "stegg_short_ascii.jpg"), None)
    if jpeg_path is None:
        pytest.skip("no F5 JPEG fixture found")
    return jpeg_path


# ---------------------------------------------------------------------------
# stegg_f5_capacity
# ---------------------------------------------------------------------------


def test_f5_capacity_reports_keys(carrier_jpg):
    out = _run(execute_f5_capacity(str(carrier_jpg)))
    result = json.loads(out)
    assert "coeff_total" in result
    assert "capacity" in result
    assert "capacity_bytes" in result
    assert result["coeff_total"] > 0
    assert result["capacity_bytes"] > 0


# ---------------------------------------------------------------------------
# stegg_f5_encode + stegg_f5_decode round-trip
# ---------------------------------------------------------------------------


def test_f5_encode_decode_roundtrip_utf8(carrier_jpg, tmp_path):
    """Encode a UTF-8 message, decode it, assert bytes-exact match."""
    message = "Hello, F5 pipeline test! 🔐"
    password = "test-password"
    output = tmp_path / "encoded.jpg"

    enc_out = _run(execute_f5_encode(
        str(carrier_jpg),
        message=message,
        password=password,
        output_path=str(output),
    ))
    enc = json.loads(enc_out)
    assert "output_path" in enc
    assert Path(enc["output_path"]).exists()
    assert enc["payload_bytes"] == len(message.encode("utf-8"))

    dec_out = _run(execute_f5_decode(str(output), password=password))
    dec = json.loads(dec_out)
    assert dec["decoded"] is True
    assert dec["payload_utf8"] == message
    assert dec["size"] == len(message.encode("utf-8"))


def test_f5_encode_decode_roundtrip_hex(carrier_jpg, tmp_path):
    """Encode raw hex payload, decode, assert hex match."""
    payload_hex = "deadbeefcafebabe00112233"
    password = "hex-test-key"
    output = tmp_path / "hex_encoded.jpg"

    enc_out = _run(execute_f5_encode(
        str(carrier_jpg),
        payload_hex=payload_hex,
        password=password,
        output_path=str(output),
    ))
    enc = json.loads(enc_out)
    assert enc["payload_bytes"] == len(bytes.fromhex(payload_hex))

    dec_out = _run(execute_f5_decode(str(output), password=password))
    dec = json.loads(dec_out)
    assert dec["decoded"] is True
    assert dec["payload_hex"] == payload_hex
    # hex payload is not valid UTF-8, so payload_utf8 should be absent
    assert "payload_utf8" not in dec


def test_f5_decode_wrong_password(carrier_jpg, tmp_path):
    """Wrong password produces a decode error, not garbage."""
    output = tmp_path / "wrongkey.jpg"
    _run(execute_f5_encode(
        str(carrier_jpg), message="secret", password="alice",
        output_path=str(output),
    ))
    dec_out = _run(execute_f5_decode(str(output), password="bob"))
    dec = json.loads(dec_out)
    assert dec["decoded"] is False
    assert "error" in dec


def test_f5_encode_rejects_ambiguous_payload(carrier_jpg, tmp_path):
    """Both message and payload_hex should be rejected."""
    out = _run(execute_f5_encode(
        str(carrier_jpg),
        message="hello",
        payload_hex="abcd",
        password="x",
        output_path=str(tmp_path / "amb.jpg"),
    ))
    assert "exactly one of" in out.lower()


def test_f5_encode_rejects_no_payload(carrier_jpg, tmp_path):
    """Neither message nor payload_hex should be rejected."""
    out = _run(execute_f5_encode(
        str(carrier_jpg),
        password="x",
        output_path=str(tmp_path / "none.jpg"),
    ))
    assert "exactly one of" in out.lower()


def test_f5_capacity_missing_file():
    out = _run(execute_f5_capacity("/nonexistent/path.jpg"))
    assert "not found" in out.lower() or "error" in out.lower()
