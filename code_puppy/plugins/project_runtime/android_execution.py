"""One-shot Android activity launch under a Project OS lease."""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from . import effect_arguments, effect_specs, execution_preflight, lease_store

ANDROID_ACTION_SCOPE = effect_specs.ANDROID.action_scope
ANDROID_CAPABILITY_SCOPE = effect_specs.ANDROID.capability_scope
ANDROID_EFFECT_EVENT_TYPE = effect_specs.ANDROID.audit_event_type
APPROVED_COMPONENT = effect_arguments.APPROVED_ANDROID_COMPONENT

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
    preflight = execution_preflight.preflight_execution(
        effect=effect_specs.ANDROID.name,
        confirm_lease_id=confirm_lease_id,
        arguments={"component": normalized_component},
        now_at=now_at,
    )
    if not preflight.ready:
        return AndroidExecutionResult(
            executed=False,
            lease_id=preflight.lease_id,
            run_id=preflight.run_id,
            event_id="",
            component=normalized_component,
            reason="Android execution blocked by preflight",
            record=preflight.record,
            blockers=preflight.blockers,
        )

    assert preflight.lease is not None
    lease = preflight.lease
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
