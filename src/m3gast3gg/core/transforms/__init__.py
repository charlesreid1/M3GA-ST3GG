"""Text transforms — the canonical home for reversible text transformations.

Every transform is a ``BaseTransformer`` registered in the global ``registry``
at package-import time. Consumers reach for the object model directly:

.. code-block:: python

    from m3gast3gg.core.transforms import get, registry

    t = get("caesar")
    encoded = t.func("Attack at dawn", shift=5)
    decoded = t.reverse(encoded, shift=5)

The pre-refactor free-function API (``zalgo_text``, ``base64_encode``, ...)
and the flat ``_TRANSFORMS`` dict are preserved via a legacy compatibility
shim (``_LegacyTransformsView``); they emit ``DeprecationWarning`` on first
access and will be removed in v0.next+3.
"""

from __future__ import annotations

import warnings
from typing import Any, Callable, Iterator, KeysView, List

from ._index import load_all
from .base import BaseTransformer, ConfigurableOption
from .registry import register, registry

load_all()


# ---- Preferred API ----------------------------------------------------------

def get(name: str) -> BaseTransformer:
    """Return the full ``BaseTransformer`` for a slug or human name."""
    return registry.get(name)


def list_transforms() -> List[str]:
    """List registered transform slugs, sorted by (category, slug)."""
    return [t.slug for t in registry.all()]


# ---- Legacy compatibility shim ---------------------------------------------

class _LegacyTransformsView:
    """Read-only dict-like wrapper: keys are transform slugs, values are the
    ``func`` callable. Retained so pre-refactor consumers keep working.
    Emits ``DeprecationWarning`` on first mutation-style access.
    """

    _warned = False

    def _warn(self) -> None:
        if not _LegacyTransformsView._warned:
            warnings.warn(
                "_TRANSFORMS flat dict is deprecated; use "
                "m3gast3gg.core.transforms.registry instead.",
                DeprecationWarning, stacklevel=3,
            )
            _LegacyTransformsView._warned = True

    def __getitem__(self, key: str) -> Callable[..., str]:
        return registry.get(key).func

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        return registry.get_optional(key) is not None

    def __iter__(self) -> Iterator[str]:
        return iter(t.slug for t in registry.all())

    def __len__(self) -> int:
        return len(registry)

    def keys(self) -> KeysView[str]:
        return {t.slug: None for t in registry.all()}.keys()

    def values(self) -> List[Callable[..., str]]:
        return [t.func for t in registry.all()]

    def items(self) -> List[tuple[str, Callable[..., str]]]:
        return [(t.slug, t.func) for t in registry.all()]

    def get(self, key: str, default: Any = None) -> Any:
        t = registry.get_optional(key)
        return t.func if t is not None else default


_TRANSFORMS = _LegacyTransformsView()


def get_transform(name: str) -> Callable[..., str]:
    """Legacy free-function API. Returns just the callable, not the
    ``BaseTransformer``. Preserved for two releases (see plan §12.2.7).
    """
    return registry.get(name).func


# ---- Legacy free-function re-exports ---------------------------------------
# Deprecation-window shims so the old surface keeps working during migration.
# Bound to ``registry.get(slug).func`` at import so identity equality holds:
# ``get_transform("fullwidth") is fullwidth_text``.

zalgo_text = registry.get("zalgo").func
fullwidth_text = registry.get("fullwidth").func
leetspeak = registry.get("leetspeak").func
base64_encode = registry.get("base64").func
base32_encode = registry.get("base32").func
binary_encode = registry.get("binary").func
ternary_encode = registry.get("ternary").func
hex_encode = registry.get("hex").func
reverse_text = registry.get("reverse").func

from .encoding._base_n import base_n_encode  # noqa: E402  (re-export)


__all__ = [
    "BaseTransformer",
    "ConfigurableOption",
    "registry",
    "register",
    "get",
    "get_transform",
    "list_transforms",
    "_TRANSFORMS",
    "zalgo_text",
    "fullwidth_text",
    "leetspeak",
    "base64_encode",
    "base32_encode",
    "binary_encode",
    "ternary_encode",
    "hex_encode",
    "reverse_text",
    "base_n_encode",
]
