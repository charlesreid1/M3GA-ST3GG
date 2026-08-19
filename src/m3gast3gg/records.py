"""
Typed-record knowledge repository (the KR layer) for ST3GG.

Loads the JSON records under `knowledge/records/` — the typed, dated, cited
facts that back ST3GG's knowledge-retrieval tools (`stegg_lookup_technique`,
`stegg_verify_survival`, `stegg_bibliography`, `stegg_verify_claim`, …).
Where the prose corpus is what the assistant *reads*, this is what it
*looks facts up in*: numbers, not adjectives.

Discipline:
  * every record is typed, dated (`era_bounds`), and family-bound;
  * `citations[]` is non-empty and resolves into `bibliography.json`;
  * disputes are carried in `disputed{}`, never silently resolved.

Loading is eager, cached, and network-free. Empty citations or unresolved
bibliography refs raise `RecordError` at load time — the server cannot
boot with a broken KR.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

RECORD_FILES = (
    "bibliography",
    "techniques",
    "carrier_formats",
    "layers",
    "transports",
    "survival",
    "detectors",
    "signatures",
    "capacity_models",
    "external_tools",
    "ctf_genres",
    "myths",
)

# Envelope fields every retrieval-tool response carries so callers can weight
# their answer.
ENVELOPE_FIELDS = ("citations", "era_bounds", "carrier_family", "confidence")


class RecordError(RuntimeError):
    """Raised when the record set violates the load-time contract."""


@dataclass
class RecordStore:
    root: Path
    records: dict = field(default_factory=dict)          # id -> record
    by_category: dict = field(default_factory=dict)      # category -> [ids]
    alias_index: dict = field(default_factory=dict)      # normalized alias/name -> id

    @classmethod
    def load(cls, records_dir: Path, *, strict: bool = True) -> "RecordStore":
        store = cls(root=records_dir)
        for stem in RECORD_FILES:
            path = records_dir / f"{stem}.json"
            if not path.exists():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as e:
                raise RecordError(f"{path}: {e}") from e
            if not isinstance(data, list):
                raise RecordError(f"{path}: top-level JSON must be an array of records")
            for rec in data:
                store._add(rec, source=path.name)
        if not store.records:
            raise RecordError(f"no records loaded from {records_dir}")
        if strict:
            store._validate()
        store._build_indexes()
        return store

    def _add(self, rec: dict, source: str) -> None:
        rid = rec.get("id")
        if not rid:
            raise RecordError(f"{source}: record without an id: {rec!r:.120}")
        if rid in self.records:
            raise RecordError(f"duplicate record id {rid!r} (in {source})")
        rec.setdefault("_source", source)
        self.records[rid] = rec

    def _validate(self) -> None:
        bib_ids = {rid for rid, r in self.records.items() if r.get("category") == "bibliography"}
        for rid, rec in self.records.items():
            if rec.get("category") == "bibliography":
                continue
            cites = rec.get("citations") or []
            if not cites:
                raise RecordError(f"{rid}: empty citations[] (every fact must cite a source)")
            for c in cites:
                if c not in bib_ids:
                    raise RecordError(f"{rid}: citation {c!r} does not resolve to a bibliography record")
            if "era_bounds" not in rec:
                raise RecordError(f"{rid}: missing era_bounds")
            eb = rec["era_bounds"]
            if not (isinstance(eb, list) and len(eb) == 2):
                raise RecordError(f"{rid}: era_bounds must be [first, last] (got {eb!r})")

    def _build_indexes(self) -> None:
        self.by_category.clear()
        self.alias_index.clear()
        for rid, rec in self.records.items():
            self.by_category.setdefault(rec.get("category", "_uncategorized"), []).append(rid)
            for key in [rec.get("name", ""), rid, *rec.get("aliases", [])]:
                norm = _normalize(key)
                if norm:
                    self.alias_index.setdefault(norm, rid)

    # ---- queries ----

    def get(self, record_id: str) -> dict | None:
        return self.records.get(record_id)

    def resolve(self, name: str) -> dict | None:
        rec = self.records.get(name)
        if rec:
            return rec
        rid = self.alias_index.get(_normalize(name))
        return self.records.get(rid) if rid else None

    def in_category(self, category: str) -> list[dict]:
        return [self.records[i] for i in self.by_category.get(category, [])]

    def all_records(self) -> list[dict]:
        return list(self.records.values())


def _normalize(s: str) -> str:
    return re.sub(r"[\s_\-]+", " ", str(s).strip().lower())


def public_view(rec: dict) -> dict:
    """A record with internal (_-prefixed) fields stripped, for tool output."""
    return {k: v for k, v in rec.items() if not k.startswith("_")}


def envelope(rec: dict) -> dict:
    """The common {citations, era_bounds, carrier_family, confidence} envelope."""
    return {f: rec.get(f) for f in ENVELOPE_FIELDS}


def _parse_year(value) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    m = re.match(r"^(\d{4})", str(value))
    return int(m.group(1)) if m else None


def era_contains(rec: dict, year: int) -> bool:
    """True if `year` falls within the record's era_bounds (open ends allowed)."""
    eb = rec.get("era_bounds") or [None, None]
    lo = _parse_year(eb[0]) if len(eb) > 0 else None
    hi = _parse_year(eb[1]) if len(eb) > 1 else None
    if lo is not None and year < lo:
        return False
    if hi is not None and year > hi:
        return False
    return True
