"""Helpers for treating MCP as an optional extra.

Keeps the install hint in one place so import guards, command handlers,
and lazy module exports all say the same thing instead of free-styling.
"""

from __future__ import annotations

import importlib

_INSTALL_COMMANDS = (
    "uv sync --extra mcp",
    "pip install 'code-puppy[mcp]'",
)


class MCPUnavailableError(ModuleNotFoundError):
    """Raised when optional MCP support is requested but not installed."""


def get_mcp_install_hint(feature: str = "MCP support") -> str:
    """Return a friendly install hint for missing optional MCP support."""
    commands = " or ".join(f"`{cmd}`" for cmd in _INSTALL_COMMANDS)
    return f"{feature} isn't installed. Install it with {commands}."


def has_mcp_support() -> bool:
    """Return True when the optional ``mcp`` dependency can be imported."""
    try:
        importlib.import_module("mcp")
    except ImportError:
        return False
    return True


def raise_if_mcp_unavailable(feature: str = "MCP support") -> None:
    """Raise a friendly error when MCP support is unavailable."""
    if has_mcp_support():
        return
    raise MCPUnavailableError(get_mcp_install_hint(feature))
