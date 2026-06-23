"""Shared rendering helpers for doctrine/decision explanation surfaces."""

from __future__ import annotations

from typing import Any


def render_decision_detail(record: Any) -> str:
    """Render one decision as a human-readable doctrine explanation block."""
    if record is None:
        return ""

    evidence = _render_list(getattr(record, "evidence_artifact_ids", []) or [])
    repos = _render_list(
        getattr(record, "affected_repos", []) or [],
        sort_values=True,
    )
    last_reviewed = str(getattr(record, "last_reviewed_at", "") or "unknown")
    created_at = str(getattr(record, "created_at", "") or "unknown")

    lines = [
        f"Decision: {getattr(record, 'title', '')}",
        f"Decision ID: {getattr(record, 'id', '')}",
        f"Status: {getattr(record, 'status', '')}",
        f"Confidence: {getattr(record, 'confidence', '')}",
        f"Summary: {getattr(record, 'summary', '')}",
        f"Rationale: {getattr(record, 'rationale', '')}",
        f"Evidence: {evidence}",
        f"Affected Repos: {repos}",
        f"Last Reviewed: {last_reviewed}",
        f"Created: {created_at}",
    ]
    return "\n".join(lines)


def _render_list(values: list[str], sort_values: bool = False) -> str:
    cleaned = [str(value).strip() for value in values if str(value).strip()]
    if sort_values:
        cleaned = sorted(cleaned, key=str.casefold)
    return " ".join(cleaned) if cleaned else "none recorded"
