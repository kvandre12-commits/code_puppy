"""Project OS governance adapter for Code Puppy (first governed runtime).

Thin integration layer between Code Puppy and the standalone ``project_os``
policy package. Code Puppy depends on ``project_os``; ``project_os`` must never
import Code Puppy. This module copies none of the policy logic - it only
translates Code Puppy's boundary events into PolicyEngine calls and applies the
resulting decisions under the universal observe/enforce mode rule.

Disabled by default. Nothing here changes behavior until ``activate()`` is
called explicitly, and ``project_os`` is imported (and version-checked) lazily
only at activation, so the package is not a hard import dependency for the
disabled path.
"""

from .adapter import (
    ALLOW,
    DENY,
    LIMIT,
    AdapterOutcome,
    Mode,
    activate,
    before_claim,
    before_final_result_release,
    before_provider_request,
    before_tool_call,
    current_receipt,
    deactivate,
    effective_retry_ceiling,
    is_active,
    is_enforcing,
    note_http_attempt,
    raise_policy_error,
    reconcile_usage,
    run_complete,
    transform_tool_result,
)

__all__ = [
    "Mode",
    "AdapterOutcome",
    "ALLOW",
    "DENY",
    "LIMIT",
    "activate",
    "deactivate",
    "is_active",
    "is_enforcing",
    "current_receipt",
    "before_provider_request",
    "reconcile_usage",
    "before_tool_call",
    "transform_tool_result",
    "before_claim",
    "before_final_result_release",
    "note_http_attempt",
    "effective_retry_ceiling",
    "raise_policy_error",
    "run_complete",
]
