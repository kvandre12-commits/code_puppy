"""Lease persistence helpers for Project OS."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from . import store


@dataclass(frozen=True, slots=True)
class LeaseRecord:
    """Short-lived one-shot operational authority."""

    lease_id: str
    run_id: str
    subject_identity: str
    action_scope: str
    capability_scope: str
    issued_at: str
    expires_at: str
    consumed_at: str = ""
    issued_event_id: str = ""
    consumed_event_id: str = ""
    reason: str = ""


@dataclass(frozen=True, slots=True)
class LeaseWriteResult:
    """Lease mutation result with audit event evidence."""

    lease: LeaseRecord
    event: store.EventRecord


def lease_from_dict(raw: Mapping[str, Any]) -> LeaseRecord:
    """Create a LeaseRecord from raw state."""
    return LeaseRecord(
        lease_id=str(raw.get("lease_id") or ""),
        run_id=str(raw.get("run_id") or ""),
        subject_identity=str(raw.get("subject_identity") or ""),
        action_scope=str(raw.get("action_scope") or ""),
        capability_scope=str(raw.get("capability_scope") or ""),
        issued_at=str(raw.get("issued_at") or ""),
        expires_at=str(raw.get("expires_at") or ""),
        consumed_at=str(raw.get("consumed_at") or ""),
        issued_event_id=str(raw.get("issued_event_id") or ""),
        consumed_event_id=str(raw.get("consumed_event_id") or ""),
        reason=str(raw.get("reason") or ""),
    )


def lease_to_dict(lease: LeaseRecord) -> dict[str, Any]:
    """Serialize a LeaseRecord."""
    return asdict(lease)


def parse_time(value: str) -> datetime | None:
    """Parse an ISO-ish timestamp."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def list_leases(state: Mapping[str, Any] | None = None) -> tuple[LeaseRecord, ...]:
    """Return persisted leases sorted by lease_id."""
    raw_state = state if state is not None else store.load_state()
    raw_leases = raw_state.get("leases", {})
    if not isinstance(raw_leases, dict):
        return ()
    leases = tuple(
        lease_from_dict(raw) for raw in raw_leases.values() if isinstance(raw, dict)
    )
    return tuple(sorted(leases, key=lambda lease: lease.lease_id))


def get_lease(lease_id: str) -> LeaseRecord:
    """Load one lease by ID."""
    raw = store.load_state().get("leases", {}).get(lease_id)
    if not isinstance(raw, dict):
        raise KeyError(f"Lease not found: {lease_id}")
    return lease_from_dict(raw)


def create_lease_record(record: Mapping[str, str]) -> LeaseWriteResult:
    """Persist a lease and its lease_issued audit event."""
    lease = lease_from_dict(record)
    if not lease.lease_id:
        raise ValueError("lease_id is required")
    if not lease.run_id:
        raise ValueError("run_id is required")
    store.get_run(lease.run_id)
    state = store.load_state()
    leases = state.setdefault("leases", {})
    if lease.lease_id in leases:
        raise ValueError(f"Lease already exists: {lease.lease_id}")
    event = store.append_event_to_state(
        state,
        run_id=lease.run_id,
        event_type="lease_issued",
        payload_summary=f"Lease issued: {lease.lease_id}",
    )
    final_lease = LeaseRecord(
        **{**lease_to_dict(lease), "issued_event_id": event.event_id}
    )
    leases[final_lease.lease_id] = lease_to_dict(final_lease)
    store.save_state(state)
    return LeaseWriteResult(lease=final_lease, event=event)


def consume_lease_for_noop(lease: LeaseRecord) -> LeaseWriteResult:
    """Mark one lease consumed and write the no-op execution event."""
    state = store.load_state()
    leases = state.setdefault("leases", {})
    if lease.lease_id not in leases:
        raise KeyError(f"Lease not found: {lease.lease_id}")
    current = lease_from_dict(leases[lease.lease_id])
    if current.consumed_at:
        raise ValueError(f"Lease already consumed: {lease.lease_id}")
    event = store.append_event_to_state(
        state,
        run_id=current.run_id,
        event_type="noop_executed",
        payload_summary=f"No-op executed under lease: {current.lease_id}",
        parent_event_id=current.issued_event_id,
    )
    consumed = LeaseRecord(
        **{
            **lease_to_dict(current),
            "consumed_at": event.timestamp,
            "consumed_event_id": event.event_id,
        }
    )
    leases[consumed.lease_id] = lease_to_dict(consumed)
    store.save_state(state)
    return LeaseWriteResult(lease=consumed, event=event)
