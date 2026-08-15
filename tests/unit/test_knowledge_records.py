"""Knowledge base: record loading, envelope invariants, retrieval tools."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from st3ggmcp import records
from st3ggmcp.tools import TOOL_EXECUTORS


REPO_ROOT = Path(__file__).resolve().parents[2]
RECORDS_DIR = REPO_ROOT / "knowledge" / "records"


@pytest.fixture(scope="module")
def store() -> records.RecordStore:
    return records.RecordStore.load(RECORDS_DIR)


def test_store_loads_all_categories(store: records.RecordStore) -> None:
    categories = set(store.by_category)
    assert {
        "bibliography",
        "technique",
        "carrier_format",
        "layer",
        "transport",
        "survival",
        "detector",
        "signature",
        "myth",
        "capacity_model",
        "external_tool",
        "ctf_genre",
    } <= categories


def test_every_non_bibliography_record_cites_a_bibliography_entry(store: records.RecordStore) -> None:
    bib_ids = {rid for rid, r in store.records.items() if r.get("category") == "bibliography"}
    for rid, rec in store.records.items():
        if rec.get("category") == "bibliography":
            continue
        cites = rec.get("citations") or []
        assert cites, f"{rid} has no citations"
        for c in cites:
            assert c in bib_ids, f"{rid} cites unresolved {c!r}"


def test_every_record_has_era_bounds(store: records.RecordStore) -> None:
    for rid, rec in store.records.items():
        eb = rec.get("era_bounds")
        assert isinstance(eb, list) and len(eb) == 2, f"{rid} has bad era_bounds: {eb!r}"


def test_lookup_technique_returns_full_record() -> None:
    r = asyncio.run(TOOL_EXECUTORS["stegg_lookup_technique"](name="f5"))
    obj = json.loads(r)
    assert obj["id"] == "image-f5"
    assert "technical_body" in obj
    assert obj["technical_body"]["code_module"].startswith("img_core.f5")


def test_verify_survival_slack_lsb() -> None:
    r = asyncio.run(TOOL_EXECUTORS["stegg_verify_survival"](
        technique="image-lsb", transport="slack_upload"
    ))
    obj = json.loads(r)
    assert obj["technique_id"] == "image-lsb"
    assert obj["transport_id"] == "transport-slack-upload"
    assert obj["status"].startswith("✅")


@pytest.mark.parametrize("claim, expected", [
    ("LSB survives JPEG recompression at Q=99", "false"),
    ("homoglyphs survive NFKC normalization", "false"),
    ("Slack preserves EXIF metadata on upload", "false"),
    ("zero-width chars are invisible everywhere", "needs_qualification"),
    ("steghide can read outguess files", "false"),
    ("F5 DCT steg survives Slack re-encode", "false"),
    ("the sky is blue", "unverified"),
])
def test_verify_claim_grades_myths(claim: str, expected: str) -> None:
    r = asyncio.run(TOOL_EXECUTORS["stegg_verify_claim"](text=claim))
    obj = json.loads(r)
    assert obj["verdict"] == expected, f"{claim!r} => {obj['verdict']!r}"


def test_explain_pipeline_filters_by_transport() -> None:
    r = asyncio.run(TOOL_EXECUTORS["stegg_explain_pipeline"](
        goal="prose-looking text over slack paste",
        carrier="text",
        transport="slack_paste",
        constraint="prose-like",
    ))
    obj = json.loads(r)
    assert obj["candidates"] > 0
    ids = [s["technique_id"] for s in obj["steps"]]
    assert "text-cyrillic-homoglyph" in ids
