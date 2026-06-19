"""Read-only Project Run authority check report."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from . import lease_draft


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

    blockers = (
        "identity store not implemented for Project Run leases",
        "authority grant store not implemented for Project Run leases",
        "capability grant store not implemented for Project Run leases",
    )
    return AuthorityCheck(
        validation_passed=True,
        lease_draft_id=_lease_draft_id(draft),
        run_id=draft.run_id,
        requested_agent_identity=draft.requested_agent_identity,
        requested_action_scope=draft.requested_action_scope,
        requested_capability_scope=draft.requested_capability_scope,
        identity_present=False,
        authority_grant_present=False,
        capability_grant_present=False,
        lease_issuable=False,
        reason="lease draft is not issuable until identity, authority, and capability grants exist",
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
