"""Confirmed Project OS lease issuance."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from . import authority_check, lease_store

EXPIRY_MINUTES = 15


@dataclass(frozen=True, slots=True)
class LeaseIssueResult:
    """Result of a confirmed lease issuance attempt."""

    issued: bool
    lease_id: str
    run_id: str
    event_id: str
    reason: str
    record: Mapping[str, str]
    blockers: tuple[str, ...]


def lease_id_for(run_id: str, action_scope: str) -> str:
    """Return deterministic lease ID for the current bounded action."""
    if not run_id or not action_scope:
        return ""
    return ":".join(("lease", run_id, action_scope))


def _iso_at(value: str | None) -> str:
    if value:
        return value
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _record_from_check(
    check: authority_check.AuthorityCheck,
    issued_at: str | None,
) -> dict[str, str]:
    final_issued_at = _iso_at(issued_at)
    issued_dt = lease_store.parse_time(final_issued_at)
    expires_at = ""
    if issued_dt:
        expires_at = (issued_dt + timedelta(minutes=EXPIRY_MINUTES)).isoformat()
    return {
        "lease_id": lease_id_for(check.run_id, check.requested_action_scope),
        "run_id": check.run_id,
        "subject_identity": check.requested_agent_identity,
        "action_scope": check.requested_action_scope,
        "capability_scope": check.requested_capability_scope,
        "issued_at": final_issued_at,
        "expires_at": expires_at,
        "consumed_at": "",
        "issued_event_id": "",
        "consumed_event_id": "",
        "reason": f"issued from {check.lease_draft_id}",
    }


def _duplicate_blocker(lease_id: str) -> tuple[str, ...]:
    if any(lease.lease_id == lease_id for lease in lease_store.list_leases()):
        return ("lease_id already exists",)
    return ()


def issue_lease(
    *,
    confirm_lease_id: str,
    issued_at: str | None = None,
) -> LeaseIssueResult:
    """Issue one lease only after authority-check passes and ID confirmation matches."""
    check = authority_check.check_authority()
    record = _record_from_check(check, issued_at) if check.run_id else {}
    expected = str(record.get("lease_id") or "")
    if not expected or confirm_lease_id != expected:
        return LeaseIssueResult(
            issued=False,
            lease_id=expected,
            run_id=str(record.get("run_id") or ""),
            event_id="",
            reason="confirmation lease_id did not match current authority-check",
            record=record,
            blockers=("confirmation mismatch", *check.blockers),
        )
    duplicate_blockers = _duplicate_blocker(expected)
    if not check.lease_issuable or duplicate_blockers:
        return LeaseIssueResult(
            issued=False,
            lease_id=expected,
            run_id=str(record.get("run_id") or ""),
            event_id="",
            reason="lease issuance blocked by authority-check",
            record=record,
            blockers=(*check.blockers, *duplicate_blockers),
        )

    result = lease_store.create_lease_record(record)
    return LeaseIssueResult(
        issued=True,
        lease_id=result.lease.lease_id,
        run_id=result.lease.run_id,
        event_id=result.event.event_id,
        reason="Lease issued and audited",
        record=lease_store.lease_to_dict(result.lease),
        blockers=(),
    )


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def format_result(result: LeaseIssueResult) -> str:
    """Render lease issuance result."""
    lines = [
        "Project Run Lease Issue",
        "",
        f"issued                      : {_yes_no(result.issued)}",
        f"reason                      : {result.reason}",
        f"lease_id                    : {result.lease_id or '(none)'}",
        f"run_id                      : {result.run_id or '(none)'}",
        f"event_id                    : {result.event_id or '(none)'}",
        "creates_lease               : " + _yes_no(result.issued),
        "mutates                     : " + _yes_no(result.issued),
        "creates_audit_event         : " + _yes_no(result.issued),
        "wakes                       : no",
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
