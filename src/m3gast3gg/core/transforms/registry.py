"""Registry — the flat table of every registered ``BaseTransformer``.

Populated once at package import (single-threaded, no lock). Each transform
module calls ``register(t)`` after constructing its ``BaseTransformer``.
Lookups accept either the slug (``"caesar"``) or the human name
(``"Caesar Cipher"``); slugs take precedence.
"""

from __future__ import annotations

from typing import Dict, Iterator, List, Optional

from .base import BaseTransformer


class Registry:
    def __init__(self) -> None:
        self._by_slug: Dict[str, BaseTransformer] = {}
        self._by_name: Dict[str, BaseTransformer] = {}

    def register(self, t: BaseTransformer) -> None:
        if t.map is not None and t.can_decode:
            values = list(t.map.values())
            if len(set(values)) != len(values):
                raise ValueError(
                    f"{t.name}: map is not bijective; supply an explicit reverse"
                )
        if t.slug in self._by_slug:
            raise ValueError(
                f"duplicate transform slug: {t.slug!r} "
                f"(existing name: {self._by_slug[t.slug].name!r})"
            )
        if t.name in self._by_name:
            raise ValueError(f"duplicate transform name: {t.name!r}")
        self._by_slug[t.slug] = t
        self._by_name[t.name] = t

    def get(self, key: str) -> BaseTransformer:
        if key in self._by_slug:
            return self._by_slug[key]
        if key in self._by_name:
            return self._by_name[key]
        raise KeyError(f"no transform registered as {key!r}")

    def get_optional(self, key: str) -> Optional[BaseTransformer]:
        try:
            return self.get(key)
        except KeyError:
            return None

    def all(self) -> List[BaseTransformer]:
        return sorted(self._by_slug.values(), key=lambda t: (t.category, t.slug))

    def by_category(self, category: str) -> List[BaseTransformer]:
        return [t for t in self.all() if t.category == category]

    def __iter__(self) -> Iterator[BaseTransformer]:
        return iter(self.all())

    def __len__(self) -> int:
        return len(self._by_slug)


registry = Registry()


def register(t: BaseTransformer) -> None:
    registry.register(t)
