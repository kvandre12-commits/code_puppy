"""One-shot browser URL execution under a Project OS lease."""

from __future__ import annotations

import webbrowser
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from . import effect_arguments, effect_specs, execution_preflight, lease_store

BROWSER_ACTION_SCOPE = effect_specs.BROWSER.action_scope
BROWSER_CAPABILITY_SCOPE = effect_specs.BROWSER.capability_scope
BROWSER_EFFECT_EVENT_TYPE = effect_specs.BROWSER.audit_event_type
ALLOWED_URL = effect_arguments.ALLOWED_BROWSER_URL

BrowserOpener = Callable[[str], bool | None]


@dataclass(frozen=True, slots=True)
class BrowserExecutionResult:
    """Result of attempting one bounded browser effect."""

    executed: bool
    lease_id: str
    run_id: str
    event_id: str
    url: str
    reason: str
    record: Mapping[str, str]
    blockers: tuple[str, ...]


def _open_browser(url: str, opener: BrowserOpener | None) -> bool:
    if opener is not None:
        return opener(url) is not False
    return webbrowser.open(url)


def execute_browser(
    *,
    confirm_lease_id: str,
    url: str,
    opener: BrowserOpener | None = None,
    now_at: str | None = None,
) -> BrowserExecutionResult:
    """Execute exactly one browser URL effect under a valid one-shot lease."""
    normalized_url = url.strip()
    preflight = execution_preflight.preflight_execution(
        effect=effect_specs.BROWSER.name,
        confirm_lease_id=confirm_lease_id,
        arguments={"url": normalized_url},
        now_at=now_at,
    )
    if not preflight.ready:
        return BrowserExecutionResult(
            executed=False,
            lease_id=preflight.lease_id,
            run_id=preflight.run_id,
            event_id="",
            url=normalized_url,
            reason="browser execution blocked by preflight",
            record=preflight.record,
            blockers=preflight.blockers,
        )

    assert preflight.lease is not None
    lease = preflight.lease
    if not _open_browser(normalized_url, opener):
        return BrowserExecutionResult(
            executed=False,
            lease_id=lease.lease_id,
            run_id=lease.run_id,
            event_id="",
            url=normalized_url,
            reason="browser opener reported failure; no audit event written",
            record=lease_store.lease_to_dict(lease),
            blockers=("browser opener failed",),
        )

    result = lease_store.consume_lease_for_effect(
        lease,
        event_type=BROWSER_EFFECT_EVENT_TYPE,
        payload_summary=f"Browser opened URL under lease: {normalized_url}",
    )
    return BrowserExecutionResult(
        executed=True,
        lease_id=result.lease.lease_id,
        run_id=result.lease.run_id,
        event_id=result.event.event_id,
        url=normalized_url,
        reason="Browser URL opened and audited",
        record=lease_store.lease_to_dict(result.lease),
        blockers=(),
    )


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def format_result(result: BrowserExecutionResult) -> str:
    """Render browser execution result."""
    lines = [
        "Project Run Execute Browser",
        "",
        f"executed                    : {_yes_no(result.executed)}",
        f"reason                      : {result.reason}",
        f"lease_id                    : {result.lease_id or '(none)'}",
        f"run_id                      : {result.run_id or '(none)'}",
        f"event_id                    : {result.event_id or '(none)'}",
        f"url                         : {result.url or '(none)'}",
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
