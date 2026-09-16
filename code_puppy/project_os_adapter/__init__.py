"""Project OS governance adapter for Code Puppy (first governed runtime).

Thin integration layer between Code Puppy and the standalone ``project_os``
policy package. Code Puppy depends on ``project_os``; ``project_os`` must never
import Code Puppy. This module copies none of the policy logic - it only
translates Code Puppy's boundary events into PolicyEngine calls and maps the
resulting decisions back onto Code Puppy's conventions.

Disabled by default. Nothing here touches behavior until ``activate()`` is
called explicitly, and ``project_os`` is imported lazily only at activation, so
the package is not even a hard import dependency for the disabled path.
"""

from .adapter import (
    ALLOW,
    DENY,
    LIMIT,
    AdapterOutcome,
    Mode,
    activate,
    after_tool_result,
    before_claim,
    before_model_request,
    before_tool_call,
    current_receipt,
    deactivate,
    is_active,
    is_enforcing,
    note_http_attempt,
    run_complete,
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
    "before_model_request",
    "before_tool_call",
    "after_tool_result",
    "before_claim",
    "note_http_attempt",
    "run_complete",
]
