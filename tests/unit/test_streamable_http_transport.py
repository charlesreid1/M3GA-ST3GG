"""End-to-end test for the streamable-http MCP transport.

The FastMCP migration exposes ``--transport streamable-http`` on the same
``m3gast3gg-mcp`` entry point. Client-visible behavior should be identical
to what the hand-rolled Starlette ASGI app used to serve at ``/mcp``.

The test spawns the server on a free port, drives it through the reference
MCP streamable-http client, and asserts:

  * ``initialize`` completes,
  * ``tools/list`` returns the full in-process registry,
  * one round-trip ``tools/call`` succeeds.

We deliberately keep the assertion surface small: the stdio suite already
guards the wire protocol at a fine grain; this file guards that the HTTP
transport is present, mounted at ``/mcp``, and speaks the same schema.
"""

from __future__ import annotations

import socket
import subprocess
import sys
import time
from contextlib import closing

import pytest

from m3gast3gg.mcp import TOOL_EXECUTORS


pytestmark = pytest.mark.asyncio


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_port(host: str, port: int, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.settimeout(0.5)
            try:
                s.connect((host, port))
                return
            except OSError:
                time.sleep(0.1)
    raise RuntimeError(f"server on {host}:{port} did not accept connections within {timeout}s")


class _ServerProcess:
    def __init__(self, transport: str, port: int):
        self.port = port
        self.proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "m3gast3gg.server",
                "--transport", transport,
                "--host", "127.0.0.1",
                "--port", str(port),
                "--log-level", "warning",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def __enter__(self):
        _wait_for_port("127.0.0.1", self.port)
        return self

    def __exit__(self, *_):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()


async def test_streamable_http_lists_and_calls_a_tool():
    from mcp.client.session import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    port = _free_port()
    with _ServerProcess("streamable-http", port):
        url = f"http://127.0.0.1:{port}/mcp"
        async with streamablehttp_client(url) as (read, write, _session_id):
            async with ClientSession(read, write) as session:
                await session.initialize()

                tools = await session.list_tools()
                names = {t.name for t in tools.tools}
                assert names == set(TOOL_EXECUTORS.keys()), (
                    "tools/list output over streamable-http drifted from the "
                    "in-process registry"
                )

                result = await session.call_tool("stegg_list_techniques", {})
                assert not result.isError
                assert result.content, "expected at least one content block"
                text = "".join(
                    c.text for c in result.content if getattr(c, "type", None) == "text"
                )
                assert '"families"' in text
                assert '"image"' in text
