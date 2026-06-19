"""One-shot no-op execution under a Project OS lease."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone

from . import authority_validator, lease_draft, lease_store, store


@dataclass(frozen=True, slots=True)
class NoopExecutionResult:
    """Result of attempting one bounded no-op effect."""

    executed: bool
    lease_id: str
    run_id: str
    event_id: str
    reason: str
    record: Mapping[str, str]
    blockers: tuple[str, ...]


def _now(value: str | None) -> datetime:
    if value:
        parsed = lease_store.parse_time(value)
        if parsed:
            return parsed
    return datetime.now(timezone.utc)


def _grant_active(grant: store.AuthorityGrant, now: datetime) -> bool:
    if grant.revoked_at:
        return False
    expires_at = lease_store.parse_time(grant.expires_at)
    return expires_at is None or expires_at > now


def _matching_active_grant(lease: lease_store.LeaseRecord, now: datetime) -> bool:
    return any(
        grant.subject_identity == lease.subject_identity
        and grant.allowed_action_scope == lease.action_scope
        and grant.allowed_capability_scope == lease.capability_scope
        and grant.run_id == lease.run_id
        and _grant_active(grant, now)
        for grant in store.list_authority_grants()
    )


def _lease_blockers(
    lease: lease_store.LeaseRecord,
    now: datetime,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if lease.consumed_at:
        blockers.append("lease already consumed")
    expires_at = lease_store.parse_time(lease.expires_at)
    if expires_at is None or expires_at <= now:
        blockers.append("lease expired")
    if lease.action_scope != lease_draft.REQUESTED_ACTION_SCOPE:
        blockers.append("lease action scope mismatch")
    if lease.capability_scope != lease_draft.REQUESTED_CAPABILITY_SCOPE:
        blockers.append("lease capability scope mismatch")
    if not lease.issued_event_id:
        blockers.append("lease issue audit event missing")
    try:
        store.get_run(lease.run_id)
    except KeyError:
        blockers.append("lease run boundary missing")
    registry_report = authority_validator.validate_authority()
    if not registry_report.passed:
        blockers.append("authority registry validation failed")
    elif not _matching_active_grant(lease, now):
        blockers.append("matching active authority grant missing")
    return tuple(blockers)


def execute_noop(
    *,
    confirm_lease_id: str,
    now_at: str | None = None,
) -> NoopExecutionResult:
    """Execute exactly one no-op effect under a valid one-shot lease."""
    try:
        lease = lease_store.get_lease(confirm_lease_id)
    except KeyError:
        return NoopExecutionResult(
            executed=False,
            lease_id=confirm_lease_id,
            run_id="",
            event_id="",
            reason="lease not found; no effect executed",
            record={},
            blockers=("lease missing",),
        )

    blockers = _lease_blockers(lease, _now(now_at))
    if blockers:
        return NoopExecutionResult(
            executed=False,
            lease_id=lease.lease_id,
            run_id=lease.run_id,
            event_id="",
            reason="no-op execution blocked by lease validation",
            record=lease_store.lease_to_dict(lease),
            blockers=blockers,
        )

    result = lease_store.consume_lease_for_noop(lease)
    return NoopExecutionResult(
        executed=True,
        lease_id=result.lease.lease_id,
        run_id=result.lease.run_id,
        event_id=result.event.event_id,
        reason="No-op executed and audited",
        record=lease_store.lease_to_dict(result.lease),
        blockers=(),
    )


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def format_result(result: NoopExecutionResult) -> str:
    """Render no-op execution result."""
    lines = [
        "Project Run Execute No-Op",
        "",
        f"executed                    : {_yes_no(result.executed)}",
        f"reason                      : {result.reason}",
        f"lease_id                    : {result.lease_id or '(none)'}",
        f"run_id                      : {result.run_id or '(none)'}",
        f"event_id                    : {result.event_id or '(none)'}",
        "bounded_effect              : " + _yes_no(result.executed),
        "consumes_lease              : " + _yes_no(result.executed),
        "mutates                     : " + _yes_no(result.executed),
        "creates_audit_event         : " + _yes_no(result.executed),
        "creates_grant               : no",
        "leases                      : no",
        "wakes                       : no",
        "",
        "Lease record:",
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
