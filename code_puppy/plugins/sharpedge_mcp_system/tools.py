"""Agent-facing tools for the SharpEdge MCP system plugin."""

from __future__ import annotations

from typing import Any, Callable

from code_puppy.mcp_optional import has_mcp_support

from .bootstrap import list_first_party_servers
from .policy import build_autostart_readiness

_STATUS_TOOL_NAME = "sharpedge_mcp_system_status"
_MARKET_STATE_TOOL_NAME = "sharpedge_market_state"
# Backward-compatible internal alias used by older tests/extensions.
_TOOL_NAME = _STATUS_TOOL_NAME


def _safe_call(
    label: str, func: Callable[..., dict[str, Any]], /, **kwargs: Any
) -> dict[str, Any]:
    try:
        payload = func(**kwargs)
    except Exception as exc:  # pragma: no cover - defensive
        return {"success": False, "label": label, "error": str(exc)}
    if isinstance(payload, dict):
        payload.setdefault("label", label)
        return payload
    return {"success": False, "label": label, "error": "non-dict payload"}


def sharpedge_mcp_system_status(
    root: str = "",
    include_android: bool = False,
    local_port: int = 9222,
) -> dict[str, Any]:
    """Return a compact status packet for the first-party SharpEdge MCP stack."""
    from code_puppy.plugins.authority_gateway.tooling import authority_gateway_status
    from code_puppy.plugins.droidpuppy_context_kit.tooling import (
        droidpuppy_context_doctor,
    )
    from code_puppy.plugins.project_os_supervisor.tooling import project_os_bus_status

    catalog_servers = list_first_party_servers()
    catalog_server_names = [item["name"] for item in catalog_servers]
    surfaces = {
        "authority_gateway": _safe_call("authority_gateway", authority_gateway_status),
        "droidpuppy_context": _safe_call(
            "droidpuppy_context",
            droidpuppy_context_doctor,
            root=root,
        ),
        "project_os_bus": _safe_call("project_os_bus", project_os_bus_status),
    }
    if include_android:
        from code_puppy.plugins.android_capability_graph_kit.tooling import (
            android_capability_graph,
        )

        surfaces["android_capability_graph"] = _safe_call(
            "android_capability_graph",
            android_capability_graph,
            deep=False,
            local_port=local_port,
        )

    recommendations = [
        "Install MCP extra with `uv sync --extra mcp` if MCP support is missing.",
        "Bind `sharpedge-android-capability` to agent sessions that need Android topology.",
        "Bind `sharpedge-governance-readonly` anywhere you want workflow/authority visibility without risky writes.",
    ]
    return {
        "success": True,
        "tool_name": _STATUS_TOOL_NAME,
        "mcp_support_installed": has_mcp_support(),
        "catalog_servers": catalog_servers,
        "catalog_server_names": catalog_server_names,
        "surface_status": surfaces,
        "autostart_readiness": build_autostart_readiness(
            catalog_server_names, root=root
        ),
        "recommendations": recommendations,
        "summary": (
            f"SharpEdge MCP system knows {len(catalog_servers)} first-party server(s); "
            f"MCP extra installed={has_mcp_support()}."
        ),
    }
