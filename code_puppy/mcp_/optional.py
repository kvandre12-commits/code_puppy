"""Optional dependency helpers for MCP support."""

from __future__ import annotations

from typing import Any

MCP_EXTRA_INSTALL_HINT = "pip install 'code-puppy[mcp]'"


def is_mcp_available() -> bool:
    """Return True when the optional MCP runtime dependencies are installed."""
    try:
        import mcp  # noqa: F401
        import pydantic_ai.mcp  # noqa: F401
    except ImportError:
        return False
    return True


def missing_mcp_message(action: str = "use MCP features") -> str:
    """Human-friendly message for unavailable MCP bridge dependencies."""
    return f"MCP support is optional. Install it to {action}: {MCP_EXTRA_INSTALL_HINT}"


def get_mcp_error_type() -> type[BaseException] | None:
    """Return the upstream MCP error type, or None when MCP is not installed."""
    try:
        from mcp.shared.exceptions import McpError
    except ImportError:
        return None
    return McpError


def require_mcp(action: str = "use MCP features") -> None:
    """Raise a clear error when optional MCP dependencies are missing."""
    if not is_mcp_available():
        raise RuntimeError(missing_mcp_message(action))


def emit_missing_mcp_warning(action: str = "use MCP features") -> None:
    """Emit a warning without importing messaging at module import time."""
    from code_puppy.messaging import emit_warning

    emit_warning(missing_mcp_message(action))


def optional_mcp_manager() -> Any | None:
    """Return the MCP manager when available, otherwise warn and return None."""
    if not is_mcp_available():
        emit_missing_mcp_warning("manage MCP servers")
        return None

    from code_puppy.mcp_.manager import get_mcp_manager

    return get_mcp_manager()
