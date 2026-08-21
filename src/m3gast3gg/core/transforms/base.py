"""BaseTransformer + ConfigurableOption — the object model for text transforms.

Every text transform in ``m3gast3gg.core.transforms`` is a ``BaseTransformer``
instance carrying its name, category, priority, and callables. The 12 fields
match the JS ``BaseTransformer`` in P4RS3LT0NGV3 so that agent-level
inspection and JSON serialization is portable between the two projects.

Priority scheme (from P4RS3LT0NGV3 ``BaseTransformer.js``):

- 310  Semaphore Flags (exclusive to 8 arrow emojis)
- 300  Exclusive character sets (Binary, Morse, Braille, Brainfuck, Tap Code)
- 290  Hexadecimal
- 285  Pattern-based (Pig Latin, Dovahzul)
- 280  Base32
- 270-275  Base64 / Base58 family
- 260  A1Z26
- 100  High confidence (Emoji Steganography, unique Unicode ranges)
- 85   Unicode transformations (fancy text default)
- 70   Common encodings (URL, HTML, ASCII85)
- 60   Ciphers (ROT13, Caesar)
- 50   Generic text transforms
- 20   Low confidence generic
- 1    Invisible text (last resort)
- 0    Cannot decode / encode-only
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


VALID_CATEGORIES = frozenset({
    "case", "cipher", "concealment", "encoding", "format",
    "signwriting", "special", "symbol", "technical", "unicode", "visual",
})
VALID_INPUT_KINDS = frozenset({"textarea", "file", "hex"})
VALID_OPTION_TYPES = frozenset({"boolean", "select", "text", "number"})


@dataclass
class ConfigurableOption:
    id: str
    label: str
    type: str
    default: Any = None
    options: Optional[List[Any]] = None
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None

    def __post_init__(self) -> None:
        if not self.id.isidentifier():
            raise ValueError(f"option id {self.id!r} is not a legal Python identifier")
        if self.type not in VALID_OPTION_TYPES:
            raise ValueError(f"option {self.id}: unknown type {self.type!r}")
        if self.type == "select":
            if not self.options:
                raise ValueError(f"option {self.id}: select requires non-empty options")
        elif self.type == "number":
            if self.min is None or self.max is None:
                raise ValueError(f"option {self.id}: number requires min and max")
            if self.min > self.max:
                raise ValueError(f"option {self.id}: min > max")
            if self.default is not None and not (self.min <= self.default <= self.max):
                raise ValueError(f"option {self.id}: default outside [min, max]")
        elif self.type == "boolean":
            if self.default not in (True, False):
                raise ValueError(f"option {self.id}: boolean default must be True or False")


@dataclass
class BaseTransformer:
    name: str
    func: Callable[..., str]
    category: str
    priority: int
    description: str = ""
    can_decode: bool = True
    input_kind: str = "textarea"
    reverse: Optional[Callable[..., str]] = None
    preview: Optional[Callable[..., str]] = None
    detector: Optional[Callable[[str], bool]] = None
    map: Optional[Dict[str, str]] = None
    configurable_options: List[ConfigurableOption] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("BaseTransformer.name must be non-empty")
        if self.category not in VALID_CATEGORIES:
            raise ValueError(f"{self.name}: unknown category {self.category!r}")
        if not (0 <= self.priority <= 310):
            raise ValueError(f"{self.name}: priority {self.priority} outside [0, 310]")
        if self.input_kind not in VALID_INPUT_KINDS:
            raise ValueError(f"{self.name}: unknown input_kind {self.input_kind!r}")
        if self.preview is None:
            self.preview = self.func
        if not self.can_decode:
            self.reverse = None
        elif self.reverse is None:
            if self.map is not None:
                self.reverse = self._auto_reverse
            else:
                raise ValueError(
                    f"{self.name}: can_decode=True requires either a reverse callable or a map"
                )
        seen_ids: set[str] = set()
        for opt in self.configurable_options:
            if opt.id in seen_ids:
                raise ValueError(f"{self.name}: duplicate option id {opt.id!r}")
            seen_ids.add(opt.id)

    def _auto_reverse(self, text: str, **_: Any) -> str:
        reverse_map = {v: k for k, v in (self.map or {}).items()}
        return "".join(reverse_map.get(c, c) for c in text)

    @property
    def slug(self) -> str:
        return re.sub(r"[^a-z0-9]+", "-", self.name.lower()).strip("-")
