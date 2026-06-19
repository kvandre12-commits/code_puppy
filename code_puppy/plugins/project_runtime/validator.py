"""Read-only Project OS validator.

The validator is intentionally boring: it reports violations but never mutates,
repairs, normalizes, or backfills Project Run state.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from . import store


@dataclass(frozen=True, slots=True)
class ValidationViolation:
    """One Project OS law violation."""

    law: str
    detail: str
    run_id: str = ""
    event_id: str = ""


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Read-only validation result."""

    run_count: int
    event_count: int
    violations: tuple[ValidationViolation, ...]

    @property
    def passed(self) -> bool:
        return not self.violations


LEGAL_TRANSITIONS: dict[str, set[str]] = {
    "created": {"ready", "sleeping", "blocked", "waiting_approval", "archived"},
    "ready": {
        "running",
        "sleeping",
        "blocked",
        "waiting_event",
        "waiting_approval",
        "archived",
    },
    "running": {
        "sleeping",
        "blocked",
        "waiting_event",
        "waiting_approval",
        "completed",
        "failed",
        "suspended",
    },
    "sleeping": {
        "ready",
        "running",
        "blocked",
        "waiting_event",
        "waiting_approval",
        "archived",
    },
    "waiting_event": {
        "ready",
        "running",
        "blocked",
        "waiting_approval",
        "archived",
    },
    "waiting_approval": {"ready", "running", "blocked", "archived"},
    "blocked": {"ready", "waiting_approval", "suspended", "failed", "archived"},
    "suspended": {"ready", "sleeping", "archived"},
    "failed": {"ready", "archived"},
    "completed": {"archived"},
    "archived": set(),
}

_EVENT_TRANSITION_TARGETS = {
    "project_run_resumed": "running",
    "project_run_slept": "sleeping",
    "project_run_completed": "completed",
    "run_blocked": "blocked",
    "approval_requested": "waiting_approval",
}

_TERMINAL_EVENTS = {"project_run_completed"}
_ACTIVE_AFTER_TERMINAL_EVENTS = {
    "project_run_resumed",
    "project_run_slept",
    "checkpoint_saved",
    "run_blocked",
    "run_unblocked",
    "approval_requested",
    "approval_granted",
}


def _violation(
    violations: list[ValidationViolation],
    law: str,
    detail: str,
    *,
    run_id: str = "",
    event_id: str = "",
) -> None:
    violations.append(
        ValidationViolation(law=law, detail=detail, run_id=run_id, event_id=event_id)
    )


def _raw_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, dict) else {}


def _validate_runs(
    raw_runs: Mapping[str, Any], violations: list[ValidationViolation]
) -> set[str]:
    run_ids: set[str] = set()
    for key, raw in raw_runs.items():
        run_id = str(key)
        run_ids.add(run_id)
        if not isinstance(raw, dict):
            _violation(
                violations,
                "Every Project Run must be a structured record.",
                "run entry is not an object",
                run_id=run_id,
            )
            continue
        stored_run_id = str(raw.get("run_id") or "")
        if stored_run_id and stored_run_id != run_id:
            _violation(
                violations,
                "Every Project Run has one stable run_id.",
                f"run key {run_id!r} does not match stored run_id {stored_run_id!r}",
                run_id=run_id,
            )
        status = str(raw.get("status") or "")
        try:
            store.normalize_status(status)
        except ValueError as exc:
            _violation(
                violations,
                "Every Project Run has exactly one valid current state.",
                str(exc),
                run_id=run_id,
            )
    return run_ids


def _validate_events(
    raw_events: Mapping[str, Any],
    run_ids: set[str],
    violations: list[ValidationViolation],
) -> None:
    for key, raw in raw_events.items():
        event_id = str(key)
        if not isinstance(raw, dict):
            _violation(
                violations,
                "Every Event Record must be a structured record.",
                "event entry is not an object",
                event_id=event_id,
            )
            continue
        stored_event_id = str(raw.get("event_id") or "")
        if stored_event_id and stored_event_id != event_id:
            _violation(
                violations,
                "Every Event Record has one stable event_id.",
                f"event key {event_id!r} does not match stored event_id {stored_event_id!r}",
                event_id=event_id,
            )
        run_id = str(raw.get("run_id") or "")
        event_type = str(raw.get("event_type") or "")
        try:
            store.normalize_event_type(event_type)
        except ValueError as exc:
            _violation(
                violations,
                "Every Event Record has exactly one known Event Type.",
                str(exc),
                run_id=run_id,
                event_id=event_id,
            )
        source = str(raw.get("source") or "").strip()
        if not source:
            _violation(
                violations,
                "Every Event Record must have source attribution.",
                "event source is empty",
                run_id=run_id,
                event_id=event_id,
            )
        if run_id not in run_ids:
            _violation(
                violations,
                "Every Event Record belongs to exactly one existing Project Run.",
                f"event references missing run_id {run_id!r}",
                run_id=run_id,
                event_id=event_id,
            )
        parent_event_id = str(raw.get("parent_event_id") or "")
        if parent_event_id and parent_event_id not in raw_events:
            _violation(
                violations,
                "Event causality must point to an existing Event Record.",
                f"parent_event_id {parent_event_id!r} does not exist",
                run_id=run_id,
                event_id=event_id,
            )


def _validate_causality_acyclic(
    raw_events: Mapping[str, Any], violations: list[ValidationViolation]
) -> None:
    for event_id in raw_events:
        seen: set[str] = set()
        current_id = str(event_id)
        while current_id:
            if current_id in seen:
                _violation(
                    violations,
                    "Event causality must remain acyclic.",
                    f"cycle detected at {current_id!r}",
                    event_id=str(event_id),
                )
                break
            seen.add(current_id)
            raw = raw_events.get(current_id)
            if not isinstance(raw, dict):
                break
            parent_id = str(raw.get("parent_event_id") or "")
            if parent_id and parent_id not in raw_events:
                break
            current_id = parent_id


def _events_by_run(raw_events: Mapping[str, Any]) -> dict[str, list[store.EventRecord]]:
    grouped: dict[str, list[store.EventRecord]] = defaultdict(list)
    for key, raw in raw_events.items():
        if not isinstance(raw, dict):
            continue
        event = store.event_from_dict(
            {**raw, "event_id": str(raw.get("event_id") or key)}
        )
        grouped[event.run_id].append(event)
    for events in grouped.values():
        events.sort(key=lambda event: (event.timestamp, event.event_id))
    return grouped


def _validate_known_transition(
    from_status: str,
    to_status: str,
    event: store.EventRecord,
    violations: list[ValidationViolation],
) -> str:
    if to_status not in LEGAL_TRANSITIONS.get(from_status, set()):
        _violation(
            violations,
            "Every state transition follows the legal lifecycle graph.",
            f"illegal transition {from_status} -> {to_status} via {event.event_type}",
            run_id=event.run_id,
            event_id=event.event_id,
        )
    return to_status


def _validate_run_event_sequence(
    run_id: str,
    events: list[store.EventRecord],
    violations: list[ValidationViolation],
) -> None:
    inferred_status = ""
    pending_block_event = ""
    pending_approval_event = ""
    approval_resolution_event = ""
    terminal_event = ""

    for event in events:
        if event.event_type == "run_created":
            # Current Event Records do not persist the initial status chosen at
            # creation time. Avoid inventing an implicit transition here; only
            # enforce transitions when later events provide explicit evidence.
            continue

        if terminal_event and event.event_type in _ACTIVE_AFTER_TERMINAL_EVENTS:
            _violation(
                violations,
                "Terminal states are not resumable by default.",
                f"{event.event_type} appears after terminal event {terminal_event}",
                run_id=run_id,
                event_id=event.event_id,
            )

        if pending_block_event and event.event_type == "project_run_resumed":
            _violation(
                violations,
                "A blocked run cannot resume without run_unblocked causality.",
                f"project_run_resumed appears after blocker {pending_block_event}",
                run_id=run_id,
                event_id=event.event_id,
            )
        if pending_approval_event and event.event_type == "project_run_resumed":
            _violation(
                violations,
                "A waiting_approval run cannot resume without approval_granted causality.",
                f"project_run_resumed appears after approval request {pending_approval_event}",
                run_id=run_id,
                event_id=event.event_id,
            )

        if event.event_type == "run_unblocked":
            if not pending_block_event and not approval_resolution_event:
                _violation(
                    violations,
                    "Unblock transitions require blocker or approval evidence.",
                    "run_unblocked appears without a preceding run_blocked or approval_granted",
                    run_id=run_id,
                    event_id=event.event_id,
                )
            pending_block_event = ""
            approval_resolution_event = ""
            if inferred_status == "blocked":
                inferred_status = "ready"
            continue

        if event.event_type == "approval_granted":
            if not pending_approval_event:
                _violation(
                    violations,
                    "Approval grants require a preceding approval request.",
                    "approval_granted appears without approval_requested",
                    run_id=run_id,
                    event_id=event.event_id,
                )
            pending_approval_event = ""
            approval_resolution_event = event.event_id
            if inferred_status == "waiting_approval":
                inferred_status = "ready"
            continue

        to_status = _EVENT_TRANSITION_TARGETS.get(event.event_type)
        if to_status:
            if inferred_status:
                inferred_status = _validate_known_transition(
                    inferred_status, to_status, event, violations
                )
            else:
                inferred_status = to_status
            if event.event_type == "run_blocked":
                pending_block_event = event.event_id
            if event.event_type == "approval_requested":
                pending_approval_event = event.event_id
            if event.event_type in _TERMINAL_EVENTS:
                terminal_event = event.event_id


def _validate_current_status_has_event_evidence(
    raw_runs: Mapping[str, Any],
    events_by_run: Mapping[str, list[store.EventRecord]],
    violations: list[ValidationViolation],
) -> None:
    required_event_by_status = {
        "running": "project_run_resumed",
        "completed": "project_run_completed",
        "blocked": "run_blocked",
        "waiting_approval": "approval_requested",
    }
    for run_id, raw in raw_runs.items():
        if not isinstance(raw, dict):
            continue
        status = str(raw.get("status") or "")
        try:
            normalized_status = store.normalize_status(status)
        except ValueError:
            continue
        required_event = required_event_by_status.get(normalized_status)
        if not required_event:
            continue
        event_types = {event.event_type for event in events_by_run.get(str(run_id), [])}
        if required_event not in event_types:
            _violation(
                violations,
                "Every state transition is caused by an Event Record.",
                f"status {normalized_status!r} has no {required_event} evidence",
                run_id=str(run_id),
            )


def validate_state(state: Mapping[str, Any] | None = None) -> ValidationReport:
    """Validate persisted Project OS state without mutating it."""
    raw_state = store.load_state() if state is None else state
    raw_runs = _raw_mapping(raw_state.get("runs"))
    raw_events = _raw_mapping(raw_state.get("events"))

    violations: list[ValidationViolation] = []
    run_ids = _validate_runs(raw_runs, violations)
    _validate_events(raw_events, run_ids, violations)
    _validate_causality_acyclic(raw_events, violations)

    events_by_run = _events_by_run(raw_events)
    for run_id, events in events_by_run.items():
        if run_id in run_ids:
            _validate_run_event_sequence(run_id, events, violations)
    _validate_current_status_has_event_evidence(raw_runs, events_by_run, violations)

    return ValidationReport(
        run_count=len(raw_runs),
        event_count=len(raw_events),
        violations=tuple(violations),
    )


def format_report(report: ValidationReport) -> str:
    """Render a validation report for operators."""
    status = "PASS" if report.passed else "FAIL"
    lines = [
        "Project OS Validation",
        "",
        f"status : {status}",
        f"checked: {report.run_count} run(s), {report.event_count} event(s)",
    ]
    if report.passed:
        lines.extend(["", "No violations."])
        return "\n".join(lines)

    lines.extend(["", "violations:"])
    for violation in report.violations:
        target = []
        if violation.run_id:
            target.append(f"run_id={violation.run_id}")
        if violation.event_id:
            target.append(f"event_id={violation.event_id}")
        target_text = " ".join(target) if target else "state=global"
        lines.append(f"- {target_text}")
        lines.append(f"  law   : {violation.law}")
        lines.append(f"  detail: {violation.detail}")
    return "\n".join(lines)
