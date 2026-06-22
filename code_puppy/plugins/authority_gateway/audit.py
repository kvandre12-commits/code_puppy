from __future__ import annotations

import datetime as dt
import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Any

from code_puppy.plugins.project_os_supervisor.bus import (
    publish_project_os_event_best_effort,
)

from .identity import get_execution_identity
from .lease_store import (
    LeaseRecord,
    get_default_principal_id,
    get_eyes_root,
    revoke_all_active_leases,
)

try:
    import jsonschema
except Exception:  # pragma: no cover - best effort only
    jsonschema = None

REPO_ROOT = Path(__file__).resolve().parents[3]
AUDIT_SCHEMA = (
    REPO_ROOT / "DroidPuppy" / "contracts" / "v2" / "eyes_audit_event.schema.json"
)


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _audit_events_dir() -> Path:
    path = get_eyes_root() / "audit" / "events"
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_recent_authority_events(
    *, event_types: set[str] | None = None, window_seconds: int = 10
) -> list[dict[str, Any]]:
    cutoff_ns = time.time_ns() - (window_seconds * 1_000_000_000)
    events: list[dict[str, Any]] = []
    for path in sorted(_audit_events_dir().glob("*.json")):
        try:
            payload = _read_json(path)
        except Exception:
            continue
        if event_types and str(payload.get("event_type", "")) not in event_types:
            continue
        timestamp_ns = int(payload.get("timestamp_ns", 0) or 0)
        if timestamp_ns < cutoff_ns:
            continue
        events.append(payload)
    events.sort(key=lambda payload: int(payload.get("timestamp_ns", 0) or 0))
    return events


def list_authority_events(
    *,
    limit: int = 20,
    event_types: set[str] | None = None,
    principal_id: str | None = None,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for path in sorted(_audit_events_dir().glob("*.json")):
        try:
            payload = _read_json(path)
        except Exception:
            continue
        if event_types and str(payload.get("event_type", "")) not in event_types:
            continue
        if principal_id and payload.get("principal_id") != principal_id:
            continue
        events.append(payload)
    events.sort(key=lambda payload: int(payload.get("timestamp_ns", 0) or 0))
    if limit > 0:
        return events[-limit:]
    return events


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _write_json_new(path: Path, payload: dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _previous_event_sha() -> str | None:
    events = sorted(_audit_events_dir().glob("*.json"))
    if not events:
        return None
    latest = _read_json(events[-1])
    value = latest.get("event_sha256")
    return str(value) if value else None


def _validate(payload: dict[str, Any]) -> None:
    if jsonschema is None or not AUDIT_SCHEMA.is_file():
        return
    jsonschema.validate(payload, json.loads(AUDIT_SCHEMA.read_text()))


def emit_authority_event(
    event_type: str,
    *,
    principal_id: str | None = None,
    lease_id: str | None = None,
    capability: str | None = None,
    tool_name: str | None = None,
    outcome: str | None = None,
    reason: str = "",
    details: dict[str, Any] | None = None,
) -> Path | None:
    timestamp_ns = time.time_ns()
    identity = get_execution_identity()
    event_details = {**identity.as_details(), **(details or {})}
    event_core = {
        "contract_version": "2.0.0",
        "event_id": f"audit-{uuid.uuid4().hex[:10]}",
        "event_type": event_type,
        "principal_id": principal_id or identity.authority_principal_id,
        "lease_id": lease_id,
        "capability": capability,
        "tool_name": tool_name,
        "outcome": outcome,
        "reason": reason,
        "details": event_details,
        "timestamp": _now(),
        "timestamp_ns": timestamp_ns,
        "previous_event_sha256": _previous_event_sha(),
    }
    event = dict(event_core)
    event["event_sha256"] = _sha256_text(_canonical_json(event_core))
    try:
        _validate(event)
        path = _audit_events_dir() / f"{timestamp_ns}_{event['event_id']}.json"
        _write_json_new(path, event)
        publish_project_os_event_best_effort(
            "authority.audit",
            event_type,
            source="authority_gateway.audit",
            payload=event,
        )
        return path
    except Exception:
        return None


def revoke_all_leases_with_audit(
    reason: str,
    *,
    revoked_by: str = "system",
    principal_id: str | None = None,
) -> list[LeaseRecord]:
    principal = principal_id or get_default_principal_id()
    revoked = revoke_all_active_leases(
        reason=reason,
        revoked_by=revoked_by,
        principal_id=principal_id,
    )
    for record in revoked:
        emit_authority_event(
            "lease_revoked",
            principal_id=principal,
            lease_id=record.lease_id,
            outcome="revoked",
            reason=reason,
            details={
                "revoked_by": revoked_by,
                "status": record.status,
                "capabilities": record.capabilities,
            },
        )
    emit_authority_event(
        "leases_revoked",
        principal_id=principal,
        outcome="revoked",
        reason=reason,
        details={"count": len(revoked), "revoked_by": revoked_by},
    )
    return revoked
