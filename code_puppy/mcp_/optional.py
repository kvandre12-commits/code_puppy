"""Helpers for treating MCP support as an optional dependency."""

from __future__ import annotations

from importlib import import_module

_MCP_EXTRA_INSTALL = "pip install 'code-puppy[mcp]'"
_MCP_MODULE_PREFIXES = ("mcp", "pydantic_ai.mcp")


def is_missing_mcp_dependency(exc: BaseException) -> bool:
    """Return True when ``exc`` is a missing-module error for MCP bits."""
    if not isinstance(exc, ModuleNotFoundError):
        return False
    name = getattr(exc, "name", "") or ""
    return any(
        name == prefix or name.startswith(f"{prefix}.")
        for prefix in _MCP_MODULE_PREFIXES
    )


def get_missing_mcp_message(feature: str = "MCP features") -> str:
    """Build a friendly install hint for a missing MCP extra."""
    return (
        f"{feature} require the optional mcp extra. "
        f"Install it with: {_MCP_EXTRA_INSTALL}"
    )


def raise_for_missing_mcp(feature: str = "MCP features") -> None:
    """Raise a consistent runtime error for missing MCP support."""
    raise RuntimeError(get_missing_mcp_message(feature))


def is_mcp_available() -> bool:
    """Return True when both the MCP SDK and pydantic-ai MCP bridge import."""
    try:
        import_module("mcp")
        import_module("pydantic_ai.mcp")
    except ModuleNotFoundError as exc:
        if is_missing_mcp_dependency(exc):
            return False
        raise
    return True
