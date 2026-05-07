"""MCP server that wraps the tokentoll CLI.

Exposes scan and diff as MCP tools so LLMs can estimate
and compare LLM API costs from within an MCP-capable host.
"""

import json
import subprocess
import sys
from typing import Optional

from mcp.server.fastmcp import FastMCP

server = FastMCP(
    "tokentoll",
    instructions="Catch LLM cost changes in code review. Scan for LLM API calls and estimate costs.",
)


def _run_cli(args: list[str]) -> str:
    """Run tokentoll CLI as a subprocess and return its stdout.

    All logging is written to stderr so that stdout remains clean
    for the MCP stdio transport.
    """
    cmd = [sys.executable, "-m", "tokentoll"] + args
    print(f"Running: {' '.join(cmd)}", file=sys.stderr)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        error_detail = result.stderr.strip() or result.stdout.strip() or "Unknown error"
        return json.dumps({
            "error": True,
            "returncode": result.returncode,
            "message": error_detail,
        })

    return result.stdout


@server.tool()
def scan(path: str = ".", calls_per_month: Optional[int] = None) -> str:
    """Scan a directory for LLM API calls and estimate monthly costs.

    Finds all LLM API call sites (OpenAI, Anthropic, etc.) in the given
    path and produces a cost estimate based on token counts and pricing.

    Args:
        path: Directory or file path to scan. Defaults to current directory.
        calls_per_month: Assumed monthly call volume per call site. If not
            provided, the CLI default (1000) is used.

    Returns:
        JSON string with the scan results including call sites and cost estimates.
    """
    args = ["scan", path, "--format", "json"]
    if calls_per_month is not None:
        args.extend(["--calls-per-month", str(calls_per_month)])
    return _run_cli(args)


@server.tool()
def diff(base_ref: str, head_ref: str = "HEAD") -> str:
    """Compare LLM costs between two git refs.

    Shows which LLM call sites were added, removed, or changed between
    the base and head refs, along with the cost impact of those changes.

    Args:
        base_ref: The base git ref (branch, tag, or commit) to compare from.
        head_ref: The head git ref to compare to. Defaults to HEAD.

    Returns:
        JSON string with the diff results including cost changes.
    """
    args = ["diff", "--base", base_ref, "--head", head_ref, "--format", "json"]
    return _run_cli(args)


def main() -> None:
    """Entry point for the MCP server. Runs over stdio transport."""
    print("Starting tokentoll MCP server...", file=sys.stderr)
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
