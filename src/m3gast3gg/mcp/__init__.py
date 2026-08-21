"""Tool registry for the m3gast3gg MCP server.

Each per-family submodule exports its own `EXECUTORS` and `SCHEMAS` dicts;
this module merges them into the two dicts server.py consumes. Adding a tool
means editing exactly one submodule.
"""

from __future__ import annotations

from . import image, jailbreak, knowledge, meta, network, text, transforms, triage

# Re-export individual executors so callers can still do
#   `from m3gast3gg.mcp import execute_text_encode`
# the way they did before tools.py was split into a package.
from .image import (  # noqa: F401
    execute_apng_fdat_encode,
    execute_apng_fdat_decode,
    execute_audio_lsb_encode,
    execute_carve,
    execute_write_image_metadata,
    execute_decode_manual,
    execute_detect_trailing,
    execute_encode_manual,
    execute_encode_metadata,
    execute_gif_comment_encode,
    execute_gif_comment_decode,
    execute_gif_palette_encode,
    execute_gif_palette_decode,
    execute_jsteg_capacity,
    execute_jsteg_decode,
    execute_jsteg_encode,
    execute_lsb_smart_scan,
    execute_pdf_smuggle,
    execute_polyglot_encode,
    execute_pvd_capacity,
    execute_pvd_decode,
    execute_pvd_encode,
    execute_read_metadata,
    execute_read_png_chunks,
)
from .meta import execute_capabilities, execute_list_techniques  # noqa: F401
from .network import (  # noqa: F401
    execute_network_decode,
    execute_network_encode,
    execute_network_methods,
)
from .text import (  # noqa: F401
    execute_text_capacity,
    execute_text_decode,
    execute_text_encode,
    execute_text_steg,
    execute_text_steg_message,
)
from .transforms import (  # noqa: F401
    execute_auto_decode,
    execute_chain_transforms,
    execute_decode_transform,
    execute_encode_transform,
    execute_inspect_transform,
    execute_list_transforms,
)
from .triage import execute_triage  # noqa: F401
from .jailbreak import (  # noqa: F401
    execute_jailbreak_compose_image,
    execute_jailbreak_compose_text,
    execute_jailbreak_compose_unicode_tag,
    execute_jailbreak_detect,
    execute_jailbreak_list,
    execute_transforms_list,
)

_MODULES = (image, triage, text, meta, network, jailbreak, knowledge, transforms)

TOOL_EXECUTORS: dict = {}
TOOL_SCHEMAS: dict = {}

for _m in _MODULES:
    for _name, _fn in _m.EXECUTORS.items():
        if _name in TOOL_EXECUTORS:
            raise RuntimeError(f"duplicate tool executor registered: {_name}")
        TOOL_EXECUTORS[_name] = _fn
    for _name, _schema in _m.SCHEMAS.items():
        if _name in TOOL_SCHEMAS:
            raise RuntimeError(f"duplicate tool schema registered: {_name}")
        TOOL_SCHEMAS[_name] = _schema

# Sanity: every executor should have a schema and vice versa.
_missing_schemas = set(TOOL_EXECUTORS) - set(TOOL_SCHEMAS)
_missing_executors = set(TOOL_SCHEMAS) - set(TOOL_EXECUTORS)
if _missing_schemas or _missing_executors:
    raise RuntimeError(
        f"tool registry mismatch: missing schemas={_missing_schemas}, "
        f"missing executors={_missing_executors}"
    )

__all__ = ["TOOL_EXECUTORS", "TOOL_SCHEMAS"]
