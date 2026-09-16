"""MCP (Model Context Protocol) management system for Code Puppy.

The MCP bridge is optional. Keep this package import light so core Code Puppy can
start without installing ``code-puppy[mcp]``. Public symbols are resolved lazily
when a caller actually uses MCP features.
"""

from __future__ import annotations

from typing import Any

_SYMBOL_MODULES = {
    "ManagedMCPServer": ".managed_server",
    "ServerConfig": ".managed_server",
    "ServerState": ".managed_server",
    "ServerStatusTracker": ".status_tracker",
    "Event": ".status_tracker",
    "MCPManager": ".manager",
    "ServerInfo": ".manager",
    "get_mcp_manager": ".manager",
    "ServerRegistry": ".registry",
    "MCPErrorIsolator": ".error_isolation",
    "ErrorStats": ".error_isolation",
    "ErrorCategory": ".error_isolation",
    "QuarantinedServerError": ".error_isolation",
    "get_error_isolator": ".error_isolation",
    "CircuitBreaker": ".circuit_breaker",
    "CircuitState": ".circuit_breaker",
    "CircuitOpenError": ".circuit_breaker",
    "RetryManager": ".retry_manager",
    "RetryStats": ".retry_manager",
    "get_retry_manager": ".retry_manager",
    "retry_mcp_call": ".retry_manager",
    "MCPDashboard": ".dashboard",
    "MCPConfigWizard": ".config_wizard",
    "run_add_wizard": ".config_wizard",
    "get_mcp_logs_dir": ".mcp_logs",
    "get_log_file_path": ".mcp_logs",
    "read_logs": ".mcp_logs",
    "write_log": ".mcp_logs",
    "clear_logs": ".mcp_logs",
    "list_servers_with_logs": ".mcp_logs",
    "get_log_stats": ".mcp_logs",
}

__all__ = list(_SYMBOL_MODULES)


def __getattr__(name: str) -> Any:
    """Resolve MCP exports lazily so MCP dependencies stay optional."""
    module_name = _SYMBOL_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    try:
        from importlib import import_module

        module = import_module(module_name, __name__)
    except ImportError as exc:
        if _is_mcp_dependency_error(exc):
            from code_puppy.mcp_.optional import missing_mcp_message

            raise RuntimeError(missing_mcp_message("use MCP features")) from exc
        raise

    value = getattr(module, name)
    globals()[name] = value
    return value


def _is_mcp_dependency_error(exc: ImportError) -> bool:
    missing_name = getattr(exc, "name", "") or ""
    return missing_name == "mcp" or missing_name.startswith("mcp.")
