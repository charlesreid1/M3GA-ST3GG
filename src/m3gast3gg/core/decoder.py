"""Universal decoder — given a mystery string, try every registered transform.

Walks the transform registry, gates each candidate on its ``detector`` (a
transform with no detector is skipped — the auto-decoder only surfaces
transforms whose alphabets are self-signalling), invokes ``reverse``, and
ranks the results by priority + printability confidence.

Ciphers (Caesar, ROT13, Vigenère, Atbash) have no detector on purpose —
they look like normal letters, and firing on every letter-heavy string
would flood the output. Users who suspect a cipher pass the name
explicitly to ``stegg transform decode``.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List

from .transforms import registry
from .transforms.base import BaseTransformer


@dataclass
class DecodeCandidate:
    method: str
    slug: str
    text: str
    priority: int
    confidence: float
    low_confidence: bool

    def to_dict(self) -> dict:
        return asdict(self)


def universal_decode(
    text: str,
    top_k: int = 5,
    include_low_confidence: bool = True,
) -> List[DecodeCandidate]:
    if not text:
        return []
    if top_k <= 0:
        return []
    candidates: list[DecodeCandidate] = []
    for t in registry.all():
        if not t.can_decode or t.reverse is None:
            continue
        if t.detector is None:
            continue
        try:
            fires = bool(t.detector(text))
        except Exception:
            fires = False
        if not fires:
            continue
        try:
            decoded = t.reverse(text)
        except Exception:
            continue
        if decoded == text or not decoded:
            continue
        conf = _confidence(t, decoded)
        candidates.append(DecodeCandidate(
            method=t.name,
            slug=t.slug,
            text=decoded,
            priority=t.priority,
            confidence=conf,
            low_confidence=(t.priority < 20),
        ))
    candidates.sort(key=lambda c: (-c.priority, -c.confidence, c.slug))
    if not include_low_confidence:
        candidates = [c for c in candidates if not c.low_confidence]
    return candidates[:top_k]


def _confidence(t: BaseTransformer, decoded: str) -> float:
    """Baseline priority / 310, boosted by printability, penalized by replacement chars."""
    base = t.priority / 310.0
    if not decoded:
        return 0.0
    printable = sum(1 for c in decoded if c.isprintable() or c == "\n")
    printable_ratio = printable / len(decoded)
    replacement = decoded.count("�")
    replacement_penalty = min(0.5, replacement / max(1, len(decoded)))
    return max(0.0, min(1.0, base * printable_ratio - replacement_penalty))
