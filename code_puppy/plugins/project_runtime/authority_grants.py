"""Read-only Authority Grant reporting for Project OS."""

from __future__ import annotations

from collections.abc import Sequence

from . import store


def format_grants(grants: Sequence[store.AuthorityGrant]) -> str:
    """Render configured authority grants without issuing or mutating authority."""
    lines = [
        "Project Authority Grants",
        "",
        "mutates   : no",
        "authorizes: no",
        "leases    : no",
        "executes  : no",
        "",
        "Grants:",
    ]
    if not grants:
        lines.append("- (none)")
        return "\n".join(lines)

    for grant in grants:
        lines.extend(
            [
                f"- grant_id                : {grant.grant_id}",
                f"  subject_identity        : {grant.subject_identity}",
                f"  allowed_action_scope    : {grant.allowed_action_scope}",
                f"  allowed_capability_scope: {grant.allowed_capability_scope}",
                f"  boundary                : {grant.boundary}",
                f"  project_id              : {grant.project_id or '(none)'}",
                f"  run_id                  : {grant.run_id or '(none)'}",
                f"  issuer                  : {grant.issuer or '(unknown)'}",
                f"  issued_at               : {grant.issued_at or '(unknown)'}",
                f"  expires_at              : {grant.expires_at or '(none)'}",
                f"  revoked_at              : {grant.revoked_at or '(none)'}",
                f"  reason                  : {grant.reason or '(none)'}",
                f"  precedent_id            : {grant.precedent_id or '(none)'}",
            ]
        )
    return "\n".join(lines)
