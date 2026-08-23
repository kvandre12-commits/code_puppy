"""One-shot Android activity launch under a Project OS lease."""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone

from . import authority_validator, lease_store, store

ANDROID_ACTION_SCOPE = "android.launch_activity"
ANDROID_CAPABILITY_SCOPE = "android.activity.settings"
ANDROID_EFFECT_EVENT_TYPE = "android_effect_executed"
APPROVED_COMPONENT = "com.android.settings/.Settings"

AndroidLauncher = Callable[[str], bool | None]


@dataclass(frozen=True, slots=True)
class AndroidExecutionResult:
    """Result of attempting one bounded Android device effect."""

    executed: bool
    lease_id: str
    run_id: str
    event_id: str
    component: str
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
    *,
    component: str,
    now: datetime,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if component != APPROVED_COMPONENT:
        blockers.append("Android activity scope mismatch")
    if lease.consumed_at:
        blockers.append("lease already consumed")
    expires_at = lease_store.parse_time(lease.expires_at)
    if expires_at is None or expires_at <= now:
        blockers.append("lease expired")
    if lease.action_scope != ANDROID_ACTION_SCOPE:
        blockers.append("lease action scope mismatch")
    if lease.capability_scope != ANDROID_CAPABILITY_SCOPE:
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


def _launch_activity(component: str, launcher: AndroidLauncher | None) -> bool:
    if launcher is not None:
        return launcher(component) is not False
    try:
        completed = subprocess.run(
            ["am", "start", "-n", component],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0


def execute_android(
    *,
    confirm_lease_id: str,
    component: str,
    launcher: AndroidLauncher | None = None,
    now_at: str | None = None,
) -> AndroidExecutionResult:
    """Execute exactly one Android activity launch under a valid one-shot lease."""
    normalized_component = component.strip()
    try:
        lease = lease_store.get_lease(confirm_lease_id)
    except KeyError:
        return AndroidExecutionResult(
            executed=False,
            lease_id=confirm_lease_id,
            run_id="",
            event_id="",
            component=normalized_component,
            reason="lease not found; no Android effect executed",
            record={},
            blockers=("lease missing",),
        )

    blockers = _lease_blockers(
        lease,
        component=normalized_component,
        now=_now(now_at),
    )
    if blockers:
        return AndroidExecutionResult(
            executed=False,
            lease_id=lease.lease_id,
            run_id=lease.run_id,
            event_id="",
            component=normalized_component,
            reason="Android execution blocked by lease validation",
            record=lease_store.lease_to_dict(lease),
            blockers=blockers,
        )

    if not _launch_activity(normalized_component, launcher):
        return AndroidExecutionResult(
            executed=False,
            lease_id=lease.lease_id,
            run_id=lease.run_id,
            event_id="",
            component=normalized_component,
            reason="Android launcher reported failure; no audit event written",
            record=lease_store.lease_to_dict(lease),
            blockers=("Android launcher failed",),
        )

    result = lease_store.consume_lease_for_effect(
        lease,
        event_type=ANDROID_EFFECT_EVENT_TYPE,
        payload_summary=f"Android launched activity under lease: {normalized_component}",
    )
    return AndroidExecutionResult(
        executed=True,
        lease_id=result.lease.lease_id,
        run_id=result.lease.run_id,
        event_id=result.event.event_id,
        component=normalized_component,
        reason="Android activity launched and audited",
        record=lease_store.lease_to_dict(result.lease),
        blockers=(),
    )


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def format_result(result: AndroidExecutionResult) -> str:
    """Render Android execution result."""
    lines = [
        "Project Run Execute Android",
        "",
        f"executed                    : {_yes_no(result.executed)}",
        f"reason                      : {result.reason}",
        f"lease_id                    : {result.lease_id or '(none)'}",
        f"run_id                      : {result.run_id or '(none)'}",
        f"event_id                    : {result.event_id or '(none)'}",
        f"component                   : {result.component or '(none)'}",
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
