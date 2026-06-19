"""Read-only runnable Project Run candidate projection."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from . import store, validator

RUNNABLE_STATUSES = {"ready", "sleeping"}

_STATUS_EXCLUSION_REASONS = {
    "created": "not admitted as runnable work yet",
    "running": "already has execution attention",
    "waiting_event": "waiting for an Event Queue trigger; no mutable queue exists yet",
    "waiting_approval": "waiting for approval; scheduler cannot bypass approval",
    "blocked": "blocked; scheduler cannot bypass blocker evidence",
    "suspended": "suspended by policy or operator choice",
    "completed": "terminal completed run is not schedulable",
    "failed": "failed run requires operator triage or retry evidence",
    "archived": "archived historical run is not schedulable",
}


@dataclass(frozen=True, slots=True)
class RuntimeCandidate:
    """One Project Run that a future scheduler could consider."""

    run_id: str
    project: str
    objective: str
    status: str
    reason: str


@dataclass(frozen=True, slots=True)
class RuntimeExclusion:
    """One Project Run excluded from the runnable candidate projection."""

    run_id: str
    project: str
    objective: str
    status: str
    reason: str
    law: str = ""
    detail: str = ""
    precedent_id: str = ""
    remedy: str = ""


@dataclass(frozen=True, slots=True)
class CandidateProjection:
    """Read-only runtime docket produced from Project Runs and validation."""

    validation_passed: bool
    run_count: int
    event_count: int
    candidates: tuple[RuntimeCandidate, ...]
    exclusions: tuple[RuntimeExclusion, ...]


def _raw_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, dict) else {}


def _text(raw: Mapping[str, Any], key: str) -> str:
    return str(raw.get(key) or "").strip()


def _run_fields(key: str, raw: Any) -> tuple[str, str, str, str]:
    if not isinstance(raw, dict):
        return key, "(unknown)", "(unknown)", "(malformed)"
    run_id = _text(raw, "run_id") or key
    project = _text(raw, "project") or "(unknown)"
    objective = _text(raw, "objective") or "(unknown)"
    status = _text(raw, "status") or "(missing)"
    try:
        status = store.normalize_status(status)
    except ValueError:
        pass
    return run_id, project, objective, status


def _violations_by_run(
    report: validator.ValidationReport,
) -> dict[str, list[validator.ValidationViolation]]:
    grouped: dict[str, list[validator.ValidationViolation]] = defaultdict(list)
    for violation in report.violations:
        if violation.run_id:
            grouped[violation.run_id].append(violation)
    return grouped


def _exclusion_from_violation(
    *,
    run_id: str,
    project: str,
    objective: str,
    status: str,
    violation: validator.ValidationViolation,
) -> RuntimeExclusion:
    return RuntimeExclusion(
        run_id=run_id,
        project=project,
        objective=objective,
        status=status,
        reason="validator violation blocks runtime progression",
        law=violation.law,
        detail=violation.detail,
        precedent_id=violation.precedent_id,
        remedy=violation.remedy,
    )


def _status_exclusion(
    *, run_id: str, project: str, objective: str, status: str
) -> RuntimeExclusion:
    reason = _STATUS_EXCLUSION_REASONS.get(status, "unknown or invalid state")
    return RuntimeExclusion(
        run_id=run_id,
        project=project,
        objective=objective,
        status=status,
        reason=reason,
    )


def project_candidates(state: Mapping[str, Any] | None = None) -> CandidateProjection:
    """Return the read-only runnable candidate projection.

    This never mutates, claims, leases, wakes, repairs, or schedules anything.
    """
    raw_state = store.load_state() if state is None else state
    report = validator.validate_state(raw_state)
    raw_runs = _raw_mapping(raw_state.get("runs"))
    violations_by_run = _violations_by_run(report)

    candidates: list[RuntimeCandidate] = []
    exclusions: list[RuntimeExclusion] = []

    sorted_runs = sorted(
        raw_runs.items(),
        key=lambda item: (
            _text(item[1], "updated_at") if isinstance(item[1], dict) else "",
            str(item[0]),
        ),
        reverse=True,
    )
    for key, raw in sorted_runs:
        run_id, project, objective, status = _run_fields(str(key), raw)
        run_violations = violations_by_run.get(str(key), []) or violations_by_run.get(
            run_id, []
        )
        if run_violations:
            exclusions.append(
                _exclusion_from_violation(
                    run_id=run_id,
                    project=project,
                    objective=objective,
                    status=status,
                    violation=run_violations[0],
                )
            )
            continue
        if not report.passed:
            exclusions.append(
                RuntimeExclusion(
                    run_id=run_id,
                    project=project,
                    objective=objective,
                    status=status,
                    reason="validator FAIL blocks all runtime progression",
                )
            )
            continue
        if status in RUNNABLE_STATUSES:
            candidates.append(
                RuntimeCandidate(
                    run_id=run_id,
                    project=project,
                    objective=objective,
                    status=status,
                    reason=f"runnable: status {status!r} with validator PASS",
                )
            )
            continue
        exclusions.append(
            _status_exclusion(
                run_id=run_id,
                project=project,
                objective=objective,
                status=status,
            )
        )

    return CandidateProjection(
        validation_passed=report.passed,
        run_count=report.run_count,
        event_count=report.event_count,
        candidates=tuple(candidates),
        exclusions=tuple(exclusions),
    )


def format_projection(projection: CandidateProjection) -> str:
    """Render the runnable candidate projection for operators."""
    status = "PASS" if projection.validation_passed else "FAIL"
    lines = [
        "Project Run Candidates",
        "",
        f"validator: {status}",
        f"checked  : {projection.run_count} run(s), {projection.event_count} event(s)",
        "",
        "Candidates:",
    ]
    if not projection.candidates:
        lines.append("- (none)")
    for candidate in projection.candidates:
        lines.extend(
            [
                f"- {candidate.run_id}",
                f"  project  : {candidate.project}",
                f"  objective: {candidate.objective}",
                f"  status   : {candidate.status}",
                f"  reason   : {candidate.reason}",
            ]
        )
    lines.extend(["", "Excluded:"])
    if not projection.exclusions:
        lines.append("- (none)")
    for exclusion in projection.exclusions:
        lines.extend(
            [
                f"- {exclusion.run_id}",
                f"  project  : {exclusion.project}",
                f"  objective: {exclusion.objective}",
                f"  status   : {exclusion.status}",
                f"  reason   : {exclusion.reason}",
            ]
        )
        if exclusion.law:
            lines.append(f"  law      : {exclusion.law}")
        if exclusion.precedent_id:
            lines.append(f"  precedent: {exclusion.precedent_id}")
        if exclusion.remedy:
            lines.append(f"  remedy   : {exclusion.remedy}")
        if exclusion.detail:
            lines.append(f"  detail   : {exclusion.detail}")
    return "\n".join(lines)
