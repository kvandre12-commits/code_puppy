"""Register callbacks for the SharpEdge first-party MCP system plugin."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback
from code_puppy.messaging import emit_info, emit_warning

from .bootstrap import list_first_party_servers
from .market_state import sharpedge_market_state as sharpedge_market_state_impl
from .policy import build_autostart_readiness
from .server_specs import get_server_templates
from .tools import (
    _MARKET_STATE_TOOL_NAME,
    _STATUS_TOOL_NAME,
    sharpedge_mcp_system_status as sharpedge_mcp_system_status_impl,
)

_COMMAND_NAME = "sharpedge-mcp"


def register_sharpedge_mcp_system_status(agent: Any) -> None:
    @agent.tool
    async def sharpedge_mcp_system_status(
        context: RunContext,
        root: str = "",
        include_android: bool = False,
        local_port: int = 9222,
    ) -> dict[str, Any]:
        del context
        return sharpedge_mcp_system_status_impl(
            root=root,
            include_android=include_android,
            local_port=local_port,
        )


def register_sharpedge_market_state(agent: Any) -> None:
    @agent.tool
    async def sharpedge_market_state(
        context: RunContext,
        signal_path: str = "",
        max_age_seconds: int = 300,
    ) -> dict[str, Any]:
        """Read SharpEdge's current market state without execution authority."""
        del context
        return sharpedge_market_state_impl(
            signal_path=signal_path,
            max_age_seconds=max_age_seconds,
        )


def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {
            "name": _STATUS_TOOL_NAME,
            "register_func": register_sharpedge_mcp_system_status,
        },
        {
            "name": _MARKET_STATE_TOOL_NAME,
            "register_func": register_sharpedge_market_state,
        },
    ]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_STATUS_TOOL_NAME, _MARKET_STATE_TOOL_NAME]


def _register_mcp_catalog_servers() -> list[Any]:
    return get_server_templates()


async def _pre_mcp_autostart(agent_name: str, server_names: list[str]) -> None:
    readiness = build_autostart_readiness(server_names)
    managed = readiness.get("managed_server_names") or []
    if not managed:
        return
    emit_info(f"SharpEdge MCP bootstrap for agent '{agent_name}': {', '.join(managed)}")
    for check in readiness.get("checks", []):
        label = str(check.get("label", "check"))
        if check.get("success", True):
            emit_info(f"  {label}: ready")
            continue
        emit_warning(f"  {label}: {check.get('error', 'readiness check failed')}")


def _custom_help() -> list[tuple[str, str]]:
    return [(_COMMAND_NAME, "Show SharpEdge first-party MCP server status")]


def _handle_custom_command(command: str, name: str) -> bool | None:
    if name != _COMMAND_NAME:
        return None
    status = sharpedge_mcp_system_status_impl()
    emit_info(status["summary"])
    emit_info("First-party SharpEdge MCP servers:")
    for server in list_first_party_servers():
        emit_info(f"  - {server['name']} ({server['display_name']})")
    return True


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
register_callback("register_mcp_catalog_servers", _register_mcp_catalog_servers)
register_callback("pre_mcp_autostart", _pre_mcp_autostart)
register_callback("custom_command_help", _custom_help)
register_callback("custom_command", _handle_custom_command)
