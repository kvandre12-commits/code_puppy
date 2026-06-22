from __future__ import annotations

from typing import Any

from .anomaly import get_active_quarantines, release_quarantine
from .audit import (
    list_authority_events,
    read_recent_authority_events,
    revoke_all_leases_with_audit,
)
from .lease_store import get_default_principal_id, get_eyes_root, iter_active_leases

STATUS_WINDOW_SECONDS = 300
DEFAULT_AUDIT_LIMIT = 20


def _serialize_lease(record: Any) -> dict[str, Any]:
    return {
        "lease_id": record.lease_id,
        "principal_id": record.principal_id,
        "status": record.status,
        "capabilities": record.capabilities,
        "allowed_tools": record.allowed_tools,
        "constraints": record.constraints,
        "quotas": record.quotas,
        "remaining_uses": record.remaining_uses,
        "not_before": record.payload.get("not_before"),
        "expires_at": record.payload.get("expires_at"),
        "last_used_at": record.payload.get("last_used_at"),
        "path": str(record.path),
    }


def _active_leases(principal_id: str = "") -> list[dict[str, Any]]:
    leases = []
    for record in iter_active_leases():
        if principal_id and record.principal_id != principal_id:
            continue
        leases.append(_serialize_lease(record))
    return leases


def _format_audit_event(event: dict[str, Any]) -> str:
    event_type = str(event.get("event_type", ""))
    tool_name = str(event.get("tool_name", "") or "-")
    lease_id = str(event.get("lease_id", "") or "-")
    reason = str(event.get("reason", "") or "")
    details = event.get("details") if isinstance(event.get("details"), dict) else {}
    timestamp = str(event.get("timestamp", ""))
    principal_id = str(event.get("principal_id", "") or "*")

    if event_type == "tool_allowed":
        label = "ALLOWED"
        summary = tool_name
    elif event_type == "tool_blocked":
        label = "BLOCKED"
        summary = f"{tool_name} ({details.get('block_kind', 'policy')})"
    elif event_type == "anomaly_detected":
        label = "TRIPPED"
        summary = f"circuit_breaker ({details.get('signature', 'unknown')})"
    elif event_type == "lease_revoked":
        label = "REVOKED"
        summary = f"lease {lease_id}"
    elif event_type == "leases_revoked":
        label = "REVOKED_ALL"
        summary = f"leases x{details.get('count', 0)}"
    elif event_type == "lease_consumed":
        label = "CONSUMED"
        summary = f"lease {lease_id} via {tool_name}"
    elif event_type == "tool_failed":
        label = "FAILED"
        summary = tool_name
    elif event_type == "quarantine_released":
        label = "RELEASED"
        summary = "quarantine"
    elif event_type == "lease_minted":
        label = "MINTED"
        summary = f"lease {lease_id}"
    elif event_type == "review_decision":
        label = "REVIEW"
        summary = str(details.get("decision", "decision"))
    else:
        label = event_type.upper() or "EVENT"
        summary = tool_name if tool_name != "-" else lease_id

    suffix = f" :: {reason}" if reason else ""
    return f"[{label}] {timestamp} principal={principal_id} {summary}{suffix}"


def _execution_topology_snapshot() -> dict[str, Any]:
    try:
        from code_puppy.plugins.droidpuppy_doctor.tooling import droidpuppy_doctor

        result = droidpuppy_doctor(deep=False)
    except Exception as exc:
        return {
            "success": False,
            "error": f"droidpuppy_doctor unavailable: {exc}",
        }

    inventory = (
        result.get("surface_inventory")
        if isinstance(result.get("surface_inventory"), dict)
        else {}
    )
    surfaces = (
        inventory.get("surfaces") if isinstance(inventory.get("surfaces"), list) else []
    )
    ready_surface_ids = [
        str(surface.get("surface_id"))
        for surface in surfaces
        if isinstance(surface, dict) and surface.get("availability") == "ready"
    ]
    blocked_surfaces = [
        {
            "surface_id": str(surface.get("surface_id")),
            "blockers": list(surface.get("blockers") or []),
        }
        for surface in surfaces
        if isinstance(surface, dict) and surface.get("availability") == "blocked"
    ]
    summary = (
        inventory.get("summary") if isinstance(inventory.get("summary"), dict) else {}
    )

    return {
        "success": True,
        "overall_status": result.get("overall_status"),
        "deep_probe_ran": bool(result.get("deep_probe_ran")),
        "ready_surface_count": int(summary.get("ready", 0) or 0),
        "blocked_surface_count": int(summary.get("blocked", 0) or 0),
        "connected_adb_devices": int(inventory.get("connected_adb_devices", 0) or 0),
        "ready_surface_ids": ready_surface_ids,
        "blocked_surfaces": blocked_surfaces,
        "capability_routes": inventory.get("capability_routes")
        if isinstance(inventory.get("capability_routes"), list)
        else [],
    }


def authority_gateway_status() -> dict[str, Any]:
    active_leases = _active_leases()
    quarantines = [entry.as_dict() for entry in get_active_quarantines()]
    recent_anomalies = read_recent_authority_events(
        event_types={"anomaly_detected"},
        window_seconds=STATUS_WINDOW_SECONDS,
    )
    recent_blocks = read_recent_authority_events(
        event_types={"tool_blocked"},
        window_seconds=STATUS_WINDOW_SECONDS,
    )

    if quarantines:
        system_state = "contained"
    elif active_leases:
        system_state = "armed"
    else:
        system_state = "idle"

    execution_topology = _execution_topology_snapshot()
    topology_summary_bits: list[str] = []
    if execution_topology.get("success"):
        topology_summary_bits.extend(
            [
                f"surface_ready={execution_topology['ready_surface_count']}",
                f"surface_blocked={execution_topology['blocked_surface_count']}",
                f"adb_devices={execution_topology['connected_adb_devices']}",
            ]
        )
    else:
        topology_summary_bits.append("surface_topology=unavailable")

    return {
        "success": True,
        "system_state": system_state,
        "eyes_root": str(get_eyes_root()),
        "default_principal_id": get_default_principal_id(),
        "active_lease_count": len(active_leases),
        "quarantine_count": len(quarantines),
        "recent_anomaly_count": len(recent_anomalies),
        "recent_blocked_count": len(recent_blocks),
        "active_principals": sorted(
            {
                lease["principal_id"]
                for lease in active_leases
                if isinstance(lease.get("principal_id"), str) and lease["principal_id"]
            }
        ),
        "quarantined_principals": [
            entry["principal_id"] for entry in quarantines if entry.get("principal_id")
        ],
        "execution_topology": execution_topology,
        "summary": "; ".join(
            [
                f"state={system_state}",
                f"active_leases={len(active_leases)}",
                f"quarantines={len(quarantines)}",
                f"recent_anomalies={len(recent_anomalies)}",
                *topology_summary_bits,
            ]
        ),
    }


def authority_gateway_list_active_leases(principal_id: str = "") -> dict[str, Any]:
    leases = _active_leases(principal_id=principal_id)
    return {
        "success": True,
        "count": len(leases),
        "principal_filter": principal_id or None,
        "leases": leases,
    }


def authority_gateway_quarantine_status(principal_id: str = "") -> dict[str, Any]:
    quarantines = [
        entry.as_dict()
        for entry in get_active_quarantines(principal_id=principal_id or None)
    ]
    return {
        "success": True,
        "count": len(quarantines),
        "principal_filter": principal_id or None,
        "quarantines": quarantines,
    }


def authority_gateway_recent_audit(
    limit: int = DEFAULT_AUDIT_LIMIT,
    principal_id: str = "",
) -> dict[str, Any]:
    events = list_authority_events(
        limit=max(1, int(limit)),
        principal_id=principal_id or None,
    )
    timeline_lines = [_format_audit_event(event) for event in events]
    return {
        "success": True,
        "count": len(events),
        "principal_filter": principal_id or None,
        "timeline": "\n".join(timeline_lines),
        "lines": timeline_lines,
        "events": events,
    }


def authority_gateway_release_quarantine(
    principal_id: str,
    reason: str = "Manual operator quarantine release.",
    released_by: str = "operator",
) -> dict[str, Any]:
    if not principal_id.strip():
        return {
            "success": False,
            "released": False,
            "reason": "principal_id is required",
        }
    result = release_quarantine(
        principal_id=principal_id.strip(),
        reason=reason,
        released_by=released_by,
    )
    return {"success": bool(result.get("released")), **result}


def authority_gateway_revoke_all(
    principal_id: str = "",
    reason: str = "Manual operator revoke-all override.",
    revoked_by: str = "operator",
) -> dict[str, Any]:
    revoked = revoke_all_leases_with_audit(
        reason,
        revoked_by=revoked_by,
        principal_id=principal_id or None,
    )
    return {
        "success": True,
        "principal_filter": principal_id or None,
        "reason": reason,
        "revoked_by": revoked_by,
        "count": len(revoked),
        "lease_ids": [record.lease_id for record in revoked],
    }
