"""Shared lease validation for governed Project OS effects."""

from __future__ import annotations

from datetime import datetime, timezone

from . import authority_validator, effect_specs, lease_store, store


def now_from_string(value: str | None) -> datetime:
    """Parse a testable timestamp or return the current UTC time."""
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


def _matching_active_grant(
    lease: lease_store.LeaseRecord,
    effect: effect_specs.EffectSpec,
    now: datetime,
) -> bool:
    return any(
        grant.subject_identity == lease.subject_identity
        and grant.allowed_action_scope == effect.action_scope
        and grant.allowed_capability_scope == effect.capability_scope
        and grant.run_id == lease.run_id
        and _grant_active(grant, now)
        for grant in store.list_authority_grants()
    )


def blockers_for_effect_lease(
    lease: lease_store.LeaseRecord,
    effect: effect_specs.EffectSpec,
    now: datetime,
) -> tuple[str, ...]:
    """Return exact blockers preventing a lease from authorizing an effect."""
    blockers: list[str] = []
    if lease.consumed_at:
        blockers.append("lease already consumed")
    expires_at = lease_store.parse_time(lease.expires_at)
    if expires_at is None or expires_at <= now:
        blockers.append("lease expired")
    if lease.action_scope != effect.action_scope:
        blockers.append("lease action scope mismatch")
    if lease.capability_scope != effect.capability_scope:
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
    elif not _matching_active_grant(lease, effect, now):
        blockers.append("matching active authority grant missing")
    return tuple(blockers)
