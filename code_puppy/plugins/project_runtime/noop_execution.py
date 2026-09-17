"""One-shot no-op execution under a Project OS lease."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from . import effect_specs, execution_preflight, lease_store


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


def execute_noop(
    *,
    confirm_lease_id: str,
    now_at: str | None = None,
) -> NoopExecutionResult:
    """Execute exactly one no-op effect under a valid one-shot lease."""
    preflight = execution_preflight.preflight_execution(
        effect=effect_specs.NOOP.name,
        confirm_lease_id=confirm_lease_id,
        now_at=now_at,
    )
    if not preflight.ready:
        return NoopExecutionResult(
            executed=False,
            lease_id=preflight.lease_id,
            run_id=preflight.run_id,
            event_id="",
            reason="no-op execution blocked by preflight",
            record=preflight.record,
            blockers=preflight.blockers,
        )

    assert preflight.lease is not None
    result = lease_store.consume_lease_for_noop(preflight.lease)
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
