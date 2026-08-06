"""Knowledge-retrieval tools: typed records + prose corpus.

The retrieval surface described in `plan-knowledge-base.md`, backed by
the record store in `st3ggmcp.records` and the prose corpus under
`knowledge/*/`. Names mirror PHR34CKER5 for cross-repo consistency:

    stegg_lookup_technique      -> full technique record + envelope
    stegg_verify_survival       -> (technique, transport) status + evidence
    stegg_verify_claim          -> grade a natural-language claim vs myths.json
    stegg_explain_pipeline      -> ordered technique records for a goal
    stegg_bibliography          -> resolve or list bibliography entries
    stegg_cross_reference       -> traverse see_also links
    stegg_search_records        -> filter records by category/family/layer/etc.
    stegg_list_topics           -> list prose corpus topics/files
    stegg_read_lore             -> read a prose file
    stegg_search_lore           -> grep the prose corpus

All results are JSON-shaped and wrapped in the common
{citations, era_bounds, carrier_family, confidence} envelope where
applicable.
"""

from __future__ import annotations

import re
from pathlib import Path

from st3ggmcp import records

from ._common import truncate_json


KNOWLEDGE_ROOT = Path(__file__).resolve().parent.parent.parent / "knowledge"

_RECORD_STORE: records.RecordStore | None = None
_RECORD_STORE_ROOT: Path | None = None


def _record_store() -> records.RecordStore:
    """Lazy-load and cache the record store."""
    global _RECORD_STORE, _RECORD_STORE_ROOT
    root = KNOWLEDGE_ROOT / "records"
    if _RECORD_STORE is None or _RECORD_STORE_ROOT != root:
        _RECORD_STORE = records.RecordStore.load(root)
        _RECORD_STORE_ROOT = root
    return _RECORD_STORE


# ---- lore (prose corpus) helpers -------------------------------------------


def _iter_lore(root: Path) -> list[tuple[str, str, Path]]:
    """(topic, name, path) triples for every .md file under root except MANIFEST."""
    if not root.exists():
        return []
    out: list[tuple[str, str, Path]] = []
    for md in sorted(root.rglob("*.md")):
        if md.name == "MANIFEST.md":
            continue
        rel = md.relative_to(root)
        parts = rel.parts
        if len(parts) == 1:
            topic = "_root"
            name = md.stem
        else:
            topic = parts[0]
            name = "/".join(parts[1:])[:-3]
        if topic == "records":
            continue
        out.append((topic, name, md))
    return out


def _find_lore(root: Path, topic: str, name: str) -> Path | None:
    for t, n, p in _iter_lore(root):
        if t == topic and n == name:
            return p
    return None


# ---- record tools ----------------------------------------------------------


async def execute_lookup_technique(name: str = "", **_kw) -> str:
    if not name:
        return truncate_json({"error": "name required"})
    store = _record_store()
    rec = store.resolve(name)
    if rec is None or rec.get("category") != "technique":
        ids = [r["id"] for r in store.in_category("technique")]
        return truncate_json({
            "error": f"no technique {name!r}",
            "known_ids": ids,
        })
    out = records.public_view(rec)
    out["envelope"] = records.envelope(rec)
    return truncate_json(out, max_chars=6000)


async def execute_verify_survival(
    technique: str = "",
    transport: str = "",
    **_kw,
) -> str:
    if not technique or not transport:
        return truncate_json({"error": "technique and transport required"})
    store = _record_store()
    trec = store.resolve(technique)
    tport = store.resolve(transport)
    if trec is None:
        return truncate_json({"error": f"no technique {technique!r}"})
    if tport is None:
        return truncate_json({"error": f"no transport {transport!r}"})
    for rec in store.in_category("survival"):
        body = rec.get("technical_body", {}) or {}
        tid = body.get("technique_id")
        pid = body.get("transport_id")
        applies = body.get("applies_to") or []
        if pid != tport["id"]:
            continue
        if tid == trec["id"] or trec["id"] in applies:
            out = {
                "technique_id": trec["id"],
                "transport_id": tport["id"],
                "status": body.get("status"),
                "evidence": body.get("evidence"),
                "tested_at": body.get("tested_at"),
                "caveat": body.get("caveat"),
                "workaround": body.get("workaround"),
                "record_id": rec["id"],
                "envelope": records.envelope(rec),
            }
            return truncate_json(out, max_chars=4000)
    return truncate_json({
        "technique_id": trec["id"],
        "transport_id": tport["id"],
        "status": "❓ untested",
        "note": "No matching survival record. Run a transport probe and add a record to survival.json.",
    })


async def execute_bibliography(cite_id: str | None = None, **_kw) -> str:
    store = _record_store()
    if not cite_id:
        return truncate_json({
            "sources": [records.public_view(r) for r in store.in_category("bibliography")]
        }, max_chars=12000)
    rec = store.get(cite_id) or store.resolve(cite_id)
    if rec is None or rec.get("category") != "bibliography":
        ids = [r["id"] for r in store.in_category("bibliography")]
        return truncate_json({"error": f"no bibliography entry {cite_id!r}", "known_ids": ids})
    return truncate_json(records.public_view(rec))


async def execute_cross_reference(record_id: str = "", **_kw) -> str:
    if not record_id:
        return truncate_json({"error": "record_id required"})
    store = _record_store()
    rec = store.get(record_id) or store.resolve(record_id)
    if rec is None:
        return truncate_json({"error": f"no record {record_id!r}"})
    linked = []
    for ref in rec.get("see_also", []):
        target = store.get(ref) or store.resolve(ref)
        if target is None:
            linked.append({"id": ref, "resolved": False})
        else:
            linked.append({
                "id": target["id"],
                "name": target.get("name"),
                "category": target.get("category"),
                "resolved": True,
            })
    return truncate_json({"id": rec["id"], "name": rec.get("name"), "see_also": linked})


async def execute_verify_claim(text: str = "", **_kw) -> str:
    if not text:
        return truncate_json({"error": "text required"})
    store = _record_store()
    lowered = text.lower()
    myths = store.in_category("myth")
    # Rule-based: pattern-match each myth's `aliases` + `technical_body.claim`.
    hits = []
    for m in myths:
        body = m.get("technical_body", {}) or {}
        patterns = body.get("match_patterns") or []
        if not patterns:
            # fallback: extract keywords from the claim text
            patterns = _claim_keywords((body.get("claim") or "").lower())
        if not patterns:
            continue
        try:
            if all(re.search(p, lowered) for p in patterns):
                hits.append(m)
        except re.error:
            continue
    if hits:
        best = hits[0]
        body = best.get("technical_body", {}) or {}
        return truncate_json({
            "claim": text,
            "verdict": body.get("verdict", "false"),
            "reasoning": body.get("correct_form"),
            "record_id": best["id"],
            "citations": best.get("citations", []),
            "see_also": best.get("see_also", []),
        }, max_chars=4000)
    return truncate_json({
        "claim": text,
        "verdict": "unverified",
        "reasoning": (
            "No matching myth or record. This tool asserts verdicts only when it has "
            "a record; use stegg_lookup_technique / stegg_verify_survival / "
            "stegg_search_records to research manually."
        ),
    })


def _claim_keywords(claim: str) -> list[str]:
    """Extract 1-3 discriminating keywords from a myth's claim text.

    Trivial extractor: pick multi-char tokens that aren't stopwords. Good enough
    for the current myth set; expand as the KR grows.
    """
    stop = {
        "the", "a", "an", "and", "or", "of", "to", "in", "on", "at", "by",
        "for", "is", "are", "was", "were", "be", "been", "being", "with",
        "as", "that", "this", "these", "those", "not", "no", "does", "do",
        "did", "it", "its", "any", "every", "some", "all", "even", "over",
        "into", "from", "than", "then", "than", "so", "there", "their",
        "them", "they", "their", "your", "you",
    }
    tokens = re.findall(r"[a-z][a-z0-9_\-]{2,}", claim)
    keys: list[str] = []
    for tok in tokens:
        if tok in stop:
            continue
        keys.append(re.escape(tok))
        if len(keys) >= 3:
            break
    return keys


async def execute_explain_pipeline(
    goal: str = "",
    carrier: str | None = None,
    transport: str | None = None,
    constraint: str | None = None,
    **_kw,
) -> str:
    """Return an ordered list of technique records that fit the goal.

    Filter: `carrier` matches carrier_family, `transport` restricts survival
    to status ∈ {✅, ⚠} on that transport, `constraint` filters stealth_class
    (`invisible` / `prose-like` / `visibly-perturbed`).
    """
    store = _record_store()
    techs = store.in_category("technique")

    # 1. carrier filter
    if carrier:
        norm = records._normalize(carrier)
        techs = [t for t in techs if records._normalize(t.get("carrier_family", "")) == norm]

    # 2. constraint (stealth_class) filter
    if constraint:
        norm = records._normalize(constraint)
        techs = [
            t for t in techs
            if records._normalize((t.get("technical_body") or {}).get("stealth_class", "")) == norm
        ]

    # 3. transport filter via survival records
    if transport:
        tport = store.resolve(transport)
        if tport is None:
            return truncate_json({"error": f"no transport {transport!r}", "goal": goal})
        surviving_ids: set[str] = set()
        for rec in store.in_category("survival"):
            body = rec.get("technical_body", {}) or {}
            if body.get("transport_id") != tport["id"]:
                continue
            status = str(body.get("status", ""))
            if not status.startswith(("✅", "⚠")):
                continue
            surviving_ids.add(body.get("technique_id", ""))
            for aid in body.get("applies_to", []) or []:
                surviving_ids.add(aid)
        techs = [t for t in techs if t["id"] in surviving_ids]

    steps = [
        {
            "step": i + 1,
            "technique_id": t["id"],
            "name": t.get("name"),
            "why": _brief_why(t, carrier, transport, constraint),
            "capacity_formula": (t.get("technical_body") or {}).get("capacity_formula"),
            "stealth_class": (t.get("technical_body") or {}).get("stealth_class"),
            "citations": t.get("citations", []),
        }
        for i, t in enumerate(techs[:8])
    ]

    return truncate_json({
        "goal": goal,
        "filters": {"carrier": carrier, "transport": transport, "constraint": constraint},
        "candidates": len(techs),
        "steps": steps,
        "note": (
            "Multiple viable answers is a valid answer. Steps are ranked by the record "
            "order in techniques.json; refine with more specific constraints as needed."
        ),
    }, max_chars=6000)


def _brief_why(rec: dict, carrier, transport, constraint) -> str:
    body = rec.get("technical_body") or {}
    parts = []
    if carrier:
        parts.append(f"carrier_family={rec.get('carrier_family')}")
    if transport:
        parts.append(f"survives {transport}")
    if constraint:
        parts.append(f"stealth_class={body.get('stealth_class')}")
    if not parts:
        parts.append(f"layer={rec.get('layer')}")
    return "; ".join(parts)


async def execute_search_records(
    query: str | None = None,
    category: str | None = None,
    carrier_family: str | None = None,
    layer: str | None = None,
    transport: str | None = None,
    max_results: int = 20,
    **_kw,
) -> str:
    store = _record_store()
    q = records._normalize(query) if query else None
    cf = records._normalize(carrier_family) if carrier_family else None
    ly = records._normalize(layer) if layer else None

    results = []
    surviving_ids: set[str] | None = None
    if transport:
        tport = store.resolve(transport)
        if tport is None:
            return truncate_json({"error": f"no transport {transport!r}"})
        surviving_ids = set()
        for rec in store.in_category("survival"):
            body = rec.get("technical_body", {}) or {}
            if body.get("transport_id") != tport["id"]:
                continue
            status = str(body.get("status", ""))
            if not status.startswith(("✅", "⚠")):
                continue
            surviving_ids.add(body.get("technique_id", ""))
            for aid in body.get("applies_to", []) or []:
                surviving_ids.add(aid)

    for rec in store.all_records():
        if category and rec.get("category") != category:
            continue
        if cf and records._normalize(rec.get("carrier_family", "")) != cf:
            continue
        if ly and records._normalize(rec.get("layer", "")) != ly:
            continue
        if surviving_ids is not None and rec.get("category") == "technique" and rec["id"] not in surviving_ids:
            continue
        if q:
            haystack = records._normalize(
                " ".join([rec.get("id", ""), rec.get("name", ""), *rec.get("aliases", [])])
            )
            if q not in haystack:
                continue
        results.append({
            "id": rec["id"],
            "name": rec.get("name"),
            "category": rec.get("category"),
            "carrier_family": rec.get("carrier_family"),
            "layer": rec.get("layer"),
            **records.envelope(rec),
        })

    return truncate_json({
        "filters": {
            "query": query, "category": category, "carrier_family": carrier_family,
            "layer": layer, "transport": transport,
        },
        "hit_count": len(results),
        "results": results[:max_results],
    }, max_chars=6000)


# ---- lore (prose) tools ----------------------------------------------------


async def execute_list_topics(**_kw) -> str:
    lore = _iter_lore(KNOWLEDGE_ROOT)
    topics: dict[str, list[str]] = {}
    for topic, name, _path in lore:
        topics.setdefault(topic, []).append(name)
    return truncate_json({
        "root": str(KNOWLEDGE_ROOT),
        "topic_count": len(topics),
        "file_count": len(lore),
        "topics": topics,
    }, max_chars=4000)


async def execute_read_lore(topic: str = "", name: str = "", **_kw) -> str:
    if not topic or not name:
        return truncate_json({"error": "topic and name required"})
    p = _find_lore(KNOWLEDGE_ROOT, topic, name)
    if p is None:
        return truncate_json({
            "error": f"no lore for {topic}/{name}",
            "hint": "call stegg_list_topics",
        })
    try:
        return p.read_text(encoding="utf-8")
    except Exception as exc:
        return truncate_json({"error": f"read failed: {exc}"})


async def execute_search_lore(query: str = "", max_results: int = 20, **_kw) -> str:
    if not query:
        return truncate_json({"error": "query required"})
    try:
        pattern = re.compile(query, re.IGNORECASE)
    except re.error:
        pattern = re.compile(re.escape(query), re.IGNORECASE)

    hits = []
    for topic, name, path in _iter_lore(KNOWLEDGE_ROOT):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        matching = [ln for ln in text.splitlines() if pattern.search(ln)]
        if not matching:
            continue
        hits.append({
            "topic": topic,
            "name": name,
            "uri": f"stegg://{topic}/{name}",
            "match_count": len(matching),
            "first_match": matching[0].strip()[:240],
        })
    hits.sort(key=lambda h: h["match_count"], reverse=True)
    return truncate_json({
        "query": query,
        "hit_count": len(hits),
        "results": hits[:max_results],
    }, max_chars=4000)


# ---- registry --------------------------------------------------------------


EXECUTORS = {
    "stegg_lookup_technique": execute_lookup_technique,
    "stegg_verify_survival":  execute_verify_survival,
    "stegg_bibliography":     execute_bibliography,
    "stegg_cross_reference":  execute_cross_reference,
    "stegg_verify_claim":     execute_verify_claim,
    "stegg_explain_pipeline": execute_explain_pipeline,
    "stegg_search_records":   execute_search_records,
    "stegg_list_topics":      execute_list_topics,
    "stegg_read_lore":        execute_read_lore,
    "stegg_search_lore":      execute_search_lore,
}


SCHEMAS = {
    "stegg_lookup_technique": {
        "description": (
            "Look up a technique record by id, name, or alias. Returns the full "
            "technical_body (bits per carrier unit, framing, prefix scheme, "
            "capacity formula, stealth class) plus the common envelope "
            "(citations, era_bounds, carrier_family, confidence). This is the "
            "'numbers not adjectives' tool — use it before answering 'how does "
            "X work' from memory."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Technique id, name, or alias (e.g. 'f5', 'cyrillic_homoglyph', 'image-lsb')."},
            },
            "required": ["name"],
        },
    },
    "stegg_verify_survival": {
        "description": (
            "Given a (technique, transport) pair, return the survival status "
            "(✅ / ❌ / ⚠ / ❓), the evidence pointer, tested_at date, and any "
            "caveats or workarounds. Backed by survival.json records. Use "
            "before recommending a technique for a stated transport."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "technique": {"type": "string", "description": "Technique id/name/alias."},
                "transport": {"type": "string", "description": "Transport id/name/alias (e.g. 'slack_upload', 'transport-slack-paste')."},
            },
            "required": ["technique", "transport"],
        },
    },
    "stegg_bibliography": {
        "description": (
            "Resolve a bibliography entry by id, or list every source when "
            "called without arguments. Every non-bibliography record cites "
            "into this table; if a claim can't be traced to one of these "
            "entries, the record is invalid."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "cite_id": {"type": "string", "description": "Bibliography id (e.g. 'westfeld-2001-f5'). Omit to list all sources."},
            },
        },
    },
    "stegg_cross_reference": {
        "description": (
            "Traverse a record's see_also links, returning the linked "
            "records' id/name/category. The typed-record analogue of the "
            "prose corpus's [[topic/name]] links."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "record_id": {"type": "string", "description": "Record id or resolvable alias."},
            },
            "required": ["record_id"],
        },
    },
    "stegg_verify_claim": {
        "description": (
            "Grade a natural-language claim as `false` / `needs_qualification` "
            "/ `unverified` against myths.json. A conservative rule-based "
            "checker: an unmatched claim returns `unverified` rather than "
            "guessing. Better to say 'I can't confirm that from the KR' than "
            "to bluff."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The claim to grade, in natural language."},
            },
            "required": ["text"],
        },
    },
    "stegg_explain_pipeline": {
        "description": (
            "Return an ordered list of technique records that fit a goal. "
            "Filters by carrier_family, transport (uses survival.json to "
            "keep only ✅/⚠ techniques), and constraint (stealth_class). "
            "The pipeline-design tool: 'survive Slack paste, 800 bytes, "
            "prose-looking' returns cyrillic_homoglyph / cjk_homoglyph / "
            "capitalization with citations."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "goal": {"type": "string", "description": "Free-text goal description (echoed back)."},
                "carrier": {"type": "string", "description": "carrier_family filter (image | text | emoji | audio | network | document | universal)."},
                "transport": {"type": "string", "description": "Transport id/alias; restricts results to techniques that survive it."},
                "constraint": {"type": "string", "description": "stealth_class filter (invisible | prose-like | visibly-perturbed)."},
            },
        },
    },
    "stegg_search_records": {
        "description": (
            "Search the typed records with category / carrier_family / layer / "
            "transport filters. Where stegg_search_lore greps prose, this "
            "scopes the KR. Each result carries the common envelope."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Substring match on id/name/aliases."},
                "category": {"type": "string", "description": "technique | transport | survival | detector | signature | myth | carrier_format | layer | bibliography."},
                "carrier_family": {"type": "string", "description": "image | text | emoji | audio | network | document | universal."},
                "layer": {"type": "string", "description": "bit | coefficient | character | container | semantic | universal."},
                "transport": {"type": "string", "description": "If set, only return techniques whose survival on that transport is ✅ or ⚠."},
                "max_results": {"type": "integer", "description": "Cap on returned entries (default 20)."},
            },
        },
    },
    "stegg_list_topics": {
        "description": (
            "List every topic in the prose corpus (`knowledge/<topic>/`) and "
            "the markdown files under each. File contents are readable via "
            "stegg_read_lore or as MCP resources at stegg://<topic>/<name>."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    "stegg_read_lore": {
        "description": (
            "Read a single prose file from the corpus. Same content as the "
            "stegg://<topic>/<name> MCP resource."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Topic directory (e.g. 'image', 'text', 'transport')."},
                "name": {"type": "string", "description": "File name without .md."},
            },
            "required": ["topic", "name"],
        },
    },
    "stegg_search_lore": {
        "description": (
            "Search the prose corpus for a term (case-insensitive substring / "
            "regex). Returns per-file hit counts and the first matching line. "
            "For record queries (numbers, cited facts), prefer "
            "stegg_search_records."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search term or regex."},
                "max_results": {"type": "integer", "description": "Cap on returned files (default 20)."},
            },
            "required": ["query"],
        },
    },
}
