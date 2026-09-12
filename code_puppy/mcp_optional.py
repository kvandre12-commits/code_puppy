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


class _UnreachableMCPRunError(Exception):
    """Private stand-in for ``mcp``'s run-error type when MCP is absent.

    Nothing in the codebase (or in any dependency) ever raises this, so an
    ``except*``/``except`` clause bound to it is inert: it cannot accidentally
    swallow unrelated runtime failures. Used only as the fallback return of
    :func:`get_mcp_run_error_type` so callers can keep a static
    ``except* <type>`` guard without importing ``mcp`` eagerly.
    """


def get_mcp_run_error_type() -> type[BaseException]:
    """Return the exception type representing an MCP protocol/run error.

    When the optional ``mcp`` package is installed, resolve its real
    ``McpError`` class (some releases spell it ``MCPError``) so ``except*``
    guards catch genuine MCP failures during an agent run. When MCP is
    absent, return :class:`_UnreachableMCPRunError` -- a private ``Exception``
    subclass that nothing raises -- so the guard stays inert instead of
    catching normal runtime errors.
    """
    if not has_mcp_support():
        return _UnreachableMCPRunError
    try:
        from mcp.shared.exceptions import McpError

        return McpError
    except ImportError:
        pass
    try:
        from mcp.shared.exceptions import MCPError  # type: ignore[attr-defined]

        return MCPError
    except ImportError:
        return _UnreachableMCPRunError
