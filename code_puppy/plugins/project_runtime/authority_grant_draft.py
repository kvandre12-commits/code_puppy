"""Read-only Authority Grant draft reporting for Project OS."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from . import lease_draft

BOUNDARY = "project_run"
ISSUER = "operator_required"
PROPOSED_EXPIRES_AT = "one_step_or_15_minutes"


@dataclass(frozen=True, slots=True)
class AuthorityGrantDraft:
    """Read-only draft of permission evidence needed for a lease."""

    validation_passed: bool
    draft_id: str
    source_lease_draft_id: str
    grant_id: str
    subject_identity: str
    allowed_action_scope: str
    allowed_capability_scope: str
    boundary: str
    run_id: str
    issuer: str
    proposed_expires_at: str
    reason: str


def _lease_draft_id(draft: lease_draft.LeaseDraft) -> str:
    if not draft.run_id:
        return ""
    return ":".join(("lease-draft", draft.run_id, draft.requested_action_scope))


def _draft_id(draft: lease_draft.LeaseDraft) -> str:
    if not draft.run_id:
        return ""
    return ":".join(
        ("authority-grant-draft", draft.run_id, draft.requested_action_scope)
    )


def _grant_id(draft: lease_draft.LeaseDraft) -> str:
    if not draft.run_id:
        return ""
    return ":".join(("grant", draft.run_id, draft.requested_action_scope))


def draft_authority_grant(
    state: Mapping[str, Any] | None = None,
) -> AuthorityGrantDraft:
    """Draft authority evidence without creating, granting, leasing, or executing."""
    draft = lease_draft.draft_lease(state)
    if not draft.validation_passed:
        reason = "validator FAIL prevents authority grant drafting"
    elif not draft.run_id:
        reason = "no lease draft available for authority grant drafting"
    else:
        reason = "lease draft can be translated into AuthorityGrant draft evidence"

    return AuthorityGrantDraft(
        validation_passed=draft.validation_passed,
        draft_id=_draft_id(draft),
        source_lease_draft_id=_lease_draft_id(draft),
        grant_id=_grant_id(draft),
        subject_identity=draft.requested_agent_identity if draft.run_id else "",
        allowed_action_scope=draft.requested_action_scope if draft.run_id else "",
        allowed_capability_scope=draft.requested_capability_scope
        if draft.run_id
        else "",
        boundary=BOUNDARY if draft.run_id else "",
        run_id=draft.run_id,
        issuer=ISSUER if draft.run_id else "",
        proposed_expires_at=PROPOSED_EXPIRES_AT if draft.run_id else "",
        reason=reason,
    )


def format_draft(draft: AuthorityGrantDraft) -> str:
    """Render a read-only AuthorityGrant draft report."""
    validator_status = "PASS" if draft.validation_passed else "FAIL"
    lines = [
        "Project Authority Grant Draft",
        "",
        f"validator               : {validator_status}",
        f"reason                  : {draft.reason}",
        "",
        "Draft:",
    ]
    if not draft.run_id:
        lines.append("- (none)")
    else:
        lines.extend(
            [
                f"- draft_id               : {draft.draft_id}",
                f"  source_lease_draft_id  : {draft.source_lease_draft_id}",
                f"  grant_id               : {draft.grant_id}",
                f"  subject_identity       : {draft.subject_identity}",
                f"  allowed_action_scope   : {draft.allowed_action_scope}",
                f"  allowed_capability     : {draft.allowed_capability_scope}",
                f"  boundary               : {draft.boundary}",
                f"  run_id                 : {draft.run_id}",
                f"  issuer                 : {draft.issuer}",
                f"  proposed_expires_at    : {draft.proposed_expires_at}",
                "  creates_grant          : no",
                "  authorizes             : no",
                "  mutates                : no",
                "  wakes                  : no",
                "  leases                 : no",
                "  executes               : no",
            ]
        )
    return "\n".join(lines)
