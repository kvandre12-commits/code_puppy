"""Read-only Project Run lease draft report."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from . import dispatch_plan

REQUESTED_AGENT_IDENTITY = "unassigned_agent"
REQUESTED_ACTION_SCOPE = "project_run.execute_bounded_step"
REQUESTED_CAPABILITY_SCOPE = "project_runtime.step"
REQUIRED_AUTHORITY_CHECK = (
    "identity_exists + authority_grants_scope + capability_grants_scope"
)
PROPOSED_EXPIRY = "one_step_or_15_minutes"


@dataclass(frozen=True, slots=True)
class LeaseDraft:
    """Read-only authority request derived from a dispatch plan."""

    validation_passed: bool
    dispatch_plan_id: str
    run_id: str
    requested_agent_identity: str
    requested_action_scope: str
    requested_capability_scope: str
    required_authority_check: str
    proposed_expiry: str
    reason: str


def _dispatch_plan_id(plan: dispatch_plan.DispatchPlan) -> str:
    if not plan.selected:
        return ""
    return ":".join(
        (
            "dispatch-plan",
            plan.selected.run_id,
            plan.dispatch_action,
            plan.required_lease_scope,
        )
    )


def draft_lease(state: Mapping[str, Any] | None = None) -> LeaseDraft:
    """Draft a lease request without issuing authority or executing."""
    plan = dispatch_plan.plan_dispatch(state)
    selected = plan.selected

    if not plan.validation_passed:
        reason = "validator FAIL prevents lease drafting"
    elif not selected:
        reason = "no dispatch plan available for lease drafting"
    else:
        reason = "dispatch plan can proceed to authority review"

    return LeaseDraft(
        validation_passed=plan.validation_passed,
        dispatch_plan_id=_dispatch_plan_id(plan),
        run_id=selected.run_id if selected else "",
        requested_agent_identity=REQUESTED_AGENT_IDENTITY if selected else "",
        requested_action_scope=REQUESTED_ACTION_SCOPE if selected else "",
        requested_capability_scope=REQUESTED_CAPABILITY_SCOPE if selected else "",
        required_authority_check=REQUIRED_AUTHORITY_CHECK if selected else "",
        proposed_expiry=PROPOSED_EXPIRY if selected else "",
        reason=reason,
    )


def format_draft(draft: LeaseDraft) -> str:
    """Render a read-only lease draft report for operators."""
    validator_status = "PASS" if draft.validation_passed else "FAIL"
    lines = [
        "Project Run Lease Draft",
        "",
        f"validator               : {validator_status}",
        f"reason                  : {draft.reason}",
        "",
        "Draft:",
    ]
    if not draft.run_id:
        lines.append("- (none)")
        return "\n".join(lines)

    lines.extend(
        [
            f"- dispatch_plan_id        : {draft.dispatch_plan_id}",
            f"  run_id                  : {draft.run_id}",
            f"  requested_agent_identity: {draft.requested_agent_identity}",
            f"  requested_action_scope  : {draft.requested_action_scope}",
            f"  requested_capability    : {draft.requested_capability_scope}",
            f"  required_authority_check: {draft.required_authority_check}",
            f"  proposed_expiry         : {draft.proposed_expiry}",
            "  authorizes              : no",
            "  mutates                 : no",
            "  wakes                   : no",
            "  leases                  : no",
            "  executes                : no",
        ]
    )
    return "\n".join(lines)
