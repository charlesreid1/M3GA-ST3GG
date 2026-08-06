"""
Gold-standard Q/A regression tests for the ST3GG typed-record KR.

Each test is a concrete factual question a stego-CTF judge might ask,
bound to a specific record field. When someone edits a record and drifts
a value the KR promises, one of these tests goes red and points at the
drift.

This is not a test of ST3GG's language ability — it's a test that the
numbers, framings, and dates in the records still match what
plan-knowledge-base.md and the primary bibliography say they should be.

Source ground-truth: plan-knowledge-base.md, TRANSPORT_MATRIX.md,
TRANSPORT_RESULTS_SLACK.json, and the primary bibliography entries
(Westfeld 2001, Provos 2001, Fridrich 2001, Unicode UTS #36 / UAX #15,
RFC 2083, ITU-T T.81).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from st3ggmcp import records


RECORDS_DIR = Path(__file__).resolve().parents[2] / "knowledge" / "records"


@pytest.fixture(scope="module")
def store() -> records.RecordStore:
    return records.RecordStore.load(RECORDS_DIR)


def _body(store_, record_id: str) -> dict:
    rec = store_.get(record_id)
    assert rec is not None, f"record {record_id!r} missing from KR"
    return rec.get("technical_body") or {}


# --- text techniques: exact framing --------------------------------------------


def test_zero_width_uses_zwsp_zwnj(store):
    body = _body(store, "text-zero-width")
    alphabet = body["alphabet"]
    assert any("200B" in x for x in alphabet)
    assert any("200C" in x for x in alphabet)


def test_zero_width_delimiters_are_zwj(store):
    """ZWJ (U+200D) is the start+end marker — not a payload bit."""
    body = _body(store, "text-zero-width")
    assert "200D" in body["framing"]
    assert "ZWJ" in body["framing"]


def test_zero_width_bits_per_carrier_is_one(store):
    assert _body(store, "text-zero-width")["bits_per_carrier_unit"] == 1


def test_cyrillic_homoglyph_uses_16bit_length_prefix(store):
    body = _body(store, "text-cyrillic-homoglyph")
    assert body["prefix_scheme"] == "16-bit length prefix"
    assert body["header_format"] == "16-bit LE length prefix"


def test_cyrillic_homoglyph_dies_to_nfkc(store):
    """The core reason cyrillic_homoglyph isn't safe against sanitizers."""
    body = _body(store, "text-cyrillic-homoglyph")
    assert "NFKC" in body["normalization_risk"]


def test_cjk_homoglyph_swaps_ascii_punctuation(store):
    """CJK homoglyph swaps ASCII punct for fullwidth twins, not letters."""
    body = _body(store, "text-cjk-homoglyph")
    assert "punctuation" in body["alphabet"].lower() or "ASCII punct" in body["alphabet"]
    assert "fullwidth" in body["alphabet"].lower() or "CJK" in body["alphabet"]


def test_whitespace_carries_8_bits_per_line(store):
    """SNOW-style: 8 bits per line via tab/space run."""
    body = _body(store, "text-whitespace")
    assert body["bits_per_carrier_unit"] == 8
    assert "line" in body["framing"].lower() or "trailing" in body["framing"].lower()


def test_invisible_ink_uses_tag_block(store):
    """U+E0020..U+E007E is the ASCII-shadow range."""
    body = _body(store, "text-invisible-ink")
    assert "E0020" in body["alphabet"]
    assert "E007" in body["alphabet"] or "E007F" in body["framing"]


def test_invisible_ink_bits_per_carrier_is_eight(store):
    """Payload IS ASCII: 1 tag codepoint = 1 payload byte."""
    assert _body(store, "text-invisible-ink")["bits_per_carrier_unit"] == 8


def test_confusable_carries_2_bits_per_space(store):
    """Four whitespace variants → 2 bits per ASCII space carrier."""
    assert _body(store, "text-confusable")["bits_per_carrier_unit"] == 2


def test_braille_has_no_length_prefix(store):
    """braille appends the whole payload as an unbounded block — no prefix."""
    body = _body(store, "text-braille")
    assert body["prefix_scheme"] == "none — payload as an appended block"


def test_braille_maps_byte_to_u2800_plus_byte(store):
    body = _body(store, "text-braille")
    assert "U+2800" in body["alphabet"]


def test_emoji_substitution_is_red_and_blue(store):
    body = _body(store, "text-emoji-substitution")
    assert "1F534" in body["alphabet"]  # 🔴
    assert "1F535" in body["alphabet"]  # 🔵


def test_skintone_carries_2_bits_per_emoji(store):
    """Four skin-tone modifiers → 2 bits."""
    body = _body(store, "emoji-skintone")
    assert body["bits_per_carrier_unit"] == 2
    assert "1F3FB" in body["alphabet"] and "1F3FE" in body["alphabet"]


def test_capitalization_lives_at_semantic_layer(store):
    """Not a Unicode-level trick — payload lives in which words are capitalized."""
    rec = store.get("text-capitalization")
    assert rec["layer"] == "semantic"


def test_mathbold_dies_to_nfkc(store):
    body = _body(store, "text-mathbold")
    assert "NFKC" in body["normalization_risk"]


# --- image techniques: numbers and semantics -----------------------------------


def test_image_lsb_supports_randomized_strategy(store):
    """ST3GG's stealth default uses randomized traversal."""
    body = _body(store, "image-lsb")
    assert "randomized" in body["strategy"]


def test_image_lsb_supports_9_channel_presets(store):
    """R | G | B | A | RG | RB | GB | RGB | RGBA."""
    body = _body(store, "image-lsb")
    presets = body["channels"]
    for p in ("R", "G", "B", "A", "RG", "RB", "GB", "RGB", "RGBA"):
        assert p in presets, f"channel preset {p} missing from technique record"


def test_image_lsb_uses_st3gg_v3_header(store):
    """The password-derived-magic + AES-GCM header format."""
    body = _body(store, "image-lsb")
    assert "ST3GG v3" in body["header_format"] or "v3" in body["header_format"]


def test_image_lsb_capacity_formula_multiplies_wh_bpc_channels(store):
    """W * H * bits_per_channel * len(channels) / 8."""
    body = _body(store, "image-lsb")
    formula = body["capacity_formula"]
    assert "W" in formula and "H" in formula
    assert "bits_per_channel" in formula
    assert "channels" in formula
    assert "8" in formula


def test_f5_uses_matrix_encoding(store):
    """F5's defining feature: matrix encoding with parameter k."""
    body = _body(store, "image-f5")
    assert "matrix" in body["capacity_formula"].lower()
    assert "k" in body["capacity_formula"]


def test_f5_handles_shrinkage(store):
    """F5's other defining feature: shrinkage handling for coefficients decremented to zero."""
    body = _body(store, "image-f5")
    assert "shrinkage_handling" in body
    assert body["shrinkage_handling"]


def test_jsteg_is_lsb_over_nonzero_ac_coefs(store):
    """jsteg's whole thing: LSB replacement on nonzero DCT AC coefficients."""
    body = _body(store, "image-jsteg")
    formula = body["capacity_formula"]
    assert "nonzero" in formula.lower() and "coefficient" in formula.lower()


def test_dct_capacity_is_one_bit_per_64_pixels(store):
    """8×8 DCT block = 64 pixels → ~1 bit per block per AC coef."""
    body = _body(store, "image-dct")
    assert "64" in body["capacity_formula"]


def test_dct_has_three_robustness_levels(store):
    """low | medium | high — the robustness knob mentioned in the field guide."""
    body = _body(store, "image-dct")
    assert "low" in body["robustness"]
    assert "medium" in body["robustness"]
    assert "high" in body["robustness"]


def test_pvd_supports_horizontal_and_vertical(store):
    body = _body(store, "image-pvd")
    assert "horizontal" in body["direction"]
    assert "vertical" in body["direction"]


def test_png_private_chunk_uses_second_letter_lowercase(store):
    """PNG's ancillary/private convention: second letter lowercase = private."""
    body = _body(store, "image-png-private-chunk")
    assert "lowercase" in body["naming_convention"]
    assert "4-char" in body["naming_convention"]


def test_png_text_chunk_supports_three_types(store):
    body = _body(store, "image-png-text-chunk")
    types = body["chunk_types"]
    for chunk in ("tEXt", "zTXt", "iTXt"):
        assert any(chunk in t for t in types), f"{chunk} missing"


def test_matryoshka_lives_at_bit_layer(store):
    """Recursive nesting inherits LSB byte-identity per level."""
    rec = store.get("image-matryoshka")
    assert rec["layer"] == "bit"


# --- carrier formats -----------------------------------------------------------


def test_png_magic_bytes_are_correct(store):
    """The 8-byte PNG signature: \\x89PNG\\r\\n\\x1a\\n."""
    body = _body(store, "fmt-png")
    assert body["magic_bytes"] == "89 50 4E 47 0D 0A 1A 0A"


def test_png_end_marker_is_iend_chunk(store):
    body = _body(store, "fmt-png")
    assert "IEND" in body["end_marker"]


def test_png_critical_chunks_are_four(store):
    """IHDR, PLTE, IDAT, IEND — RFC 2083."""
    body = _body(store, "fmt-png")
    critical = set(body["critical_chunks"])
    assert critical == {"IHDR", "PLTE", "IDAT", "IEND"}


def test_jpeg_magic_starts_with_ffd8ff(store):
    body = _body(store, "fmt-jpeg")
    assert "FF D8 FF" in body["magic_bytes"]


def test_jpeg_end_marker_is_ffd9(store):
    """EOI marker."""
    body = _body(store, "fmt-jpeg")
    assert "FF D9" in body["end_marker"]


def test_jpeg_dct_targets_ac_not_dc(store):
    """DC coefficients are too perceptually loaded — F5/jsteg both use AC."""
    body = _body(store, "fmt-jpeg")
    assert "AC" in body["dct_targets_for_stego"]
    assert "DC" not in body["dct_targets_for_stego"].split(" DC ")[0] or "not DC" in body["dct_targets_for_stego"] or "DC coefficients are too" in body["dct_targets_for_stego"]


def test_gif_end_marker_is_3b(store):
    body = _body(store, "fmt-gif")
    assert "3B" in body["end_marker"]


def test_utf8_names_the_four_zero_width_codepoints(store):
    """ZWSP, ZWNJ, ZWJ, BOM — the four canonical zero-width chars."""
    body = _body(store, "fmt-utf8-text")
    targets = " ".join(body["steg_targets"])
    for cp in ("U+200B", "U+200C", "U+200D", "U+FEFF"):
        assert cp in targets, f"{cp} missing from utf8 steg_targets"


# --- transports: canonical layers ---------------------------------------------


def test_slack_upload_canonical_layer_is_file_bytes(store):
    """Slack upload is a file-bytes-canonical channel — bytes survive if
    the strip/re-encode list doesn't touch them."""
    body = _body(store, "transport-slack-upload")
    assert body["canonical_layer"] == "file-bytes"


def test_slack_paste_canonical_layer_is_rendered_post(store):
    body = _body(store, "transport-slack-paste")
    assert body["canonical_layer"] == "rendered-post"


def test_slack_snippet_canonical_layer_is_file_bytes(store):
    """The whole point of slack_snippet: raw bytes, not rendered."""
    body = _body(store, "transport-slack-snippet")
    assert body["canonical_layer"] == "file-bytes"


def test_slack_upload_strips_named_text_chunks(store):
    body = _body(store, "transport-slack-upload")
    strips = " ".join(body["known_strips"])
    for chunk in ("tEXt", "iTXt", "zTXt"):
        assert chunk in strips, f"{chunk} missing from Slack upload strip list"


def test_slack_upload_strips_jpeg_metadata(store):
    body = _body(store, "transport-slack-upload")
    strips = " ".join(body["known_strips"])
    assert "EXIF" in strips
    assert "XMP" in strips
    assert "IPTC" in strips


def test_slack_upload_recodes_jpeg_webp_tiff(store):
    body = _body(store, "transport-slack-upload")
    recodes = " ".join(body["known_recodes"])
    assert "JPEG" in recodes
    assert "WebP" in recodes
    assert "TIFF" in recodes


def test_slack_paste_length_cap_is_4000(store):
    body = _body(store, "transport-slack-paste")
    assert "4000" in body["length_cap"]


def test_slack_paste_retrieval_gotcha_warns_against_text_field(store):
    """The .text field is colon-form and length-capped — walk blocks[] instead."""
    body = _body(store, "transport-slack-paste")
    assert ".text" in body["retrieval_gotcha"]
    assert "colon-form" in body["retrieval_gotcha"]


def test_whatsapp_photo_is_perceptual_approximation(store):
    """WhatsApp photo mode kills LSB; canonical layer is perceptual."""
    body = _body(store, "transport-whatsapp-photo")
    assert body["canonical_layer"] == "perceptual-approximation"


def test_terminal_stdout_kills_zero_width(store):
    body = _body(store, "transport-terminal-stdout")
    strips = " ".join(body["known_strips"])
    assert "zero-width" in strips.lower()


def test_pbcopy_preserves_bytes(store):
    """The whole point of pbcopy/xclip: byte-preserving clipboard."""
    body = _body(store, "transport-pbcopy")
    assert body["canonical_layer"] == "file-bytes"
    assert body["known_strips"] == []
    assert body["known_recodes"] == []


def test_http_raw_is_the_baseline(store):
    body = _body(store, "transport-http-raw")
    assert body["canonical_layer"] == "file-bytes"
    assert body["known_strips"] == []
    assert body["known_recodes"] == []


# --- survival cells: exact verdicts from the 2026-07 Slack probe --------------


def test_survival_png_lsb_survives_slack_upload(store):
    body = _body(store, "sv-lsb-slack-upload")
    assert body["status"].startswith("✅")
    assert body["technique_id"] == "image-lsb"
    assert body["transport_id"] == "transport-slack-upload"


def test_survival_lsb_slack_covers_all_six_variants(store):
    """The probe tested 6 PNG LSB variants; the survival record must name them."""
    body = _body(store, "sv-lsb-slack-upload")
    assert body["cells_tested"] == 6


def test_survival_png_text_chunks_stripped_by_slack(store):
    """The named-text-chunk strip — a load-bearing fact for slack_upload advice."""
    body = _body(store, "sv-png-textchunk-slack-upload")
    assert body["status"].startswith("❌")


def test_survival_png_private_chunk_survives_slack(store):
    """The reason we recommend private chunks over named ones on Slack."""
    body = _body(store, "sv-png-private-chunk-slack-upload")
    assert body["status"].startswith("✅")
    assert "caveat" in body  # fragile-but-working


def test_survival_f5_dies_on_slack(store):
    body = _body(store, "sv-f5-slack-upload")
    assert body["status"].startswith("❌")


def test_survival_jsteg_dies_on_slack(store):
    body = _body(store, "sv-jsteg-slack-upload")
    assert body["status"].startswith("❌")


def test_survival_dct_is_tuned_only_on_slack(store):
    """Generic DCT survives Slack but only when sized to match the re-encoder."""
    body = _body(store, "sv-dct-slack-upload")
    assert body["status"].startswith("⚠") or "tuned" in body["status"]


def test_survival_matryoshka_inherits_lsb_survival(store):
    body = _body(store, "sv-matryoshka-slack-upload")
    assert body["status"].startswith("✅")


def test_survival_whitespace_dies_on_slack_paste(store):
    body = _body(store, "sv-whitespace-slack-paste")
    assert body["status"].startswith("❌") or "recoded" in body["status"].lower()


def test_survival_whitespace_survives_slack_snippet(store):
    """The paste-vs-snippet contrast for whitespace steg."""
    body = _body(store, "sv-whitespace-slack-snippet")
    assert body["status"].startswith("✅")


def test_survival_invisible_ink_dies_on_slack_paste(store):
    body = _body(store, "sv-invisible-ink-slack-paste")
    assert body["status"].startswith("❌") or "recoded" in body["status"].lower()


def test_survival_invisible_ink_survives_slack_snippet(store):
    body = _body(store, "sv-invisible-ink-slack-snippet")
    assert body["status"].startswith("✅")


def test_survival_emoji_tag_stripped_on_slack_paste(store):
    """Slack canonicalizes to :colon_form: — tag chars die."""
    body = _body(store, "sv-emoji-tag-slack-paste")
    assert body["status"].startswith("❌")


def test_survival_skintone_paste_is_colon_form_lossy(store):
    """Skintone bits survive in blocks[] but die if consumer reads .text."""
    body = _body(store, "sv-skintone-slack-paste")
    assert "colon-form" in body["status"] or body["status"].startswith("⚠")


def test_survival_lsb_dies_on_whatsapp_photo(store):
    body = _body(store, "sv-lsb-whatsapp-photo")
    assert body["status"].startswith("❌")
    assert "document" in body["workaround"]


# --- layers --------------------------------------------------------------------


def test_bit_layer_dies_to_lossy_reencode(store):
    body = _body(store, "layer-bit")
    dies = " ".join(body["dies_to"])
    assert "JPEG" in dies or "lossy" in dies


def test_coefficient_layer_survives_matching_quantization(store):
    body = _body(store, "layer-coefficient")
    survives = " ".join(body["survives"])
    assert "quantization" in survives.lower()


def test_character_layer_dies_to_nfkc(store):
    body = _body(store, "layer-character")
    dies = " ".join(body["dies_to"])
    assert "NFKC" in dies


def test_container_layer_survives_byte_identical_transfer(store):
    body = _body(store, "layer-container")
    survives = " ".join(body["survives"])
    assert "byte-identical" in survives.lower()


# --- detectors -----------------------------------------------------------------


def test_chi_square_works_on_lsb(store):
    body = _body(store, "det-chi-square")
    assert body["probe_type"] == "statistical"
    works = " ".join(body["works_on"]).lower()
    assert "lsb" in works


def test_rs_estimates_embedding_rate(store):
    """RS gives an estimated p, not a yes/no."""
    body = _body(store, "det-rs")
    assert "rate" in body["output_semantics"].lower()


def test_spa_and_rs_have_different_failure_modes(store):
    """The reason to run both — mismatch is itself a signal."""
    body = _body(store, "det-spa")
    assert "RS" in body["false_positive_notes"] or "different" in body["false_positive_notes"]


def test_f5_signature_scan_false_fires_on_png(store):
    body = _body(store, "det-f5-signature")
    assert "PNG" in body["false_positive_notes"]


# --- signatures / signal diagnosis ---------------------------------------------


def test_decreasing_rgb_signature_is_sequential_lsb(store):
    """The classic 'payload consumed R, spilled into G, tapered in B' pattern."""
    body = _body(store, "sig-decreasing-rgb")
    assert "sequential" in body["probable_technique"]
    assert body["strength"] == "strong"


def test_decreasing_rgb_signature_carries_python_snippet(store):
    """The signal-diagnosis records carry runnable code, not just prose."""
    body = _body(store, "sig-decreasing-rgb")
    assert "python_snippet" in body
    assert "Image.open" in body["python_snippet"]


def test_multiple_bit_planes_signature_indicates_multi_bpc(store):
    body = _body(store, "sig-multiple-bit-planes")
    assert "2 bpc" in body["probable_technique"] or "4 bpc" in body["probable_technique"]


def test_low_entropy_signature_indicates_uncompressed_ascii(store):
    """Entropy ~2-4 on the suspicious plane → English ASCII, no compression."""
    body = _body(store, "sig-low-plane-entropy-ascii")
    assert body["strength"] == "strong"
    assert "ASCII" in body["probable_technique"]


def test_high_entropy_signature_indicates_encrypted_or_compressed(store):
    """Entropy ~7.9-8.0 → ciphertext or gzip."""
    body = _body(store, "sig-high-plane-entropy-encrypted")
    assert "compressed" in body["probable_technique"] or "encrypted" in body["probable_technique"]


def test_alpha_all_ones_is_not_a_payload(store):
    """The most common false-positive: opaque source, not ciphertext."""
    body = _body(store, "sig-alpha-all-ones")
    assert "NOT a payload" in body["probable_technique"] or "fingerprint" in body["probable_technique"]


def test_f5_hit_on_png_is_weak_signal(store):
    """False positive — F5 is a JPEG tool."""
    body = _body(store, "sig-f5-hit-on-png")
    assert body["strength"] == "weak"


def test_direct_pixel_overwrite_has_snippet(store):
    body = _body(store, "sig-direct-pixel-overwrite")
    assert "python_snippet" in body


# --- myths: verdict + correct_form -------------------------------------------


def test_myth_lsb_jpeg_verdict_is_false(store):
    body = _body(store, "myth-lsb-survives-jpeg")
    assert body["verdict"] == "false"
    assert "Q99" in body["correct_form"] or "Q=99" in body["correct_form"]


def test_myth_homoglyph_nfkc_verdict_is_false(store):
    body = _body(store, "myth-homoglyph-nfkc")
    assert body["verdict"] == "false"
    assert "NFKC" in body["correct_form"]


def test_myth_zero_width_needs_qualification(store):
    """Zero-width isn't 'invisible everywhere' — terminal glyph filter."""
    body = _body(store, "myth-zero-width-invisible-everywhere")
    assert body["verdict"] == "needs_qualification"


def test_myth_slack_metadata_false(store):
    body = _body(store, "myth-slack-preserves-metadata")
    assert body["verdict"] == "false"
    assert "private chunk" in body["correct_form"].lower()


def test_myth_steghide_outguess_false(store):
    body = _body(store, "myth-steghide-reads-outguess")
    assert body["verdict"] == "false"


def test_every_myth_carries_match_patterns(store):
    """Every myth's technical_body has match_patterns for stegg_verify_claim."""
    for m in store.in_category("myth"):
        body = m.get("technical_body", {})
        assert body.get("match_patterns"), f"{m['id']}: no match_patterns"
        assert isinstance(body["match_patterns"], list)


# --- bibliography spot-checks -------------------------------------------------


def test_bibliography_westfeld_2001_is_f5_paper(store):
    rec = store.get("westfeld-2001-f5")
    assert "F5" in rec["notes"] or "F5" in rec["title"]
    assert rec["confidence"] == "primary"


def test_bibliography_fridrich_2001_is_rs_paper(store):
    rec = store.get("fridrich-2001-rs")
    assert "RS" in rec["notes"] or "RS" in rec["aliases"]
    assert rec["year"] == 2001


def test_bibliography_dumitrescu_2003_is_spa_paper(store):
    rec = store.get("dumitrescu-2003-spa")
    assert "sample" in rec["notes"].lower() or "SPA" in rec["notes"]


def test_bibliography_westfeld_pfitzmann_1999_is_chi_square(store):
    rec = store.get("westfeld-pfitzmann-1999-chi2")
    assert "chi-square" in rec["notes"].lower() or "chi-square" in " ".join(rec["aliases"])


def test_bibliography_simmons_1983_is_prisoners_problem(store):
    rec = store.get("simmons-1983-prisoners")
    assert "Prisoners" in rec["name"] or "Prisoners" in rec["notes"]


def test_bibliography_albertini_is_polyglot_catalog(store):
    rec = store.get("albertini-polyglots")
    assert "polyglot" in rec["notes"].lower()


def test_bibliography_2024_tag_injection_is_community(store):
    """The 2024 hidden-prompt-injection wave is community-attested, not primary lit."""
    rec = store.get("greenberg-2024-tag-injection")
    assert rec["confidence"] == "community"


def test_bibliography_slack_probe_is_dated_2026_07_26(store):
    """The Slack probe evidence file has a specific test date."""
    rec = store.get("st3gg-transport-results-slack")
    assert rec["era_bounds"] == ["2026-07-26", "2026-07-26"]
