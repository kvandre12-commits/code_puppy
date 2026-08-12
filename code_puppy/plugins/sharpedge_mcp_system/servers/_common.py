"""Shared helpers for SharpEdge first-party MCP stdio servers."""

from __future__ import annotations

from code_puppy.mcp_optional import raise_if_mcp_unavailable


def make_fastmcp(app_name: str):
    """Create a FastMCP app only when the optional dependency exists."""
    raise_if_mcp_unavailable(f"{app_name} MCP server")
    from mcp.server.fastmcp import FastMCP

    return FastMCP(app_name)
