"""CLI: stegg transform {list,inspect,encode,decode,auto-decode,categories}."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from m3gast3gg.cli import app


runner = CliRunner()


def _json(result):
    return json.loads(result.stdout)


def test_transform_list_json():
    r = runner.invoke(app, ["--json", "transform", "list"])
    assert r.exit_code == 0, r.stdout
    payload = _json(r)
    assert payload["count"] >= 20
    slugs = {t["slug"] for t in payload["transforms"]}
    for slug in ("base64", "caesar", "morse", "homoglyph", "reverse", "zalgo"):
        assert slug in slugs


def test_transform_list_filter_by_category():
    r = runner.invoke(app, ["--json", "transform", "list", "--category", "cipher"])
    assert r.exit_code == 0
    payload = _json(r)
    assert all(t["category"] == "cipher" for t in payload["transforms"])


def test_transform_inspect_by_slug():
    r = runner.invoke(app, ["--json", "transform", "inspect", "caesar"])
    assert r.exit_code == 0
    payload = _json(r)
    assert payload["slug"] == "caesar"
    assert payload["category"] == "cipher"
    ids = {o["id"] for o in payload["configurable_options"]}
    assert "shift" in ids


def test_transform_inspect_unknown_exits_2():
    r = runner.invoke(app, ["--json", "transform", "inspect", "does-not-exist"])
    assert r.exit_code == 2


def test_transform_encode_caesar_with_option():
    r = runner.invoke(app, [
        "--json", "transform", "encode", "caesar",
        "--text", "Attack at dawn", "--option", "shift=5",
    ])
    assert r.exit_code == 0, r.stdout
    payload = _json(r)
    assert payload["output"] == "Fyyfhp fy ifbs"
    assert payload["options"] == {"shift": 5}


def test_transform_decode_caesar():
    r = runner.invoke(app, [
        "--json", "transform", "decode", "caesar",
        "--text", "Fyyfhp fy ifbs", "--option", "shift=5",
    ])
    assert r.exit_code == 0
    payload = _json(r)
    assert payload["output"] == "Attack at dawn"


def test_transform_encode_unknown_option_exits_2():
    r = runner.invoke(app, [
        "--json", "transform", "encode", "caesar",
        "--text", "hi", "--option", "notreal=1",
    ])
    assert r.exit_code == 2


def test_transform_encode_option_out_of_range_exits_2():
    r = runner.invoke(app, [
        "--json", "transform", "encode", "caesar",
        "--text", "hi", "--option", "shift=100",
    ])
    assert r.exit_code == 2


def test_transform_auto_decode_base64():
    r = runner.invoke(app, [
        "--json", "transform", "auto-decode",
        "--text", "SGVsbG8sIFdvcmxkIQ==",
    ])
    assert r.exit_code == 0
    payload = _json(r)
    assert payload["candidates"]
    top = payload["candidates"][0]
    assert top["slug"] == "base64"
    assert top["text"] == "Hello, World!"


def test_transform_categories_json():
    r = runner.invoke(app, ["--json", "transform", "categories"])
    assert r.exit_code == 0
    payload = _json(r)
    assert payload["total"] >= 20
    assert "cipher" in payload["categories"]
    assert "encoding" in payload["categories"]


def test_transform_encode_empty_input_returns_empty():
    """Empty stdin under the test runner is treated as an empty input, which
    encodes to an empty output — the "no input" refusal only fires under a
    TTY, which the test runner doesn't emulate."""
    r = runner.invoke(app, ["--json", "transform", "encode", "caesar"])
    assert r.exit_code == 0
    payload = _json(r)
    assert payload["output"] == ""


def test_transform_decode_encode_only_exits_2():
    """A transform with can_decode=False would refuse decode; none of ours
    fit right now, so instead we just verify the error path via a bogus
    transform in a way that exercises code."""
    r = runner.invoke(app, ["--json", "transform", "decode", "no-such-transform",
                            "--text", "x"])
    assert r.exit_code == 2
