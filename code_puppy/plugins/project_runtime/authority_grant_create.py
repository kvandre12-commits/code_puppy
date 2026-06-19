"""Privileged AuthorityGrant creation for Project OS."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from . import authority_grant_create_plan, authority_validator, store


@dataclass(frozen=True, slots=True)
class AuthorityGrantCreateResult:
    """Result of a confirmed AuthorityGrant creation attempt."""

    created: bool
    grant_id: str
    run_id: str
    event_id: str
    reason: str
    record: Mapping[str, str]
    blockers: tuple[str, ...]


def create_authority_grant(
    *,
    confirm_grant_id: str,
    issued_at: str | None = None,
) -> AuthorityGrantCreateResult:
    """Create an AuthorityGrant only after a valid plan and exact confirmation."""
    state = store.load_state()
    plan = authority_grant_create_plan.plan_grant_create(state, issued_at=issued_at)
    expected = plan.grant_id
    if not expected or confirm_grant_id != expected:
        return AuthorityGrantCreateResult(
            created=False,
            grant_id=expected,
            run_id=str(plan.exact_record.get("run_id", ""))
            if plan.exact_record
            else "",
            event_id="",
            reason=("confirmation grant_id did not match current grant-create-plan"),
            record=plan.exact_record,
            blockers=("confirmation mismatch", *plan.blockers),
        )
    if not plan.would_create_valid_record:
        return AuthorityGrantCreateResult(
            created=False,
            grant_id=expected,
            run_id=str(plan.exact_record.get("run_id", ""))
            if plan.exact_record
            else "",
            event_id="",
            reason="grant creation blocked by grant-create-plan",
            record=plan.exact_record,
            blockers=plan.blockers,
        )

    grant, event = store.create_authority_grant_record(plan.exact_record)
    post_report = authority_validator.validate_authority()
    if not post_report.passed:  # pragma: no cover - defensive corruption guard
        raise RuntimeError("created AuthorityGrant failed post-create validation")
    return AuthorityGrantCreateResult(
        created=True,
        grant_id=grant.grant_id,
        run_id=grant.run_id,
        event_id=event.event_id,
        reason="AuthorityGrant created and audited",
        record=plan.exact_record,
        blockers=(),
    )


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def format_result(result: AuthorityGrantCreateResult) -> str:
    """Render AuthorityGrant creation result."""
    lines = [
        "Project Authority Grant Create",
        "",
        f"created                     : {_yes_no(result.created)}",
        f"reason                      : {result.reason}",
        f"grant_id                    : {result.grant_id or '(none)'}",
        f"run_id                      : {result.run_id or '(none)'}",
        f"event_id                    : {result.event_id or '(none)'}",
        "creates_grant               : " + _yes_no(result.created),
        "mutates                     : " + _yes_no(result.created),
        "creates_audit_event         : " + _yes_no(result.created),
        "authorizes                  : no",
        "wakes                       : no",
        "leases                      : no",
        "executes                    : no",
        "",
        "Exact record:",
    ]
    if result.record:
        lines.extend(
            f"  {key}: {value or '(none)'}" for key, value in result.record.items()
        )
    else:
        lines.append("  (none)")
    lines.extend(["", "Blockers:"])
    if result.blockers:
        lines.extend(f"- {blocker}" for blocker in result.blockers)
    else:
        lines.append("- (none)")
    return "\n".join(lines)
