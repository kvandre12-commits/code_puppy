from __future__ import annotations

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


def active_quarantine_reason(*, principal_id: str | None = None) -> str | None:
    events = read_recent_authority_events(
        event_types={"anomaly_detected"},
        window_seconds=QUARANTINE_WINDOW_SECONDS,
    )
    for event in reversed(events):
        if principal_id and event.get("principal_id") not in {None, principal_id}:
            continue
        return (
            "[BLOCKED] Principal is quarantined after a recent security anomaly. "
            f"Wait {QUARANTINE_WINDOW_SECONDS}s before retrying."
        )
    return None


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
