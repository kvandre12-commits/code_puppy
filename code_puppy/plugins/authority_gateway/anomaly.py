from __future__ import annotations

import datetime as dt
import time
from dataclasses import dataclass
from typing import Any

from .audit import (
    emit_authority_event,
    read_recent_authority_events,
    revoke_all_leases_with_audit,
)

CONSTRAINT_BLOCK_THRESHOLD = 3
CONSTRAINT_BLOCK_WINDOW_SECONDS = 10
RUNAWAY_ATTEMPT_THRESHOLD = 20
RUNAWAY_ATTEMPT_WINDOW_SECONDS = 5
QUARANTINE_WINDOW_SECONDS = 60
RUNAWAY_TOOL_NAMES = {"agent_run_shell_command", "android_intent_send"}


@dataclass(frozen=True)
class AnomalyResult:
    tripped: bool = False
    reason: str = ""
    details: dict[str, Any] | None = None


@dataclass(frozen=True)
class QuarantineEntry:
    principal_id: str | None
    anomaly_event_id: str
    reason: str
    started_at: str
    expires_at: str
    seconds_remaining: int
    signature: str
    details: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "principal_id": self.principal_id,
            "anomaly_event_id": self.anomaly_event_id,
            "reason": self.reason,
            "started_at": self.started_at,
            "expires_at": self.expires_at,
            "seconds_remaining": self.seconds_remaining,
            "signature": self.signature,
            "details": self.details,
        }


def _constraint_block_events(principal_id: str | None) -> list[dict[str, Any]]:
    events = read_recent_authority_events(
        event_types={"tool_blocked"},
        window_seconds=CONSTRAINT_BLOCK_WINDOW_SECONDS,
    )
    filtered: list[dict[str, Any]] = []
    for event in events:
        if principal_id and event.get("principal_id") not in {None, principal_id}:
            continue
        details = event.get("details") if isinstance(event.get("details"), dict) else {}
        if details.get("block_kind") == "constraint":
            filtered.append(event)
    return filtered


def _runaway_attempt_events(principal_id: str | None) -> list[dict[str, Any]]:
    events = read_recent_authority_events(
        event_types={"tool_allowed"},
        window_seconds=RUNAWAY_ATTEMPT_WINDOW_SECONDS,
    )
    filtered: list[dict[str, Any]] = []
    for event in events:
        if principal_id and event.get("principal_id") not in {None, principal_id}:
            continue
        if str(event.get("tool_name", "")) in RUNAWAY_TOOL_NAMES:
            filtered.append(event)
    return filtered


def _principal_key(principal_id: str | None) -> str:
    return principal_id or ""


def _iso_from_ns(timestamp_ns: int) -> str:
    return dt.datetime.fromtimestamp(
        timestamp_ns / 1_000_000_000, tz=dt.timezone.utc
    ).isoformat()


def get_active_quarantines(*, principal_id: str | None = None) -> list[QuarantineEntry]:
    anomalies = read_recent_authority_events(
        event_types={"anomaly_detected"},
        window_seconds=QUARANTINE_WINDOW_SECONDS,
    )
    releases = read_recent_authority_events(
        event_types={"quarantine_released"},
        window_seconds=QUARANTINE_WINDOW_SECONDS,
    )
    latest_release_ns: dict[str, int] = {}
    for event in releases:
        key = _principal_key(
            str(event.get("principal_id")) if event.get("principal_id") else None
        )
        latest_release_ns[key] = max(
            latest_release_ns.get(key, 0), int(event.get("timestamp_ns", 0) or 0)
        )

    active_by_principal: dict[str, QuarantineEntry] = {}
    now_ns = time.time_ns()
    for event in anomalies:
        event_principal = (
            str(event.get("principal_id")) if event.get("principal_id") else None
        )
        if principal_id and event_principal != principal_id:
            continue

        details = event.get("details") if isinstance(event.get("details"), dict) else {}
        quarantine_seconds = int(
            details.get("quarantine_seconds", QUARANTINE_WINDOW_SECONDS) or 0
        )
        timestamp_ns = int(event.get("timestamp_ns", 0) or 0)
        expires_ns = timestamp_ns + (quarantine_seconds * 1_000_000_000)
        if expires_ns <= now_ns:
            continue

        key = _principal_key(event_principal)
        if latest_release_ns.get(key, 0) >= timestamp_ns:
            continue

        seconds_remaining = max(1, (expires_ns - now_ns + 999_999_999) // 1_000_000_000)
        active_by_principal[key] = QuarantineEntry(
            principal_id=event_principal,
            anomaly_event_id=str(event.get("event_id", "")),
            reason=str(event.get("reason", "")),
            started_at=str(event.get("timestamp", "")),
            expires_at=_iso_from_ns(expires_ns),
            seconds_remaining=int(seconds_remaining),
            signature=str(details.get("signature", "")),
            details=details,
        )

    return sorted(
        active_by_principal.values(),
        key=lambda item: (item.principal_id or "", item.expires_at),
    )


def active_quarantine_reason(*, principal_id: str | None = None) -> str | None:
    active = get_active_quarantines(principal_id=principal_id)
    if not active:
        return None
    entry = active[0]
    return (
        "[BLOCKED] Principal is quarantined after a recent security anomaly. "
        f"Wait {entry.seconds_remaining}s before retrying."
    )


def release_quarantine(
    *,
    principal_id: str,
    released_by: str = "operator",
    reason: str = "Manual operator quarantine release.",
) -> dict[str, Any]:
    active = get_active_quarantines(principal_id=principal_id)
    if not active:
        return {
            "released": False,
            "principal_id": principal_id,
            "reason": "No active quarantine found for principal.",
        }

    entry = active[0]
    event_path = emit_authority_event(
        "quarantine_released",
        principal_id=principal_id,
        outcome="released",
        reason=reason,
        details={
            "released_by": released_by,
            "released_anomaly_event_id": entry.anomaly_event_id,
            "released_signature": entry.signature,
            "seconds_remaining": entry.seconds_remaining,
        },
    )
    return {
        "released": True,
        "principal_id": principal_id,
        "released_by": released_by,
        "event_ref": str(event_path) if event_path else None,
        "released_anomaly_event_id": entry.anomaly_event_id,
        "reason": reason,
    }


def _trip_circuit_breaker(
    *,
    principal_id: str | None,
    reason: str,
    details: dict[str, Any],
) -> AnomalyResult:
    emit_authority_event(
        "anomaly_detected",
        principal_id=principal_id,
        outcome="tripped",
        reason=reason,
        details={**details, "quarantine_seconds": QUARANTINE_WINDOW_SECONDS},
    )
    revoked = revoke_all_leases_with_audit(
        reason,
        revoked_by="authority_gateway",
        principal_id=principal_id,
    )
    return AnomalyResult(
        tripped=True,
        reason=reason,
        details={**details, "revoked_lease_count": len(revoked)},
    )


def evaluate_runtime_anomalies(*, principal_id: str | None = None) -> AnomalyResult:
    constraint_blocks = _constraint_block_events(principal_id)
    if len(constraint_blocks) >= CONSTRAINT_BLOCK_THRESHOLD:
        return _trip_circuit_breaker(
            principal_id=principal_id,
            reason=(
                "[BLOCKED] Security isolation triggered after repeated execution "
                "constraint violations."
            ),
            details={
                "signature": "repeated_constraint_violations",
                "count": len(constraint_blocks),
                "window_seconds": CONSTRAINT_BLOCK_WINDOW_SECONDS,
                "event_ids": [
                    str(event.get("event_id", "")) for event in constraint_blocks
                ],
                "tool_names": [
                    str(event.get("tool_name", "")) for event in constraint_blocks
                ],
            },
        )

    runaway_attempts = _runaway_attempt_events(principal_id)
    if len(runaway_attempts) >= RUNAWAY_ATTEMPT_THRESHOLD:
        return _trip_circuit_breaker(
            principal_id=principal_id,
            reason=(
                "[BLOCKED] Security isolation triggered after detecting a runaway "
                "shell/intent execution loop."
            ),
            details={
                "signature": "runaway_tool_loop",
                "count": len(runaway_attempts),
                "window_seconds": RUNAWAY_ATTEMPT_WINDOW_SECONDS,
                "event_ids": [
                    str(event.get("event_id", "")) for event in runaway_attempts
                ],
                "tool_names": [
                    str(event.get("tool_name", "")) for event in runaway_attempts
                ],
            },
        )

    return AnomalyResult()
