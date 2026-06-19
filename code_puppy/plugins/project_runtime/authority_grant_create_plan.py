"""Read-only AuthorityGrant creation preflight for Project OS."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from . import authority_grant_draft, authority_validator, store

EXPIRY_MINUTES = 15


@dataclass(frozen=True, slots=True)
class AuthorityGrantCreatePlan:
    """Read-only preflight for creating an AuthorityGrant record."""

    validation_passed: bool
    current_registry_valid: bool
    draft_id: str
    grant_id: str
    would_create_valid_record: bool
    would_duplicate_grant_id: bool
    would_conflict_active_grant: bool
    would_violate_scope_boundary_rules: bool
    reason: str
    exact_record: Mapping[str, str]
    blockers: tuple[str, ...]


def _parse_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _is_active(grant: store.AuthorityGrant, now: datetime) -> bool:
    if grant.revoked_at:
        return False
    expires_at = _parse_time(grant.expires_at)
    return expires_at is None or expires_at > now


def _matches_same_authority(
    grant: store.AuthorityGrant,
    record: Mapping[str, str],
    now: datetime,
) -> bool:
    return (
        _is_active(grant, now)
        and grant.subject_identity == record["subject_identity"]
        and grant.allowed_action_scope == record["allowed_action_scope"]
        and grant.allowed_capability_scope == record["allowed_capability_scope"]
        and grant.boundary == record["boundary"]
        and grant.run_id == record["run_id"]
        and grant.project_id == record["project_id"]
    )


def _iso_at(value: str | None) -> str:
    if value:
        return value
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _exact_record(
    draft: authority_grant_draft.AuthorityGrantDraft, issued_at: str | None
) -> dict[str, str]:
    final_issued_at = _iso_at(issued_at)
    issued_dt = _parse_time(final_issued_at)
    expires_at = ""
    if issued_dt:
        expires_at = (issued_dt + timedelta(minutes=EXPIRY_MINUTES)).isoformat()
    return {
        "grant_id": draft.grant_id,
        "subject_identity": draft.subject_identity,
        "allowed_action_scope": draft.allowed_action_scope,
        "allowed_capability_scope": draft.allowed_capability_scope,
        "boundary": draft.boundary,
        "issuer": draft.issuer,
        "issued_at": final_issued_at,
        "expires_at": expires_at,
        "revoked_at": "",
        "project_id": "",
        "run_id": draft.run_id,
        "reason": f"planned from {draft.source_lease_draft_id}",
        "precedent_id": "PRECEDENT-006",
    }


def _with_record(
    state: Mapping[str, Any] | None, record: Mapping[str, str]
) -> dict[str, Any]:
    raw_state = copy.deepcopy(state if state is not None else store.load_state())
    if not isinstance(raw_state, dict):
        raw_state = store.empty_state()
    grants = raw_state.setdefault("authority_grants", {})
    if not isinstance(grants, dict):
        raw_state["authority_grants"] = {}
        grants = raw_state["authority_grants"]
    grants[record["grant_id"]] = dict(record)
    return raw_state


def _blockers(
    *,
    validation_passed: bool,
    current_registry_valid: bool,
    duplicate: bool,
    conflict: bool,
    hypothetical_valid: bool,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if not validation_passed:
        blockers.append("validator FAIL prevents grant creation planning")
    if not current_registry_valid:
        blockers.append("current authority registry validation failed")
    if duplicate:
        blockers.append("grant_id already exists")
    if conflict:
        blockers.append("active grant already covers requested authority")
    if not hypothetical_valid:
        blockers.append("hypothetical grant registry would not validate")
    return tuple(blockers)


def plan_grant_create(
    state: Mapping[str, Any] | None = None,
    *,
    issued_at: str | None = None,
) -> AuthorityGrantCreatePlan:
    """Plan grant creation without creating, granting, leasing, or executing."""
    draft = authority_grant_draft.draft_authority_grant(state)
    current_report = authority_validator.validate_authority(state)
    if not draft.validation_passed or not draft.run_id:
        reason = (
            "validator FAIL prevents grant creation planning"
            if not draft.validation_passed
            else "no authority grant draft available for creation planning"
        )
        return AuthorityGrantCreatePlan(
            validation_passed=draft.validation_passed,
            current_registry_valid=current_report.passed,
            draft_id=draft.draft_id,
            grant_id=draft.grant_id,
            would_create_valid_record=False,
            would_duplicate_grant_id=False,
            would_conflict_active_grant=False,
            would_violate_scope_boundary_rules=False,
            reason=reason,
            exact_record={},
            blockers=_blockers(
                validation_passed=draft.validation_passed,
                current_registry_valid=current_report.passed,
                duplicate=False,
                conflict=False,
                hypothetical_valid=False,
            ),
        )

    record = _exact_record(draft, issued_at)
    current_grants = store.list_authority_grants(state)
    duplicate = any(grant.grant_id == draft.grant_id for grant in current_grants)
    now = _parse_time(record["issued_at"]) or datetime.now(timezone.utc)
    conflict = any(
        grant.grant_id != draft.grant_id and _matches_same_authority(grant, record, now)
        for grant in current_grants
    )
    hypothetical_state = _with_record(state, record)
    hypothetical_report = authority_validator.validate_authority(hypothetical_state)
    hypothetical_valid = hypothetical_report.passed
    would_violate = not hypothetical_valid
    would_create = (
        current_report.passed and hypothetical_valid and not duplicate and not conflict
    )
    reason = (
        "grant creation plan is valid but does not create authority"
        if would_create
        else "grant creation plan is blocked"
    )
    blockers = _blockers(
        validation_passed=True,
        current_registry_valid=current_report.passed,
        duplicate=duplicate,
        conflict=conflict,
        hypothetical_valid=hypothetical_valid,
    )
    return AuthorityGrantCreatePlan(
        validation_passed=True,
        current_registry_valid=current_report.passed,
        draft_id=draft.draft_id,
        grant_id=draft.grant_id,
        would_create_valid_record=would_create,
        would_duplicate_grant_id=duplicate,
        would_conflict_active_grant=conflict,
        would_violate_scope_boundary_rules=would_violate,
        reason=reason,
        exact_record=record,
        blockers=blockers,
    )


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def format_plan(plan: AuthorityGrantCreatePlan) -> str:
    """Render a read-only AuthorityGrant creation plan."""
    validator_status = "PASS" if plan.validation_passed else "FAIL"
    registry_status = "PASS" if plan.current_registry_valid else "FAIL"
    lines = [
        "Project Authority Grant Create Plan",
        "",
        f"validator                    : {validator_status}",
        f"current_authority_validation : {registry_status}",
        f"reason                       : {plan.reason}",
        "",
        "Plan:",
    ]
    if not plan.exact_record:
        lines.append("- (none)")
    else:
        lines.extend(
            [
                f"- draft_id                    : {plan.draft_id}",
                f"  grant_id                    : {plan.grant_id}",
                f"  would_create_valid_record   : {_yes_no(plan.would_create_valid_record)}",
                f"  would_duplicate_grant_id    : {_yes_no(plan.would_duplicate_grant_id)}",
                f"  would_conflict_active_grant : {_yes_no(plan.would_conflict_active_grant)}",
                f"  would_violate_scope_boundary: {_yes_no(plan.would_violate_scope_boundary_rules)}",
                "  creates_grant               : no",
                "  mutates                     : no",
                "  authorizes                  : no",
                "  wakes                       : no",
                "  leases                      : no",
                "  executes                    : no",
                "",
                "Exact record:",
            ]
        )
        lines.extend(
            f"  {key}: {value or '(none)'}" for key, value in plan.exact_record.items()
        )

    lines.extend(["", "Blockers:"])
    if not plan.blockers:
        lines.append("- (none)")
    else:
        lines.extend(f"- {blocker}" for blocker in plan.blockers)
    return "\n".join(lines)
