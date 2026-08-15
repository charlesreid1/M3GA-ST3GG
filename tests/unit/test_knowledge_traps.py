"""
Adversarial trap catalog + integrity tests for ST3GG's typed-record KR.

Each trap is a natural-language claim a CTF judge might plant. Every trap
comes with (a) an adversarial paraphrase the KR must recognize as wrong,
and (b) a truthful control that must NOT be misclassified — the false-
lead half of the catalog. Controls are how we notice when the match_patterns
grow too eager and start reporting bluffs.

Integrity tests catch silent rot: orphan bibliography entries, unresolved
see_also links, categories the plan promised but the KR forgot.

Source ground-truth: plan-knowledge-base.md, the seeded myths.json trap
patterns, and the Slack probe (TRANSPORT_RESULTS_SLACK.json).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from st3ggmcp import records
from st3ggmcp.tools import TOOL_EXECUTORS


RECORDS_DIR = Path(__file__).resolve().parents[2] / "knowledge" / "records"


@pytest.fixture(scope="module")
def store() -> records.RecordStore:
    return records.RecordStore.load(RECORDS_DIR)


def _verify_claim(text: str) -> dict:
    r = asyncio.run(TOOL_EXECUTORS["stegg_verify_claim"](text=text))
    return json.loads(r)


# --- load-time contract -------------------------------------------------------


def test_store_loads_at_least_a_hundred_records(store):
    assert len(store.records) >= 100


def test_every_expected_category_is_populated(store):
    """Every category the plan describes has at least one record."""
    expected = {
        "bibliography",
        "technique",
        "carrier_format",
        "layer",
        "transport",
        "survival",
        "detector",
        "signature",
        "myth",
    }
    have = set(store.by_category)
    missing = expected - have
    assert not missing, f"categories with zero records: {sorted(missing)}"


def test_every_nonbib_record_has_resolvable_citations(store):
    bib_ids = {r["id"] for r in store.in_category("bibliography")}
    for rec in store.all_records():
        if rec.get("category") == "bibliography":
            continue
        cites = rec.get("citations") or []
        assert cites, f"{rec['id']} has empty citations"
        assert all(c in bib_ids for c in cites), f"{rec['id']} cites unknown source"


def test_every_record_has_two_element_era_bounds(store):
    for rec in store.all_records():
        eb = rec.get("era_bounds")
        assert isinstance(eb, list) and len(eb) == 2, f"{rec['id']} era_bounds"


def test_empty_citations_raises(tmp_path):
    (tmp_path / "bibliography.json").write_text('[{"id":"b1","category":"bibliography","era_bounds":[null,null]}]')
    (tmp_path / "techniques.json").write_text(
        '[{"id":"t1","category":"technique","era_bounds":[null,null],"citations":[]}]'
    )
    with pytest.raises(records.RecordError, match="empty citations"):
        records.RecordStore.load(tmp_path)


def test_unresolved_citation_raises(tmp_path):
    (tmp_path / "bibliography.json").write_text('[{"id":"b1","category":"bibliography","era_bounds":[null,null]}]')
    (tmp_path / "techniques.json").write_text(
        '[{"id":"t1","category":"technique","era_bounds":[null,null],"citations":["nope"]}]'
    )
    with pytest.raises(records.RecordError, match="does not resolve"):
        records.RecordStore.load(tmp_path)


def test_missing_era_bounds_raises(tmp_path):
    (tmp_path / "bibliography.json").write_text('[{"id":"b1","category":"bibliography","era_bounds":[null,null]}]')
    (tmp_path / "techniques.json").write_text(
        '[{"id":"t1","category":"technique","citations":["b1"]}]'
    )
    with pytest.raises(records.RecordError, match="era_bounds"):
        records.RecordStore.load(tmp_path)


def test_duplicate_id_raises(tmp_path):
    (tmp_path / "bibliography.json").write_text(
        '[{"id":"b1","category":"bibliography","era_bounds":[null,null]},'
        ' {"id":"b1","category":"bibliography","era_bounds":[null,null]}]'
    )
    with pytest.raises(records.RecordError, match="duplicate"):
        records.RecordStore.load(tmp_path)


# --- resolution + era ---------------------------------------------------------


def test_alias_resolution(store):
    """Every seeded alias resolves back to its record."""
    assert store.resolve("f5")["id"] == "image-f5"
    assert store.resolve("cyrillic_homoglyph")["id"] == "text-cyrillic-homoglyph"
    assert store.resolve("slack_upload")["id"] == "transport-slack-upload"
    assert store.resolve("slack_paste")["id"] == "transport-slack-paste"
    assert store.resolve("slack_snippet")["id"] == "transport-slack-snippet"
    assert store.resolve("png-lsb")["id"] == "image-lsb"


def test_case_and_space_insensitive_resolution(store):
    """resolve normalizes case and dashes/underscores/spaces."""
    assert store.resolve("F5")["id"] == "image-f5"
    assert store.resolve("Cyrillic Homoglyph")["id"] == "text-cyrillic-homoglyph"
    assert store.resolve("SLACK UPLOAD")["id"] == "transport-slack-upload"


def test_era_contains_bounds(store):
    """era_contains correctly bounds by lower and upper."""
    lsb = store.get("image-lsb")
    assert records.era_contains(lsb, 2020)  # LSB is 1994-open
    assert records.era_contains(lsb, 1994)  # inclusive lower bound
    assert not records.era_contains(lsb, 1993)


def test_era_contains_open_upper(store):
    """era_bounds ending in null means 'still valid'."""
    lsb = store.get("image-lsb")
    assert lsb["era_bounds"][1] is None
    assert records.era_contains(lsb, 2050)


def test_era_contains_dated_slack_probe(store):
    """The Slack probe evidence is dated exactly 2026-07-26."""
    probe = store.get("st3gg-transport-results-slack")
    assert records.era_contains(probe, 2026)
    assert not records.era_contains(probe, 2025)
    assert not records.era_contains(probe, 2027)


# --- verify_claim: the adversarial trap catalog -------------------------------
#
# Each row: (claim, expected_verdict, description). The catalog pairs
# adversarial claims (which SHOULD match a myth pattern) with truthful
# controls (which must NOT be misclassified). Controls are the false-lead
# half — they exist to keep match_patterns honest.


_ADVERSARIAL_TRAPS = [
    # --- adversarial claims (must match a myth) ---
    ("LSB steg survives JPEG re-encoding at Q99.",
     "false", "LSB-vs-JPEG (classic trap)"),
    ("Pixel-level LSB survives a JPEG round-trip.",
     "false", "LSB-vs-JPEG paraphrase"),
    ("You can safely hide with LSB and send through a JPEG pipeline.",
     "false", "LSB-vs-JPEG passive framing"),

    ("Cyrillic homoglyphs survive NFKC normalization.",
     "false", "homoglyph-vs-NFKC"),
    ("Homoglyph text steg is robust to Unicode normalization.",
     "false", "homoglyph-vs-normalization"),

    ("Slack preserves image EXIF metadata on file upload.",
     "false", "Slack-metadata trap"),
    ("Slack keeps PNG tEXt chunks intact.",
     "false", "Slack-metadata paraphrase"),

    ("Zero-width chars are invisible on every UI everywhere.",
     "needs_qualification", "zero-width universality"),
    ("Invisible zero-width chars work in any terminal, everywhere.",
     "needs_qualification", "zero-width universality paraphrase"),

    ("steghide can read files produced by outguess.",
     "false", "steghide-vs-outguess"),
    ("A steghide install will decode an F5 payload.",
     "false", "steghide-vs-F5"),

    ("F5 DCT steg survives Slack's JPEG re-encoder.",
     "false", "F5-Slack recode"),
    ("jsteg payload survives WhatsApp photo re-encode.",
     "false", "jsteg-WhatsApp recode"),
    ("OutGuess DCT payloads survive Telegram photo recompress.",
     "false", "OutGuess-Telegram recode"),

    ("Black flag emoji tag payloads survive Slack paste.",
     "false", "emoji-tag Slack paste"),
    ("Emoji tag-sequence steg works when pasted into a Slack body.",
     "false", "emoji-tag Slack paste paraphrase"),

    ("If every alpha byte's LSB is 1 that's encrypted payload.",
     "false", "alpha-all-ones-encrypted"),

    ("PCM sample LSB survives an MP3 re-encode.",
     "false", "audio-LSB-vs-MP3"),
    ("Audio LSB payload will safely round-trip through Opus.",
     "false", "audio-LSB-vs-Opus paraphrase"),

    ("Slack recodes PNG pixels and strips IDAT on upload.",
     "false", "slack-strips-pixels"),

    ("EXIF survives everywhere across every messenger.",
     "false", "metadata-survives-anywhere"),

    ("Variation selectors survive terminal mouse-copy.",
     "false", "VS-terminal"),

    ("Polyglot files decode regardless of order of the containers.",
     "needs_qualification", "polyglot-order"),

    ("Any generic JPEG library can decode an F5 payload.",
     "false", "F5-any-decoder"),

    ("Chi-square attacks reliably detect OutGuess.",
     "false", "chi-square-vs-OutGuess"),

    ("Encrypting the cover payload makes the steg channel undetectable.",
     "false", "encryption-hides-steg"),

    ("Unicode tag characters pass through every input sanitizer safely.",
     "false", "tag-block sanitizers"),

    ("iMessage always delivers original bytes for photos.",
     "needs_qualification", "iMessage-original-bytes"),

    ("GitHub strips EXIF metadata from uploaded images.",
     "false", "github-strips-exif"),

    ("PVD survives JPEG re-encoding through Slack.",
     "false", "PVD-vs-JPEG"),

    # --- truthful CONTROLS (must NOT match any myth) ---
    # Real technical facts. `unverified` is the honest answer here.
    ("The sky is blue.",
     "unverified", "CONTROL: unrelated statement"),
    ("PNG uses IHDR PLTE IDAT IEND critical chunks.",
     "unverified", "CONTROL: PNG chunk grammar (true)"),
    ("DCT lives at the coefficient layer.",
     "unverified", "CONTROL: layer taxonomy (true)"),
    ("The ST3GG v3 header uses HMAC-SHA256-derived magic bytes.",
     "unverified", "CONTROL: v3 header (true)"),
    ("PVD hides in the difference between adjacent pixels.",
     "unverified", "CONTROL: PVD (true)"),
    ("Slack has three distinct upload transports.",
     "unverified", "CONTROL: Slack has three transports (true)"),
    # An 'LSB' mention alone must NOT trigger the LSB-vs-JPEG trap.
    ("LSB works fine when the file is delivered byte-identical over HTTP.",
     "unverified", "CONTROL: LSB byte-identical is fine"),
    # A JPEG mention alone must NOT trigger.
    ("JPEG uses 8 by 8 DCT blocks.",
     "unverified", "CONTROL: JPEG DCT block structure"),
    # A homoglyph mention alone must NOT trigger the NFKC trap.
    ("Homoglyphs are visually-identical Unicode codepoint pairs.",
     "unverified", "CONTROL: homoglyph definition"),
    # A Slack mention alone must NOT trigger the metadata trap.
    ("Slack canonicalizes emoji to colon form on the wire.",
     "unverified", "CONTROL: Slack emoji canon"),
    # A 'zero-width' mention alone must NOT trigger the universality trap.
    ("Zero-width chars occupy Unicode codepoints U+200B through U+200D.",
     "unverified", "CONTROL: zero-width codepoint range"),
    # A 'steghide' mention alone must NOT trigger.
    ("steghide is a JPEG steganography tool.",
     "unverified", "CONTROL: steghide description"),
    # An 'F5' + 'Slack' combo without 'survive' language must NOT trigger.
    ("F5 was published by Andreas Westfeld in 2001.",
     "unverified", "CONTROL: F5 publication history"),
    # An 'alpha' + 'payload' combo without 'all ones' must NOT trigger.
    ("The alpha channel can carry a payload if the source image had alpha.",
     "unverified", "CONTROL: alpha payload conditional"),
]


@pytest.mark.parametrize("claim,verdict,description", _ADVERSARIAL_TRAPS)
def test_adversarial_trap_catalog(claim, verdict, description):
    """Adversarial claims must match a myth; truthful controls must return
    `unverified` rather than being bluffed into a false verdict."""
    v = _verify_claim(claim)
    assert v["verdict"] == verdict, (
        f"{description}: expected {verdict!r}, got {v['verdict']!r} — {claim}"
    )


def test_unmatched_claim_is_unverified_not_bluffed():
    """The no-bluff invariant: 'unverified' means 'I don't have a record,'
    not 'I guessed.'"""
    v = _verify_claim("blue is the primary color of steganography")
    assert v["verdict"] == "unverified"
    assert "record" in v["reasoning"].lower()


def test_verify_claim_returns_myth_id_when_it_hits(store):
    """A verified verdict comes back with the record_id and citations, so
    the caller can look up primary sources."""
    v = _verify_claim("LSB survives JPEG re-encoding at Q99")
    assert v["verdict"] == "false"
    assert v.get("record_id") == "myth-lsb-survives-jpeg"
    assert v["citations"], "no citations returned with false verdict"


# --- trap catalog structural checks -------------------------------------------


def test_every_myth_carries_match_patterns(store):
    """Every myth needs match_patterns; without them verify_claim can't hit."""
    for m in store.in_category("myth"):
        body = m.get("technical_body", {})
        patterns = body.get("match_patterns") or []
        assert patterns, f"{m['id']}: empty match_patterns"


def test_every_myth_match_pattern_is_valid_regex(store):
    """match_patterns are compiled as regex; malformed ones would silently
    kill verify_claim on that myth."""
    import re
    for m in store.in_category("myth"):
        for pat in m["technical_body"].get("match_patterns", []):
            try:
                re.compile(pat)
            except re.error as e:
                pytest.fail(f"{m['id']}: invalid regex {pat!r}: {e}")


def test_every_myth_has_verdict_and_correct_form(store):
    """A myth without correct_form is useless; a verdict is what makes it a trap."""
    for m in store.in_category("myth"):
        body = m["technical_body"]
        assert body.get("verdict") in ("false", "needs_qualification"), f"{m['id']}: bad verdict"
        assert body.get("correct_form"), f"{m['id']}: empty correct_form"


def test_trap_catalog_size_meets_target(store):
    """The plan targets 20 seeded myths. Failing this means the catalog
    shrank — investigate before merging."""
    assert len(store.in_category("myth")) >= 20


# --- integrity: silent rot detection ------------------------------------------


def test_no_orphan_bibliography_records(store):
    """Every bibliography entry must be cited by at least one non-bib record.
    Orphans are dead weight and often indicate a rename that lost its
    references."""
    cited: set[str] = set()
    for rec in store.all_records():
        if rec.get("category") == "bibliography":
            continue
        cited.update(rec.get("citations") or [])
    bib_ids = {r["id"] for r in store.in_category("bibliography")}
    orphans = bib_ids - cited
    assert not orphans, f"orphan bibliography entries: {sorted(orphans)}"


def test_all_see_also_references_resolve(store):
    """Every see_also entry must resolve to an existing record id or alias."""
    broken = []
    for rec in store.all_records():
        for ref in rec.get("see_also") or []:
            if ref in store.records:
                continue
            if store.alias_index.get(records._normalize(ref)) is not None:
                continue
            broken.append((rec["id"], ref))
    assert not broken, f"broken see_also links: {broken[:10]}"


def test_survival_records_reference_real_technique_and_transport(store):
    """Every survival record's technical_body.technique_id and .transport_id
    must resolve. `applies_to` (used by umbrella rows) same story."""
    broken = []
    for rec in store.in_category("survival"):
        body = rec.get("technical_body") or {}
        for field in ("technique_id", "transport_id"):
            target = body.get(field)
            if target and target not in store.records:
                broken.append((rec["id"], field, target))
        for aid in body.get("applies_to") or []:
            if aid not in store.records:
                broken.append((rec["id"], "applies_to", aid))
    assert not broken, f"broken survival refs: {broken[:10]}"


def test_bibliography_records_dont_self_cite(store):
    """Bib records must not have a citations field — that's for consumers,
    not the bib entries themselves."""
    for rec in store.in_category("bibliography"):
        cites = rec.get("citations")
        if cites:
            pytest.fail(f"bibliography record {rec['id']} has citations={cites}")


def test_no_record_cites_itself(store):
    for rec in store.all_records():
        rid = rec["id"]
        cites = rec.get("citations") or []
        assert rid not in cites, f"{rid} cites itself"


def test_disputed_fields_are_nonempty_when_present(store):
    """A disputed{} block signals 'this claim has caveats' — empty values
    defeat that."""
    for rec in store.all_records():
        disputed = rec.get("disputed")
        if not disputed:
            continue
        assert isinstance(disputed, dict), f"{rec['id']}: disputed must be a dict"
        for key, value in disputed.items():
            assert value, f"{rec['id']}: disputed.{key} is empty"


# --- ontology + coverage matrix -----------------------------------------------


PLAN_CATEGORIES = frozenset({
    "bibliography",
    "technique",
    "carrier_format",
    "layer",
    "transport",
    "survival",
    "detector",
    "signature",
    "myth",
})

KNOWN_CARRIER_FAMILIES = frozenset({
    "image", "text", "emoji", "audio", "network", "document", "universal",
})

KNOWN_LAYERS = frozenset({
    "bit", "coefficient", "character", "container", "semantic", "universal",
})


def test_plan_ontology_is_fully_covered(store):
    """Every category the plan promises has at least one record."""
    have = set(store.by_category.keys())
    missing = PLAN_CATEGORIES - have
    assert not missing, f"plan categories with zero records: {sorted(missing)}"


def test_every_record_carrier_family_is_recognized(store):
    unknown = {}
    for rec in store.all_records():
        if rec.get("category") == "bibliography":
            continue
        cf = rec.get("carrier_family")
        if cf is None:
            continue
        if cf not in KNOWN_CARRIER_FAMILIES:
            unknown.setdefault(cf, []).append(rec["id"])
    assert not unknown, f"unrecognized carrier_family values: {unknown}"


def test_every_record_layer_is_recognized(store):
    unknown = {}
    for rec in store.all_records():
        if rec.get("category") == "bibliography":
            continue
        layer = rec.get("layer")
        if layer is None:
            continue
        if layer not in KNOWN_LAYERS:
            unknown.setdefault(layer, []).append(rec["id"])
    assert not unknown, f"unrecognized layer values: {unknown}"


# Canonical (carrier_family, transport) coverage cells the KR promises to
# answer. Each cell must have at least one technique whose survival record
# on that transport is ✅ or ⚠.
COVERAGE_CELLS = [
    ("image", "transport-slack-upload"),
    ("image", "transport-http-raw"),
    ("text",  "transport-slack-paste"),
    ("text",  "transport-slack-snippet"),
    ("text",  "transport-http-raw"),
    ("emoji", "transport-slack-paste"),
]


@pytest.mark.parametrize("carrier_family,transport_id", COVERAGE_CELLS)
def test_carrier_transport_coverage(store, carrier_family, transport_id):
    """For every canonical cell, at least one technique of that family has a
    ✅ or ⚠ survival record on that transport (directly or via applies_to)."""
    surviving_ids: set[str] = set()
    for rec in store.in_category("survival"):
        body = rec.get("technical_body") or {}
        if body.get("transport_id") != transport_id:
            continue
        status = str(body.get("status", ""))
        if not status.startswith(("✅", "⚠")):
            continue
        surviving_ids.add(body.get("technique_id", ""))
        for aid in body.get("applies_to") or []:
            surviving_ids.add(aid)
    hits = [
        t for t in store.in_category("technique")
        if t["id"] in surviving_ids and t.get("carrier_family") == carrier_family
    ]
    assert hits, f"no {carrier_family} technique with ✅/⚠ survival on {transport_id}"


# --- retrieval-tool spot checks -----------------------------------------------


def test_lookup_technique_unknown_returns_known_ids():
    """Unknown lookup returns known_ids so the caller can pick the right name."""
    r = asyncio.run(TOOL_EXECUTORS["stegg_lookup_technique"](name="purple-box"))
    obj = json.loads(r)
    assert "error" in obj
    assert "known_ids" in obj
    assert obj["known_ids"]


def test_verify_survival_untested_pair_returns_question_mark():
    """A pair with no seeded record returns '❓ untested' — honest gap report."""
    r = asyncio.run(TOOL_EXECUTORS["stegg_verify_survival"](
        technique="image-lsb", transport="transport-imessage-attachment",
    ))
    obj = json.loads(r)
    assert obj["status"] == "❓ untested"


def test_search_records_by_transport_only_returns_surviving_techniques(store):
    """Passing `transport` to search_records filters to ✅/⚠ techniques on it."""
    r = asyncio.run(TOOL_EXECUTORS["stegg_search_records"](
        category="technique", transport="transport-slack-paste",
    ))
    obj = json.loads(r)
    ids = {res["id"] for res in obj["results"]}
    # These specific text techniques survive Slack paste per the probe
    assert "text-cyrillic-homoglyph" in ids
    assert "text-zero-width" in ids
    # Whitespace and invisible-ink RECODE, so they must NOT appear
    assert "text-whitespace" not in ids
    assert "text-invisible-ink" not in ids


def test_search_records_carrier_family_filter(store):
    r = asyncio.run(TOOL_EXECUTORS["stegg_search_records"](
        category="technique", carrier_family="emoji",
    ))
    obj = json.loads(r)
    families = {res.get("carrier_family") for res in obj["results"]}
    assert families == {"emoji"}


def test_cross_reference_follows_see_also_links():
    r = asyncio.run(TOOL_EXECUTORS["stegg_cross_reference"](record_id="image-lsb"))
    obj = json.loads(r)
    assert obj["id"] == "image-lsb"
    # image-lsb sees image-pvd, image-dct, layer-bit
    linked_ids = {link["id"] for link in obj["see_also"] if link["resolved"]}
    assert "image-pvd" in linked_ids or "layer-bit" in linked_ids


def test_bibliography_lists_all_when_called_bare():
    r = asyncio.run(TOOL_EXECUTORS["stegg_bibliography"]())
    obj = json.loads(r)
    ids = {s["id"] for s in obj["sources"]}
    for expected in ("westfeld-2001-f5", "fridrich-2001-rs", "simmons-1983-prisoners",
                     "rfc-2083-png", "st3gg-transport-results-slack"):
        assert expected in ids, f"{expected} missing from bibliography listing"


def test_explain_pipeline_returns_no_candidates_for_impossible_combo(store):
    """Impossible combos (image techniques over a text-only transport) return
    zero candidates rather than fabricating."""
    r = asyncio.run(TOOL_EXECUTORS["stegg_explain_pipeline"](
        goal="image over pbcopy", carrier="image", transport="transport-pbcopy",
    ))
    obj = json.loads(r)
    # No survival cells for image techniques on pbcopy → zero candidates
    assert obj["candidates"] == 0
    assert obj["steps"] == []


def test_explain_pipeline_transport_survival_wired(store):
    """The pipeline tool must filter by survival, not just carrier family."""
    r = asyncio.run(TOOL_EXECUTORS["stegg_explain_pipeline"](
        goal="text over slack paste", carrier="text", transport="transport-slack-paste",
    ))
    obj = json.loads(r)
    ids = {s["technique_id"] for s in obj["steps"]}
    # Whitespace recodes → must not appear
    assert "text-whitespace" not in ids
    # Zero-width survives → must appear (or at least one prose-plausible tech)
    assert "text-zero-width" in ids or "text-cyrillic-homoglyph" in ids


# --- lore corpus --------------------------------------------------------------


def test_list_topics_covers_the_ten_top_level_topics():
    r = asyncio.run(TOOL_EXECUTORS["stegg_list_topics"]())
    obj = json.loads(r)
    expected = {"image", "text", "emoji", "audio", "network",
                "document", "detection", "transport", "crypto", "ctf"}
    assert expected <= set(obj["topics"])


def test_read_lore_returns_readme_content():
    """The transport README carries the canonicalization-principle headline."""
    r = asyncio.run(TOOL_EXECUTORS["stegg_read_lore"](topic="transport", name="README"))
    assert "canonical" in r.lower()
    assert "slack" in r.lower()


def test_search_lore_finds_canonical_layer_prose():
    r = asyncio.run(TOOL_EXECUTORS["stegg_search_lore"](query="canonical layer"))
    obj = json.loads(r)
    assert obj["hit_count"] >= 1
    topics = {hit["topic"] for hit in obj["results"]}
    assert "transport" in topics


def test_search_lore_unknown_pattern_returns_zero_hits():
    r = asyncio.run(TOOL_EXECUTORS["stegg_search_lore"](
        query="THIS_SPECIFIC_STRING_APPEARS_NOWHERE_IN_THE_CORPUS_XYZ42",
    ))
    obj = json.loads(r)
    assert obj["hit_count"] == 0
