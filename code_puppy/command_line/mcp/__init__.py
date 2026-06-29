"""Namespace package for MCP command handlers.

Loaded lazily so the rest of Code Puppy can boot without the optional MCP
extra installed.
"""

from __future__ import annotations

from typing import Any

from code_puppy.mcp_optional import MCPUnavailableError, get_mcp_install_hint

__all__ = ["MCPCommandHandler"]


def __getattr__(name: str) -> Any:
    if name != "MCPCommandHandler":
        raise AttributeError(name)
    try:
        from .handler import MCPCommandHandler
    except ModuleNotFoundError as exc:
        missing_name = getattr(exc, "name", "") or ""
        if missing_name == "mcp" or missing_name.startswith("mcp."):
            raise MCPUnavailableError(get_mcp_install_hint("/mcp commands")) from exc
        raise
    globals()[name] = MCPCommandHandler
    return MCPCommandHandler
