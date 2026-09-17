"""Conservative coordinator for governed durable memory mutation requests.

This module intentionally does not implement ``memory.promote`` writes yet. The
current Project OS governance store and Kennel knowledge store are separate
state domains, so a durable mutation must refuse until an atomicity seam exists.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from . import effect_specs, execution_preflight

MEMORY_PROMOTE_ACTION_SCOPE = effect_specs.MEMORY_PROMOTE.action_scope
MEMORY_PROMOTE_CAPABILITY_SCOPE = effect_specs.MEMORY_PROMOTE.capability_scope
MEMORY_MUTATION_REFUSAL_REASON = effect_specs.MEMORY_PROMOTE.availability_blocker


@dataclass(frozen=True, slots=True)
class MemoryMutationRequest:
    """Evidence required before a durable memory mutation may even be considered."""

    mutation_type: str
    source_evidence: str
    mutation_reason: str
    proposed_after_object: str
    before_object: str = ""
    project_wing: str = ""
    requesting_agent: str = ""


@dataclass(frozen=True, slots=True)
class MemoryMutationResult:
    """Result of coordinating one governed memory mutation request."""

    executed: bool
    lease_id: str
    run_id: str
    event_id: str
    mutation_type: str
    reason: str
    record: Mapping[str, str]
    blockers: tuple[str, ...]
    mutates_project_os: bool
    mutates_kennel: bool
    consumes_lease: bool
    creates_audit_event: bool


def _refused(
    *,
    lease_id: str,
    run_id: str = "",
    mutation_type: str,
    reason: str,
    record: Mapping[str, str] | None = None,
    blockers: tuple[str, ...],
) -> MemoryMutationResult:
    return MemoryMutationResult(
        executed=False,
        lease_id=lease_id,
        run_id=run_id,
        event_id="",
        mutation_type=mutation_type,
        reason=reason,
        record=record or {},
        blockers=blockers,
        mutates_project_os=False,
        mutates_kennel=False,
        consumes_lease=False,
        creates_audit_event=False,
    )


def coordinate_memory_promote(
    *,
    confirm_lease_id: str,
    source_evidence: str,
    mutation_reason: str,
    proposed_after_object: str,
    before_object: str = "",
    project_wing: str = "",
    requesting_agent: str = "",
    now_at: str | None = None,
) -> MemoryMutationResult:
    """Coordinate a governed ``memory.promote`` request without mutating state.

    Current implementation is deliberately conservative: it validates the lease
    and evidence, then refuses because no atomic transaction seam currently spans
    Project OS governance JSON and Kennel SQLite/FTS5 knowledge state.
    """
    request = MemoryMutationRequest(
        mutation_type=MEMORY_PROMOTE_ACTION_SCOPE,
        source_evidence=source_evidence.strip(),
        mutation_reason=mutation_reason.strip(),
        proposed_after_object=proposed_after_object.strip(),
        before_object=before_object.strip(),
        project_wing=project_wing.strip(),
        requesting_agent=requesting_agent.strip(),
    )

    preflight = execution_preflight.preflight_execution(
        effect=effect_specs.MEMORY_PROMOTE.name,
        confirm_lease_id=confirm_lease_id,
        arguments={
            "source_evidence": request.source_evidence,
            "mutation_reason": request.mutation_reason,
            "proposed_after_object": request.proposed_after_object,
            "before_object": request.before_object,
            "project_wing": request.project_wing,
            "requesting_agent": request.requesting_agent,
        },
        now_at=now_at,
    )
    if preflight.gate == "availability":
        reason = MEMORY_MUTATION_REFUSAL_REASON
    elif preflight.gate == "arguments":
        reason = "memory mutation blocked by missing evidence"
    elif preflight.blockers == ("lease missing",):
        reason = "lease not found; no memory mutation executed"
    else:
        reason = "memory mutation blocked by lease validation"
    return _refused(
        lease_id=preflight.lease_id,
        run_id=preflight.run_id,
        mutation_type=request.mutation_type,
        reason=reason,
        record=preflight.record,
        blockers=preflight.blockers,
    )


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def format_result(result: MemoryMutationResult) -> str:
    """Render a governed memory mutation coordination result."""
    lines = [
        "Project Run Coordinate Memory Mutation",
        "",
        f"executed                    : {_yes_no(result.executed)}",
        f"reason                      : {result.reason}",
        f"mutation_type               : {result.mutation_type}",
        f"lease_id                    : {result.lease_id or '(none)'}",
        f"run_id                      : {result.run_id or '(none)'}",
        f"event_id                    : {result.event_id or '(none)'}",
        "bounded_effect              : " + _yes_no(result.executed),
        "consumes_lease              : " + _yes_no(result.consumes_lease),
        "mutates_project_os          : " + _yes_no(result.mutates_project_os),
        "mutates_kennel              : " + _yes_no(result.mutates_kennel),
        "creates_audit_event         : " + _yes_no(result.creates_audit_event),
        "creates_grant               : no",
        "leases                      : no",
        "wakes                       : no",
    ]
    if result.blockers:
        lines.append("")
        lines.append("Blockers:")
        lines.extend(f"- {blocker}" for blocker in result.blockers)
    return "\n".join(lines)
