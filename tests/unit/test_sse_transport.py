"""End-to-end test for the SSE MCP transport.

FastMCP exposes an SSE endpoint at ``/sse`` alongside the streamable-http
endpoint. This test spawns the server with ``--transport sse``, drives it
through the reference MCP SSE client, and confirms the same set of tools
is discoverable and callable.
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
    def __init__(self, port: int):
        self.port = port
        self.proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "m3gast3gg.server",
                "--transport", "sse",
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


async def test_sse_lists_and_calls_a_tool():
    from mcp.client.session import ClientSession
    from mcp.client.sse import sse_client

    port = _free_port()
    with _ServerProcess(port):
        url = f"http://127.0.0.1:{port}/sse"
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                tools = await session.list_tools()
                names = {t.name for t in tools.tools}
                assert names == set(TOOL_EXECUTORS.keys())

                result = await session.call_tool("stegg_list_techniques", {})
                assert not result.isError
                assert result.content
                text = "".join(
                    c.text for c in result.content if getattr(c, "type", None) == "text"
                )
                assert '"families"' in text
                assert '"image"' in text
