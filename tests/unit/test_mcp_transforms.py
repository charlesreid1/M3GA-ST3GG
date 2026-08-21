"""MCP contract tests for stegg_*_transform tools."""

from __future__ import annotations

import json

import pytest

from m3gast3gg.mcp.transforms import (
    execute_auto_decode,
    execute_chain_transforms,
    execute_decode_transform,
    execute_encode_transform,
    execute_inspect_transform,
    execute_list_transforms,
)


@pytest.mark.asyncio
async def test_list_transforms_smoke():
    raw = await execute_list_transforms()
    payload = json.loads(raw)
    assert payload["count"] >= 20
    slugs = {t["slug"] for t in payload["transforms"]}
    for slug in ("base64", "caesar", "morse", "homoglyph", "reverse", "zalgo"):
        assert slug in slugs


@pytest.mark.asyncio
async def test_list_transforms_category_filter():
    raw = await execute_list_transforms(category="cipher")
    payload = json.loads(raw)
    assert all(t["category"] == "cipher" for t in payload["transforms"])


@pytest.mark.asyncio
async def test_list_transforms_unknown_category():
    raw = await execute_list_transforms(category="not-real")
    payload = json.loads(raw)
    assert "error" in payload


@pytest.mark.asyncio
async def test_inspect_transform_by_slug():
    raw = await execute_inspect_transform(name="caesar")
    payload = json.loads(raw)
    assert payload["slug"] == "caesar"
    assert payload["category"] == "cipher"
    ids = {o["id"] for o in payload["configurable_options"]}
    assert "shift" in ids


@pytest.mark.asyncio
async def test_inspect_transform_unknown_error():
    raw = await execute_inspect_transform(name="does-not-exist")
    payload = json.loads(raw)
    assert "error" in payload


@pytest.mark.asyncio
async def test_encode_caesar_with_option():
    raw = await execute_encode_transform(
        name="caesar", text="Attack at dawn", options={"shift": 5},
    )
    payload = json.loads(raw)
    assert payload["output"] == "Fyyfhp fy ifbs"


@pytest.mark.asyncio
async def test_decode_caesar_with_option():
    raw = await execute_decode_transform(
        name="caesar", text="Fyyfhp fy ifbs", options={"shift": 5},
    )
    payload = json.loads(raw)
    assert payload["output"] == "Attack at dawn"


@pytest.mark.asyncio
async def test_encode_bad_option_returns_error():
    raw = await execute_encode_transform(
        name="caesar", text="x", options={"shift": 999},
    )
    payload = json.loads(raw)
    assert "error" in payload


@pytest.mark.asyncio
async def test_encode_unknown_transform_returns_error():
    raw = await execute_encode_transform(name="no-such", text="x")
    payload = json.loads(raw)
    assert "error" in payload


@pytest.mark.asyncio
async def test_encode_oversize_text_returns_error():
    big = "a" * (2 * 1024 * 1024)
    raw = await execute_encode_transform(name="base64", text=big)
    payload = json.loads(raw)
    assert "error" in payload
    assert "too large" in payload["error"]


@pytest.mark.asyncio
async def test_auto_decode_base64():
    raw = await execute_auto_decode(text="SGVsbG8sIFdvcmxkIQ==")
    payload = json.loads(raw)
    assert payload["count"] >= 1
    top = payload["candidates"][0]
    assert top["slug"] == "base64"
    assert top["text"] == "Hello, World!"


@pytest.mark.asyncio
async def test_auto_decode_empty_input():
    raw = await execute_auto_decode(text="")
    payload = json.loads(raw)
    assert payload["count"] == 0


@pytest.mark.asyncio
async def test_auto_decode_top_k_zero():
    raw = await execute_auto_decode(text="SGVsbG8=", top_k=0)
    payload = json.loads(raw)
    assert payload["count"] == 0


def test_registry_wired_into_mcp():
    """stegg_*_transform tools are picked up by the top-level registry merge."""
    from m3gast3gg.mcp import TOOL_EXECUTORS, TOOL_SCHEMAS
    for name in ("stegg_list_transforms", "stegg_inspect_transform",
                 "stegg_encode_transform", "stegg_decode_transform",
                 "stegg_chain_transforms",
                 "stegg_auto_decode"):
        assert name in TOOL_EXECUTORS, f"executor missing: {name}"
        assert name in TOOL_SCHEMAS, f"schema missing: {name}"


@pytest.mark.asyncio
async def test_chain_transforms_encode_pipeline():
    raw = await execute_chain_transforms(
        text="Attack",
        steps=[
            {"name": "caesar", "action": "encode", "options": {"shift": 5}},
            {"name": "base64", "action": "encode"},
        ],
    )
    payload = json.loads(raw)
    assert payload["output"] == "Rnl5Zmhw"
    assert len(payload["steps"]) == 2
    assert payload["steps"][0]["transform"] == "caesar"
    assert payload["steps"][1]["transform"] == "base64"


@pytest.mark.asyncio
async def test_chain_transforms_roundtrip():
    """encode(caesar → base64) then decode(base64 → caesar) recovers input."""
    forward = await execute_chain_transforms(
        text="Attack",
        steps=[
            {"name": "caesar", "options": {"shift": 5}},
            {"name": "base64"},
        ],
    )
    mid = json.loads(forward)["output"]
    reverse = await execute_chain_transforms(
        text=mid,
        steps=[
            {"name": "base64", "action": "decode"},
            {"name": "caesar", "action": "decode", "options": {"shift": 5}},
        ],
    )
    assert json.loads(reverse)["output"] == "Attack"


@pytest.mark.asyncio
async def test_chain_transforms_empty_steps_error():
    raw = await execute_chain_transforms(text="hi", steps=[])
    assert "error" in json.loads(raw)


@pytest.mark.asyncio
async def test_chain_transforms_unknown_transform_error():
    raw = await execute_chain_transforms(
        text="hi", steps=[{"name": "no-such"}],
    )
    payload = json.loads(raw)
    assert "error" in payload
    assert "unknown transform" in payload["error"]


@pytest.mark.asyncio
async def test_chain_transforms_bad_action_error():
    raw = await execute_chain_transforms(
        text="hi", steps=[{"name": "base64", "action": "wat"}],
    )
    assert "error" in json.loads(raw)


@pytest.mark.asyncio
async def test_chain_transforms_bad_option_error():
    raw = await execute_chain_transforms(
        text="hi",
        steps=[{"name": "caesar", "options": {"shift": 999}}],
    )
    assert "error" in json.loads(raw)
