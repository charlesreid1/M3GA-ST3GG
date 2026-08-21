"""Text-transform tools for the MCP server.

Exposes the m3gast3gg.core.transforms registry over MCP: list, inspect,
encode, decode, and the universal auto-decoder. Every executor returns a
JSON-encoded string via truncate_json.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from m3gast3gg.core.decoder import universal_decode
from m3gast3gg.core.transforms import registry
from m3gast3gg.core.transforms.base import BaseTransformer, VALID_CATEGORIES

from ._common import TOOL_TIMEOUT, run_sync, truncate_json

logger = logging.getLogger(__name__)

# Max UTF-8 bytes accepted on `text` — matches the text-steg tool cap.
_MAX_TEXT_BYTES = 1_048_576  # 1 MiB


def _serialize(t: BaseTransformer) -> dict:
    return {
        "name": t.name,
        "slug": t.slug,
        "category": t.category,
        "priority": t.priority,
        "description": t.description,
        "can_decode": t.can_decode,
        "input_kind": t.input_kind,
        "has_detector": t.detector is not None,
        "has_reverse": t.reverse is not None,
        "has_map": t.map is not None,
        "configurable_options": [
            {
                "id": o.id,
                "label": o.label,
                "type": o.type,
                "default": o.default,
                "options": o.options,
                "min": o.min,
                "max": o.max,
                "step": o.step,
            }
            for o in t.configurable_options
        ],
    }


def _check_text(text: Any) -> tuple[str | None, str | None]:
    if not isinstance(text, str):
        return None, "text: must be a string"
    if len(text.encode("utf-8")) > _MAX_TEXT_BYTES:
        return None, f"text: input too large (> {_MAX_TEXT_BYTES} bytes)"
    return text, None


def _validate_options(t: BaseTransformer, options: Any) -> tuple[dict | None, str | None]:
    if options is None:
        return {}, None
    if not isinstance(options, dict):
        return None, "options: must be an object"
    by_id = {o.id: o for o in t.configurable_options}
    validated: dict = {}
    for key, value in options.items():
        opt = by_id.get(key)
        if opt is None:
            return None, f"unknown option {key!r} for {t.name!r}"
        if opt.type == "boolean":
            if not isinstance(value, bool):
                return None, f"option {key}: expected boolean, got {type(value).__name__}"
        elif opt.type == "number":
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                return None, f"option {key}: expected number"
            if opt.min is not None and value < opt.min:
                return None, f"option {key}: below min {opt.min}"
            if opt.max is not None and value > opt.max:
                return None, f"option {key}: above max {opt.max}"
        elif opt.type == "select":
            if opt.options and value not in opt.options:
                return None, f"option {key}: not in {opt.options}"
        elif opt.type == "text":
            if not isinstance(value, str):
                return None, f"option {key}: expected string"
        validated[key] = value
    return validated, None


async def execute_list_transforms(category: str | None = None, **_kw) -> str:
    def work():
        if category is not None and category not in VALID_CATEGORIES:
            return {"error": f"unknown category {category!r}",
                    "valid": sorted(VALID_CATEGORIES)}
        items = registry.by_category(category) if category else registry.all()
        return {
            "transforms": [
                {"slug": t.slug, "name": t.name, "category": t.category,
                 "priority": t.priority, "can_decode": t.can_decode,
                 "has_detector": t.detector is not None}
                for t in items
            ],
            "count": len(items),
        }

    try:
        result = await run_sync(work)
    except asyncio.TimeoutError:
        return f"stegg_list_transforms timed out after {TOOL_TIMEOUT}s"
    except Exception as exc:
        logger.exception("list_transforms failed")
        return f"stegg_list_transforms error: {exc}"
    return truncate_json(result)


async def execute_inspect_transform(name: str | None = None, **_kw) -> str:
    def work():
        if not name:
            return {"error": "name is required"}
        t = registry.get_optional(name)
        if t is None:
            return {"error": f"unknown transform {name!r}"}
        return _serialize(t)

    try:
        result = await run_sync(work)
    except asyncio.TimeoutError:
        return f"stegg_inspect_transform timed out after {TOOL_TIMEOUT}s"
    except Exception as exc:
        logger.exception("inspect_transform failed")
        return f"stegg_inspect_transform error: {exc}"
    return truncate_json(result)


async def execute_encode_transform(
    name: str | None = None,
    text: Any = None,
    options: Any = None,
    **_kw,
) -> str:
    def work():
        if not name:
            return {"error": "name is required"}
        t = registry.get_optional(name)
        if t is None:
            return {"error": f"unknown transform {name!r}"}
        text_ok, err = _check_text(text)
        if err:
            return {"error": err}
        opts, err = _validate_options(t, options)
        if err:
            return {"error": err}
        try:
            output = t.func(text_ok, **opts)
        except Exception as exc:
            return {"error": f"{t.name} encode failed: {exc}"}
        return {
            "transform": t.slug,
            "options": opts,
            "output": output,
            "output_length": len(output),
        }

    try:
        result = await run_sync(work)
    except asyncio.TimeoutError:
        return f"stegg_encode_transform timed out after {TOOL_TIMEOUT}s"
    except Exception as exc:
        logger.exception("encode_transform failed")
        return f"stegg_encode_transform error: {exc}"
    return truncate_json(result)


async def execute_decode_transform(
    name: str | None = None,
    text: Any = None,
    options: Any = None,
    **_kw,
) -> str:
    def work():
        if not name:
            return {"error": "name is required"}
        t = registry.get_optional(name)
        if t is None:
            return {"error": f"unknown transform {name!r}"}
        if t.reverse is None:
            return {"error": f"{t.name} has can_decode=False; nothing to reverse"}
        text_ok, err = _check_text(text)
        if err:
            return {"error": err}
        opts, err = _validate_options(t, options)
        if err:
            return {"error": err}
        try:
            output = t.reverse(text_ok, **opts)
        except Exception as exc:
            return {"error": f"{t.name} decode failed: {exc}"}
        return {
            "transform": t.slug,
            "options": opts,
            "output": output,
            "output_length": len(output),
        }

    try:
        result = await run_sync(work)
    except asyncio.TimeoutError:
        return f"stegg_decode_transform timed out after {TOOL_TIMEOUT}s"
    except Exception as exc:
        logger.exception("decode_transform failed")
        return f"stegg_decode_transform error: {exc}"
    return truncate_json(result)


async def execute_chain_transforms(
    text: Any = None,
    steps: Any = None,
    **_kw,
) -> str:
    def work():
        text_ok, err = _check_text(text)
        if err:
            return {"error": err}
        if not isinstance(steps, list) or not steps:
            return {"error": "steps: must be a non-empty list"}
        current = text_ok
        trace: list[dict] = []
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                return {"error": f"step[{i}]: must be an object"}
            name = step.get("name")
            action = step.get("action", "encode")
            options = step.get("options")
            if not isinstance(name, str) or not name:
                return {"error": f"step[{i}].name: required string"}
            if action not in ("encode", "decode"):
                return {"error": f"step[{i}].action: must be 'encode' or 'decode'"}
            t = registry.get_optional(name)
            if t is None:
                return {"error": f"step[{i}]: unknown transform {name!r}"}
            if action == "decode" and t.reverse is None:
                return {"error": f"step[{i}]: {t.name} has can_decode=False"}
            opts, err = _validate_options(t, options)
            if err:
                return {"error": f"step[{i}]: {err}"}
            fn = t.func if action == "encode" else t.reverse
            try:
                current = fn(current, **opts)
            except Exception as exc:
                return {"error": f"step[{i}] {t.name} {action} failed: {exc}"}
            trace.append({
                "index": i,
                "transform": t.slug,
                "action": action,
                "options": opts,
                "output_length": len(current),
            })
        return {
            "input_length": len(text_ok),
            "output": current,
            "output_length": len(current),
            "steps": trace,
        }

    try:
        result = await run_sync(work)
    except asyncio.TimeoutError:
        return f"stegg_chain_transforms timed out after {TOOL_TIMEOUT}s"
    except Exception as exc:
        logger.exception("chain_transforms failed")
        return f"stegg_chain_transforms error: {exc}"
    return truncate_json(result)


async def execute_auto_decode(
    text: Any = None,
    top_k: int = 5,
    include_low_confidence: bool = True,
    **_kw,
) -> str:
    def work():
        text_ok, err = _check_text(text)
        if err:
            return {"error": err}
        if not isinstance(top_k, int) or top_k < 0:
            return {"error": "top_k: must be a non-negative integer"}
        candidates = universal_decode(
            text_ok,
            top_k=top_k,
            include_low_confidence=bool(include_low_confidence),
        )
        return {
            "input_length": len(text_ok),
            "candidates": [c.to_dict() for c in candidates],
            "count": len(candidates),
        }

    try:
        result = await run_sync(work)
    except asyncio.TimeoutError:
        return f"stegg_auto_decode timed out after {TOOL_TIMEOUT}s"
    except Exception as exc:
        logger.exception("auto_decode failed")
        return f"stegg_auto_decode error: {exc}"
    return truncate_json(result)


EXECUTORS = {
    "stegg_list_transforms": execute_list_transforms,
    "stegg_inspect_transform": execute_inspect_transform,
    "stegg_encode_transform": execute_encode_transform,
    "stegg_decode_transform": execute_decode_transform,
    "stegg_chain_transforms": execute_chain_transforms,
    "stegg_auto_decode": execute_auto_decode,
}


_CATEGORY_ENUM = sorted(VALID_CATEGORIES)


SCHEMAS = {
    "stegg_list_transforms": {
        "description": (
            "List every registered text transform (ciphers, encodings, "
            "unicode, concealment, ...). Optional --category filter."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "enum": _CATEGORY_ENUM,
                              "description": "Filter to one category."},
            },
        },
    },
    "stegg_inspect_transform": {
        "description": (
            "Return full metadata for one transform (name, slug, category, "
            "priority, description, configurable_options, capability flags)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Transform slug or human name."},
            },
            "required": ["name"],
        },
    },
    "stegg_encode_transform": {
        "description": (
            "Encode text through one transform. Options is a JSON object of "
            "key/value pairs matching the transform's configurable_options."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "text": {"type": "string"},
                "options": {"type": "object"},
            },
            "required": ["name", "text"],
        },
    },
    "stegg_decode_transform": {
        "description": (
            "Decode text through a transform's reverse. Same option shape as "
            "encode. Refuses transforms with can_decode=False."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "text": {"type": "string"},
                "options": {"type": "object"},
            },
            "required": ["name", "text"],
        },
    },
    "stegg_chain_transforms": {
        "description": (
            "Run an ordered pipeline of transforms over one input. Each step "
            "is {name, action, options} with action ∈ {encode, decode}. "
            "Useful for stacking obfuscation stages (e.g. caesar → base64 → "
            "zero-width). Returns the final output plus a per-step trace."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "steps": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "action": {"type": "string",
                                        "enum": ["encode", "decode"],
                                        "default": "encode"},
                            "options": {"type": "object"},
                        },
                        "required": ["name"],
                    },
                },
            },
            "required": ["text", "steps"],
        },
    },
    "stegg_auto_decode": {
        "description": (
            "Run the universal auto-decoder — try every detector-firing "
            "transform and return the top-K candidates ranked by priority "
            "and printability confidence."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "top_k": {"type": "integer", "minimum": 0, "default": 5},
                "include_low_confidence": {"type": "boolean", "default": True},
            },
            "required": ["text"],
        },
    },
}
