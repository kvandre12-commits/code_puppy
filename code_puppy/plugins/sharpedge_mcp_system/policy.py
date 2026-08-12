"""Readiness and policy helpers for SharpEdge first-party MCP servers."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Callable

from .bootstrap import match_first_party_server_names

_AUTHORITATIVE_SERVER = "sharpedge-governance-readonly"
_ANDROID_SERVER = "sharpedge-android-capability"


def _safe_call(
    label: str, func: Callable[..., dict[str, Any]], /, **kwargs: Any
) -> dict[str, Any]:
    try:
        payload = func(**kwargs)
    except Exception as exc:  # pragma: no cover - defensive, boring, useful
        return {"success": False, "label": label, "error": str(exc)}
    if isinstance(payload, dict):
        payload.setdefault("label", label)
        return payload
    return {"success": False, "label": label, "error": "non-dict payload"}


def build_autostart_readiness(
    server_names: Iterable[str],
    *,
    root: str = "",
) -> dict[str, Any]:
    """Return a compact readiness packet for SharpEdge-managed MCP autostart."""
    matched = match_first_party_server_names(server_names)
    if not matched:
        return {
            "managed_server_names": [],
            "checks": [],
            "summary": "No SharpEdge first-party MCP servers in this autostart set.",
        }

    checks: list[dict[str, Any]] = []
    if _AUTHORITATIVE_SERVER in matched:
        from code_puppy.plugins.authority_gateway.tooling import (
            authority_gateway_status,
        )
        from code_puppy.plugins.droidpuppy_context_kit.tooling import (
            droidpuppy_context_doctor,
        )
        from code_puppy.plugins.project_os_supervisor.tooling import (
            project_os_bus_status,
        )

        checks.extend(
            [
                _safe_call("authority_gateway", authority_gateway_status),
                _safe_call("droidpuppy_context", droidpuppy_context_doctor, root=root),
                _safe_call("project_os_bus", project_os_bus_status),
            ]
        )

    if _ANDROID_SERVER in matched:
        from code_puppy.plugins.droidpuppy_doctor.tooling import droidpuppy_doctor

        checks.append(_safe_call("droidpuppy_doctor", droidpuppy_doctor, deep=False))

    healthy = sum(1 for check in checks if check.get("success", True))
    return {
        "managed_server_names": matched,
        "checks": checks,
        "summary": (
            f"SharpEdge MCP autostart touched {len(matched)} first-party server(s); "
            f"{healthy}/{len(checks) or 1} readiness checks succeeded."
        ),
    }
