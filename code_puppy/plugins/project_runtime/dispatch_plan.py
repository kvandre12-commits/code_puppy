"""Read-only Project Run dispatch plan report."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from . import runtime_candidates, selection_policy

DISPATCH_ACTION = "prepare_agent_lease_draft"
REQUIRED_LEASE_SCOPE = "one_bounded_project_run_step"
PROOF_EVENT_TYPE = "dispatch_planned"


@dataclass(frozen=True, slots=True)
class DispatchPlan:
    """Read-only dispatch plan for one selected Project Run."""

    validation_passed: bool
    selection_policy_name: str
    selected: runtime_candidates.RuntimeCandidate | None
    dispatch_action: str
    required_lease_scope: str
    proof_event_type: str
    reason: str


def plan_dispatch(state: Mapping[str, Any] | None = None) -> DispatchPlan:
    """Plan dispatch without mutating, waking, leasing, or executing."""
    selection = selection_policy.select_candidate(state)
    selected = selection.selected

    if not selection.validation_passed:
        reason = "validator FAIL prevents dispatch planning"
    elif not selected:
        reason = "no selected candidate to dispatch"
    else:
        reason = "selected candidate can proceed to lease draft planning"

    return DispatchPlan(
        validation_passed=selection.validation_passed,
        selection_policy_name=selection.policy_name,
        selected=selected,
        dispatch_action=DISPATCH_ACTION if selected else "",
        required_lease_scope=REQUIRED_LEASE_SCOPE if selected else "",
        proof_event_type=PROOF_EVENT_TYPE if selected else "",
        reason=reason,
    )


def format_plan(plan: DispatchPlan) -> str:
    """Render a read-only dispatch plan for operators."""
    validator_status = "PASS" if plan.validation_passed else "FAIL"
    lines = [
        "Project Run Dispatch Plan",
        "",
        f"validator       : {validator_status}",
        f"selection_policy: {plan.selection_policy_name}",
        f"reason          : {plan.reason}",
        "",
        "Plan:",
    ]
    if not plan.selected:
        lines.append("- (none)")
        return "\n".join(lines)

    lines.extend(
        [
            f"- run_id              : {plan.selected.run_id}",
            f"  project             : {plan.selected.project}",
            f"  objective           : {plan.selected.objective}",
            f"  status              : {plan.selected.status}",
            f"  dispatch_action     : {plan.dispatch_action}",
            f"  required_lease_scope: {plan.required_lease_scope}",
            f"  proof_event_type    : {plan.proof_event_type}",
            "  mutates             : no",
            "  wakes               : no",
            "  leases              : no",
            "  executes            : no",
        ]
    )
    return "\n".join(lines)
