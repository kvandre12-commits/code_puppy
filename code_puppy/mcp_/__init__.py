"""MCP (Model Context Protocol) management system for Code Puppy.

This package exports the public MCP API lazily so Code Puppy can boot even
when the optional ``mcp`` dependency is not installed.
"""

from __future__ import annotations

import importlib
from typing import Any

from code_puppy.mcp_optional import MCPUnavailableError, get_mcp_install_hint

_EXPORTS = {
    "ManagedMCPServer": (".managed_server", "ManagedMCPServer"),
    "ServerConfig": (".managed_server", "ServerConfig"),
    "ServerState": (".managed_server", "ServerState"),
    "ServerStatusTracker": (".status_tracker", "ServerStatusTracker"),
    "Event": (".status_tracker", "Event"),
    "MCPManager": (".manager", "MCPManager"),
    "ServerInfo": (".manager", "ServerInfo"),
    "get_mcp_manager": (".manager", "get_mcp_manager"),
    "ServerRegistry": (".registry", "ServerRegistry"),
    "MCPErrorIsolator": (".error_isolation", "MCPErrorIsolator"),
    "ErrorStats": (".error_isolation", "ErrorStats"),
    "ErrorCategory": (".error_isolation", "ErrorCategory"),
    "QuarantinedServerError": (".error_isolation", "QuarantinedServerError"),
    "get_error_isolator": (".error_isolation", "get_error_isolator"),
    "CircuitBreaker": (".circuit_breaker", "CircuitBreaker"),
    "CircuitState": (".circuit_breaker", "CircuitState"),
    "CircuitOpenError": (".circuit_breaker", "CircuitOpenError"),
    "RetryManager": (".retry_manager", "RetryManager"),
    "RetryStats": (".retry_manager", "RetryStats"),
    "get_retry_manager": (".retry_manager", "get_retry_manager"),
    "retry_mcp_call": (".retry_manager", "retry_mcp_call"),
    "MCPDashboard": (".dashboard", "MCPDashboard"),
    "MCPConfigWizard": (".config_wizard", "MCPConfigWizard"),
    "run_add_wizard": (".config_wizard", "run_add_wizard"),
    "get_mcp_logs_dir": (".mcp_logs", "get_mcp_logs_dir"),
    "get_log_file_path": (".mcp_logs", "get_log_file_path"),
    "read_logs": (".mcp_logs", "read_logs"),
    "write_log": (".mcp_logs", "write_log"),
    "clear_logs": (".mcp_logs", "clear_logs"),
    "list_servers_with_logs": (".mcp_logs", "list_servers_with_logs"),
    "get_log_stats": (".mcp_logs", "get_log_stats"),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    """Load public MCP exports on first access."""
    if name not in _EXPORTS:
        raise AttributeError(name)

    module_name, attr_name = _EXPORTS[name]
    try:
        module = importlib.import_module(module_name, __name__)
    except ModuleNotFoundError as exc:
        missing_name = getattr(exc, "name", "") or ""
        if missing_name == "mcp" or missing_name.startswith("mcp."):
            raise MCPUnavailableError(get_mcp_install_hint("MCP support")) from exc
        raise

    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
