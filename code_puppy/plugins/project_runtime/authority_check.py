"""Read-only Project Run authority check report."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from . import lease_draft, store


@dataclass(frozen=True, slots=True)
class AuthorityCheck:
    """Read-only authority check result for a lease draft."""

    validation_passed: bool
    lease_draft_id: str
    run_id: str
    requested_agent_identity: str
    requested_action_scope: str
    requested_capability_scope: str
    identity_present: bool
    authority_grant_present: bool
    capability_grant_present: bool
    lease_issuable: bool
    reason: str
    blockers: tuple[str, ...]


def _lease_draft_id(draft: lease_draft.LeaseDraft) -> str:
    if not draft.run_id:
        return ""
    return ":".join(("lease-draft", draft.run_id, draft.requested_action_scope))


def _run_project(state: Mapping[str, Any] | None, run_id: str) -> str:
    raw_state = state if state is not None else store.load_state()
    raw_runs = raw_state.get("runs", {})
    if not isinstance(raw_runs, dict):
        return ""
    raw_run = raw_runs.get(run_id)
    if not isinstance(raw_run, dict):
        return ""
    return str(raw_run.get("project") or "")


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


def _matches_boundary(
    grant: store.AuthorityGrant, *, run_id: str, project_id: str
) -> bool:
    if grant.run_id:
        return grant.run_id == run_id
    if grant.project_id:
        return grant.project_id == project_id
    return False


def _matching_grants(
    grants: tuple[store.AuthorityGrant, ...],
    *,
    identity: str,
    run_id: str,
    project_id: str,
    now: datetime,
) -> tuple[store.AuthorityGrant, ...]:
    return tuple(
        grant
        for grant in grants
        if grant.subject_identity == identity
        and _is_active(grant, now)
        and _matches_boundary(grant, run_id=run_id, project_id=project_id)
    )


def _blockers(
    *,
    identity_present: bool,
    authority_grant_present: bool,
    capability_grant_present: bool,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if not identity_present:
        blockers.append("identity grant evidence missing")
    if not authority_grant_present:
        blockers.append("authority grant for requested action scope missing")
    if not capability_grant_present:
        blockers.append("capability grant for requested capability scope missing")
    return tuple(blockers)


def check_authority(state: Mapping[str, Any] | None = None) -> AuthorityCheck:
    """Check authority requirements without authorizing, leasing, or executing."""
    draft = lease_draft.draft_lease(state)
    if not draft.validation_passed:
        return AuthorityCheck(
            validation_passed=False,
            lease_draft_id="",
            run_id="",
            requested_agent_identity="",
            requested_action_scope="",
            requested_capability_scope="",
            identity_present=False,
            authority_grant_present=False,
            capability_grant_present=False,
            lease_issuable=False,
            reason="validator FAIL prevents authority checking",
            blockers=("validator FAIL",),
        )
    if not draft.run_id:
        return AuthorityCheck(
            validation_passed=True,
            lease_draft_id="",
            run_id="",
            requested_agent_identity="",
            requested_action_scope="",
            requested_capability_scope="",
            identity_present=False,
            authority_grant_present=False,
            capability_grant_present=False,
            lease_issuable=False,
            reason="no lease draft available for authority checking",
            blockers=("missing lease draft",),
        )

    now = datetime.now(timezone.utc)
    project_id = _run_project(state, draft.run_id)
    grants = store.list_authority_grants(state)
    identity_grants = tuple(
        grant
        for grant in grants
        if grant.subject_identity == draft.requested_agent_identity
        and _is_active(grant, now)
    )
    scoped_grants = _matching_grants(
        grants,
        identity=draft.requested_agent_identity,
        run_id=draft.run_id,
        project_id=project_id,
        now=now,
    )
    identity_present = bool(identity_grants)
    authority_grant_present = any(
        grant.allowed_action_scope == draft.requested_action_scope
        for grant in scoped_grants
    )
    capability_grant_present = any(
        grant.allowed_capability_scope == draft.requested_capability_scope
        for grant in scoped_grants
    )
    lease_issuable = (
        identity_present and authority_grant_present and capability_grant_present
    )
    blockers = _blockers(
        identity_present=identity_present,
        authority_grant_present=authority_grant_present,
        capability_grant_present=capability_grant_present,
    )
    reason = (
        "authority check passed; lease is issuable but not issued"
        if lease_issuable
        else "lease draft is not issuable until required authority evidence exists"
    )
    return AuthorityCheck(
        validation_passed=True,
        lease_draft_id=_lease_draft_id(draft),
        run_id=draft.run_id,
        requested_agent_identity=draft.requested_agent_identity,
        requested_action_scope=draft.requested_action_scope,
        requested_capability_scope=draft.requested_capability_scope,
        identity_present=identity_present,
        authority_grant_present=authority_grant_present,
        capability_grant_present=capability_grant_present,
        lease_issuable=lease_issuable,
        reason=reason,
        blockers=blockers,
    )


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def format_check(check: AuthorityCheck) -> str:
    """Render a read-only authority check report for operators."""
    validator_status = "PASS" if check.validation_passed else "FAIL"
    lines = [
        "Project Run Authority Check",
        "",
        f"validator               : {validator_status}",
        f"reason                  : {check.reason}",
        "",
        "Check:",
    ]
    if not check.run_id:
        lines.append("- (none)")
    else:
        lines.extend(
            [
                f"- lease_draft_id         : {check.lease_draft_id}",
                f"  run_id                 : {check.run_id}",
                f"  requested_agent_identity: {check.requested_agent_identity}",
                f"  requested_action_scope : {check.requested_action_scope}",
                f"  requested_capability   : {check.requested_capability_scope}",
                f"  identity_present       : {_yes_no(check.identity_present)}",
                f"  authority_grant_present: {_yes_no(check.authority_grant_present)}",
                f"  capability_grant_present: {_yes_no(check.capability_grant_present)}",
                f"  lease_issuable         : {_yes_no(check.lease_issuable)}",
                "  authorizes             : no",
                "  mutates                : no",
                "  wakes                  : no",
                "  leases                 : no",
                "  executes               : no",
            ]
        )

    lines.extend(["", "Blockers:"])
    if not check.blockers:
        lines.append("- (none)")
    else:
        lines.extend(f"- {blocker}" for blocker in check.blockers)
    return "\n".join(lines)
