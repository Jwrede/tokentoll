import asyncio

import pytest

pytest.importorskip("mcp")

from tokentoll import mcp_server  # noqa: E402


def test_server_registers_scan_and_diff():
    tools = asyncio.run(mcp_server.server.list_tools())
    assert {t.name for t in tools} == {"scan", "diff"}
