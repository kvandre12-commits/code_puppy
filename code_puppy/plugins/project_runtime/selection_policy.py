"""Read-only Project Run selection policy report."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from . import runtime_candidates

FIFO_POLICY = "fifo_updated_at_then_run_id"
_MISSING_UPDATED_AT = "9999-12-31T23:59:59+00:00"


@dataclass(frozen=True, slots=True)
class SelectionReport:
    """Read-only selection result over already-eligible candidates."""

    policy_name: str
    validation_passed: bool
    selected: runtime_candidates.RuntimeCandidate | None
    considered: tuple[runtime_candidates.RuntimeCandidate, ...]
    exclusions: tuple[runtime_candidates.RuntimeExclusion, ...]
    reason: str


def _candidate_order_key(
    candidate: runtime_candidates.RuntimeCandidate,
) -> tuple[str, str]:
    updated_at = candidate.updated_at or _MISSING_UPDATED_AT
    return updated_at, candidate.run_id


def select_candidate(state: Mapping[str, Any] | None = None) -> SelectionReport:
    """Select one candidate without mutating, dispatching, leasing, or executing."""
    projection = runtime_candidates.project_candidates(state)
    considered = tuple(sorted(projection.candidates, key=_candidate_order_key))
    selected = considered[0] if considered else None

    if not projection.validation_passed:
        reason = "validator FAIL prevents selection"
    elif not selected:
        reason = "no eligible candidates to select"
    else:
        reason = "selected oldest eligible candidate by updated_at; tie-breaker run_id"

    return SelectionReport(
        policy_name=FIFO_POLICY,
        validation_passed=projection.validation_passed,
        selected=selected,
        considered=considered,
        exclusions=projection.exclusions,
        reason=reason,
    )


def _format_candidate(candidate: runtime_candidates.RuntimeCandidate) -> list[str]:
    return [
        f"- {candidate.run_id}",
        f"  project   : {candidate.project}",
        f"  objective : {candidate.objective}",
        f"  status    : {candidate.status}",
        f"  updated_at: {candidate.updated_at or '(unknown)'}",
    ]


def format_report(report: SelectionReport) -> str:
    """Render the read-only Selection Policy report."""
    validator_status = "PASS" if report.validation_passed else "FAIL"
    lines = [
        "Project Run Selection",
        "",
        f"validator: {validator_status}",
        f"policy   : {report.policy_name}",
        f"reason   : {report.reason}",
        "",
        "Selected:",
    ]
    if report.selected:
        lines.extend(_format_candidate(report.selected))
    else:
        lines.append("- (none)")

    lines.extend(["", "Considered:"])
    if not report.considered:
        lines.append("- (none)")
    for candidate in report.considered:
        lines.extend(_format_candidate(candidate))

    lines.extend(["", "Excluded:"])
    if not report.exclusions:
        lines.append("- (none)")
    for exclusion in report.exclusions:
        lines.extend(
            [
                f"- {exclusion.run_id}",
                f"  status : {exclusion.status}",
                f"  reason : {exclusion.reason}",
            ]
        )
        if exclusion.remedy:
            lines.append(f"  remedy : {exclusion.remedy}")
    return "\n".join(lines)
