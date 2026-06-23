from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .anomaly import get_active_quarantines, release_quarantine
from .identity import get_execution_identity
from .audit import (
    emit_authority_event,
    list_authority_events,
    read_recent_authority_events,
    revoke_all_leases_with_audit,
)
from .lease_store import (
    get_default_principal_id,
    get_eyes_root,
    iter_active_leases,
    mint_lease,
)

STATUS_WINDOW_SECONDS = 300
DEFAULT_AUDIT_LIMIT = 20
_REPO_WRITE_CAPABILITIES = {"shell.repo.write"}


def _serialize_lease(record: Any) -> dict[str, Any]:
    return {
        "lease_id": record.lease_id,
        "principal_id": record.principal_id,
        "status": record.status,
        "capabilities": record.capabilities,
        "allowed_tools": record.allowed_tools,
        "constraints": record.constraints,
        "delegation": record.delegation,
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
    actor_id = str(details.get("actor_id", "") or "")
    run_id = str(details.get("run_id", "") or "")

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

    actor_suffix = f" actor={actor_id}" if actor_id else ""
    run_suffix = f" run={run_id}" if run_id else ""
    suffix = f" :: {reason}" if reason else ""
    return (
        f"[{label}] {timestamp} principal={principal_id}{actor_suffix}{run_suffix} "
        f"{summary}{suffix}"
    )


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
    identity = get_execution_identity()
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
        "default_authority_principal_id": identity.authority_principal_id,
        "current_actor_id": identity.actor_id,
        "current_run_id": identity.run_id,
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


def _resolve_grant_principal(
    principal_id: str,
    *,
    allow_nondefault_principal: bool,
) -> tuple[str, str | None]:
    stable_principal_id = get_default_principal_id()
    requested_principal_id = str(principal_id or "").strip()
    if not requested_principal_id:
        return stable_principal_id, None
    if requested_principal_id == stable_principal_id:
        return requested_principal_id, None

    identity = get_execution_identity()
    suspicious_values = {
        value for value in (identity.actor_id, identity.run_id) if value
    }
    if requested_principal_id in suspicious_values:
        mismatch_reason = "requested principal matches the current actor/run identity"
    else:
        mismatch_reason = (
            "requested principal differs from the stable authority principal"
        )

    if not allow_nondefault_principal:
        return "", (
            "Refusing to mint a lease for a nondefault principal without an explicit "
            "override. Requested principal_id="
            f"{requested_principal_id!r}; stable authority principal={stable_principal_id!r}; "
            f"reason={mismatch_reason}. Pass allow_nondefault_principal=True if you "
            "really mean to bypass the repo's normal authority wiring."
        )
    return requested_principal_id, None


def _normalize_grant_constraints(
    capabilities: list[str],
    constraints: dict[str, Any],
    *,
    repo_root: str,
) -> dict[str, Any]:
    normalized = dict(constraints)
    if _REPO_WRITE_CAPABILITIES & set(capabilities):
        allowed_paths = normalized.get("allowed_paths")
        if not isinstance(allowed_paths, list) or not any(
            str(value).strip() for value in allowed_paths
        ):
            normalized["allowed_paths"] = [
                str(Path(repo_root or ".").expanduser().resolve())
            ]
    return normalized


def authority_gateway_grant_lease(
    principal_id: str,
    capabilities: list[str],
    reason: str = "Manual operator lease grant.",
    granted_by: str = "operator",
    allowed_tools: list[str] | None = None,
    constraints_json: str = "",
    ttl_seconds: int = 3600,
    max_uses: int = 25,
    max_tool_calls: int | None = None,
    max_shell_commands: int | None = None,
    lease_id: str = "",
    requested_by_actor_id: str = "",
    delegated_by_actor_id: str = "",
    delegated_to_actor_ids: list[str] | None = None,
    run_id: str = "",
    repo_root: str = "",
    allow_nondefault_principal: bool = True,
) -> dict[str, Any]:
    """Mint a narrow execution lease.

    Prefer the stable authority principal (PROJECT_OS_AUTHORITY_PRINCIPAL_ID /
    canonical repo authority) for principal_id. Keep actor and run identities
    in delegation metadata so authority survives sub-agent/session rotation.

    For shell.repo.write, default allowed_paths to repo_root (or cwd) when the
    operator did not supply an explicit path constraint.
    """
    try:
        parsed_constraints = (
            json.loads(constraints_json) if constraints_json.strip() else {}
        )
    except json.JSONDecodeError as exc:
        return {
            "success": False,
            "granted": False,
            "reason": f"constraints_json must be valid JSON: {exc}",
        }

    resolved_principal_id, principal_error = _resolve_grant_principal(
        principal_id,
        allow_nondefault_principal=allow_nondefault_principal,
    )
    if principal_error:
        return {
            "success": False,
            "granted": False,
            "reason": principal_error,
        }

    constraints = _normalize_grant_constraints(
        capabilities,
        parsed_constraints,
        repo_root=repo_root,
    )

    try:
        record = mint_lease(
            principal_id=resolved_principal_id,
            capabilities=capabilities,
            reason=reason,
            granted_by=granted_by,
            allowed_tools=allowed_tools,
            constraints=constraints,
            ttl_seconds=ttl_seconds,
            max_uses=max_uses,
            max_tool_calls=max_tool_calls,
            max_shell_commands=max_shell_commands,
            lease_id=lease_id,
            delegation={
                "mode": (
                    "shared_authority"
                    if delegated_to_actor_ids or delegated_by_actor_id or run_id
                    else "direct"
                ),
                "requested_by_actor_id": requested_by_actor_id or None,
                "delegated_by_actor_id": delegated_by_actor_id or None,
                "delegated_to_actor_ids": delegated_to_actor_ids or [],
                "run_id": run_id or None,
            },
        )
    except ValueError as exc:
        return {
            "success": False,
            "granted": False,
            "reason": str(exc),
        }

    event_path = emit_authority_event(
        "lease_minted",
        principal_id=record.principal_id,
        lease_id=record.lease_id,
        outcome="minted",
        reason=reason,
        details={
            "granted_by": granted_by,
            "capabilities": record.capabilities,
            "allowed_tools": record.allowed_tools,
            "constraints": record.constraints,
            "delegation": record.delegation,
            "quotas": record.quotas,
        },
    )

    return {
        "success": True,
        "granted": True,
        "lease_id": record.lease_id,
        "principal_id": record.principal_id,
        "reason": reason,
        "granted_by": granted_by,
        "capabilities": record.capabilities,
        "allowed_tools": record.allowed_tools,
        "constraints": record.constraints,
        "delegation": record.delegation,
        "quotas": record.quotas,
        "not_before": record.payload.get("not_before"),
        "expires_at": record.payload.get("expires_at"),
        "path": str(record.path),
        "audit_event_path": str(event_path) if event_path else None,
    }


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
