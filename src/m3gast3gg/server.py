"""M3GA-ST3GG MCP server built on FastMCP.

One entry point exposes three transports behind a single ``--transport``
flag, mirroring the shape sibling ``phr34cker5`` uses:

    m3gast3gg-mcp --transport stdio               # JSON-RPC over stdin/stdout
    m3gast3gg-mcp --transport sse                 # legacy SSE on /sse
    m3gast3gg-mcp --transport streamable-http     # modern HTTP on /mcp  (default)
    m3gast3gg-mcp                                 # same as --transport streamable-http
    m3gast3gg-mcp-stdio                           # alias for --transport stdio

The ``--stdio`` flag remains as a hidden alias for ``--transport stdio`` so
existing Claude Desktop / opencode client configs keep working.

The tool executors and JSON schemas registered by ``m3gast3gg.mcp`` are
adopted verbatim: FastMCP receives the exact ``inputSchema`` dicts the
low-level server used to emit, and each executor's kwarg-only call
convention is preserved via a permissive pydantic arg model.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.resources import FunctionResource
from mcp.server.fastmcp.tools.base import Tool
from mcp.server.fastmcp.utilities.func_metadata import ArgModelBase, FuncMetadata
from pydantic import ConfigDict

from .mcp import TOOL_EXECUTORS, TOOL_SCHEMAS
from .mcp.knowledge import KNOWLEDGE_ROOT, _find_lore, _iter_lore

logger = logging.getLogger(__name__)

FIELD_GUIDE_PATH = Path(__file__).parent / "field_guide.md"
FIELD_GUIDE_URI = "stegg://field-guide"
LORE_URI_PREFIX = "stegg://"

INSTRUCTIONS = (
    "M3GA-ST3GG is a steganography toolkit -- detection, encode, decode, "
    "capacity, triage across image / text / audio / network carriers, plus "
    "a typed knowledge base of techniques, transports, and survival data. "
    "Use `stegg_triage` when you don't know where to start. Read the field "
    "guide resource at stegg://field-guide before analyzing any file."
)


class _PassThroughArgs(ArgModelBase):
    """Accept any kwargs and return them verbatim.

    Executors declare their input schema through ``TOOL_SCHEMAS`` and take
    ``**kwargs``; the low-level server never validated arguments against
    the schema, so neither does FastMCP here. This model catches everything
    the client sends and forwards it to the executor unchanged.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    def model_dump_one_level(self) -> dict[str, Any]:  # type: ignore[override]
        return dict(self.__pydantic_extra__ or {})


def _make_tool(name: str, executor: Callable[..., Any], schema: dict[str, Any]) -> Tool:
    """Build a FastMCP Tool that reuses our verbatim schema + kwargs executor."""

    async def _adapter(**kwargs: Any) -> str:
        return await executor(**kwargs)

    _adapter.__name__ = name

    return Tool(
        fn=_adapter,
        name=name,
        title=None,
        description=schema["description"],
        parameters=schema["inputSchema"],
        fn_metadata=FuncMetadata(
            arg_model=_PassThroughArgs,
            output_schema=None,
            output_model=None,
            wrap_output=False,
        ),
        is_async=True,
        context_kwarg=None,
        annotations=None,
        icons=None,
        meta=None,
    )


def build_mcp() -> FastMCP:
    """Construct the FastMCP server with every tool and resource registered."""
    mcp = FastMCP(name="m3gast3gg", instructions=INSTRUCTIONS)

    # Tools: bypass ToolManager.add_tool (which would re-derive the schema
    # from the function signature) and install pre-built Tool objects with
    # the exact inputSchema each executor documents in TOOL_SCHEMAS.
    for tool_name, executor in TOOL_EXECUTORS.items():
        schema = TOOL_SCHEMAS[tool_name]
        mcp._tool_manager._tools[tool_name] = _make_tool(tool_name, executor, schema)

    _register_resources(mcp)
    return mcp


def _register_resources(mcp: FastMCP) -> None:
    """Register the field guide and every prose corpus file as MCP resources."""
    if FIELD_GUIDE_PATH.exists():
        mcp.add_resource(FunctionResource(
            uri=FIELD_GUIDE_URI,  # type: ignore[arg-type]
            name="ST3GG field guide",
            description=(
                "Complete field guide for the ST3GG steganography analyst persona: "
                "technique catalog, signal-reading heuristics, extraction workflow, "
                "verdict semantics, code snippets. Read this before analyzing any file."
            ),
            mime_type="text/markdown",
            fn=lambda: FIELD_GUIDE_PATH.read_text(encoding="utf-8"),
        ))

    for topic, name, path in _iter_lore(KNOWLEDGE_ROOT):
        uri = f"{LORE_URI_PREFIX}{topic}/{name}"
        # Bind the path at closure-construction time to avoid the classic
        # late-binding footgun (`p` inside the lambda would otherwise resolve
        # to the loop's final value for every registered resource).
        mcp.add_resource(FunctionResource(
            uri=uri,  # type: ignore[arg-type]
            name=f"{topic}/{name}",
            description=f"ST3GG knowledge corpus: {topic}/{name}",
            mime_type="text/markdown",
            fn=(lambda p=path: p.read_text(encoding="utf-8")),
        ))

    # Templated resource: any stegg://<topic>/<name> URI that isn't already
    # registered above (e.g. a fresh corpus file added after startup, or a
    # client speculatively probing) falls through to this handler.
    @mcp.resource("stegg://{topic}/{name}")
    def _lore_template(topic: str, name: str) -> str:
        p = _find_lore(KNOWLEDGE_ROOT, topic, name)
        if p is None:
            raise ValueError(f"unknown lore: {topic}/{name}")
        return p.read_text(encoding="utf-8")


mcp = build_mcp()


def _configure_logging(log_level: str, *, stdio: bool) -> None:
    """Route logs to stderr for stdio (stdout is reserved for JSON-RPC)."""
    logging.basicConfig(
        level=log_level.upper(),
        format="%(asctime)s  %(levelname)-7s %(name)s: %(message)s",
        stream=sys.stderr if stdio else None,
    )


def main() -> None:
    """Entry point for ``m3gast3gg-mcp`` (and ``python -m m3gast3gg.server``)."""
    parser = argparse.ArgumentParser(prog="m3gast3gg-mcp", description="M3GA-ST3GG MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="streamable-http",
        help=(
            "MCP transport. `stdio` for local clients (Claude Desktop, opencode). "
            "`sse` for Server-Sent-Events (legacy MCP web transport). "
            "`streamable-http` for the modern HTTP transport (default; what "
            "container-to-container callers currently expect)."
        ),
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Bind host for sse/streamable-http (default 0.0.0.0). Ignored for stdio.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Bind port for sse/streamable-http (default 8765). Ignored for stdio.",
    )
    parser.add_argument("--log-level", default="info", help="log level")
    parser.add_argument(
        "--stdio",
        action="store_true",
        help=argparse.SUPPRESS,  # hidden alias for --transport stdio
    )
    args = parser.parse_args()

    if args.stdio:
        args.transport = "stdio"

    _configure_logging(args.log_level, stdio=(args.transport == "stdio"))

    if args.transport == "stdio":
        logger.info("m3gast3gg stdio server starting")
    else:
        logger.info(
            "m3gast3gg starting on %s:%d, transport=%s",
            args.host,
            args.port,
            args.transport,
        )
    logger.info("tools: %s", ", ".join(TOOL_EXECUTORS.keys()))

    if args.transport in ("sse", "streamable-http"):
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        if args.host not in ("127.0.0.1", "localhost", "::1"):
            mcp.settings.transport_security = None

    mcp.run(transport=args.transport)


def main_stdio() -> None:
    """Entry point for ``m3gast3gg-mcp-stdio`` (alias for ``--transport stdio``)."""
    parser = argparse.ArgumentParser(
        prog="m3gast3gg-mcp-stdio",
        description="M3GA-ST3GG MCP stdio server (alias for `m3gast3gg-mcp --transport stdio`)",
    )
    parser.add_argument("--log-level", default="info", help="log level for stderr (default info)")
    args = parser.parse_args()

    _configure_logging(args.log_level, stdio=True)
    logger.info("m3gast3gg stdio server starting")
    logger.info("tools: %s", ", ".join(TOOL_EXECUTORS.keys()))
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
