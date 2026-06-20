"""Lazy MCP package exports so missing extras don't break core imports."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from .optional import get_missing_mcp_message, is_missing_mcp_dependency

_EXPORTS = {
    "CircuitBreaker": ".circuit_breaker",
    "CircuitOpenError": ".circuit_breaker",
    "CircuitState": ".circuit_breaker",
    "MCPConfigWizard": ".config_wizard",
    "run_add_wizard": ".config_wizard",
    "MCPDashboard": ".dashboard",
    "ErrorCategory": ".error_isolation",
    "ErrorStats": ".error_isolation",
    "MCPErrorIsolator": ".error_isolation",
    "QuarantinedServerError": ".error_isolation",
    "get_error_isolator": ".error_isolation",
    "ManagedMCPServer": ".managed_server",
    "ServerConfig": ".managed_server",
    "ServerState": ".managed_server",
    "MCPManager": ".manager",
    "ServerInfo": ".manager",
    "get_mcp_manager": ".manager",
    "clear_logs": ".mcp_logs",
    "get_log_file_path": ".mcp_logs",
    "get_log_stats": ".mcp_logs",
    "get_mcp_logs_dir": ".mcp_logs",
    "list_servers_with_logs": ".mcp_logs",
    "read_logs": ".mcp_logs",
    "write_log": ".mcp_logs",
    "ServerRegistry": ".registry",
    "RetryManager": ".retry_manager",
    "RetryStats": ".retry_manager",
    "get_retry_manager": ".retry_manager",
    "retry_mcp_call": ".retry_manager",
    "Event": ".status_tracker",
    "ServerStatusTracker": ".status_tracker",
}

__all__ = list(_EXPORTS)


def _missing_get_mcp_manager(*_args: Any, **_kwargs: Any) -> Any:
    raise RuntimeError(get_missing_mcp_message("MCP server management"))


def __getattr__(name: str) -> Any:
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    try:
        module = import_module(module_name, __name__)
    except ModuleNotFoundError as exc:
        if not is_missing_mcp_dependency(exc):
            raise
        if name == "get_mcp_manager":
            globals()[name] = _missing_get_mcp_manager
            return _missing_get_mcp_manager
        raise RuntimeError(get_missing_mcp_message("MCP features")) from exc

    value = getattr(module, name)
    globals()[name] = value
    return value
