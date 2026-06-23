"""Decision v0 for puppy_kennel.

A deliberately tiny vertical slice:
- one durable knowledge object: ``Decision``
- one write helper: ``kennel_upsert_decision``
- two read queries: ``kennel_list_decisions`` and ``kennel_get_active_decisions``

No facts. No claims. No ontology engine. Calm down, civilization.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import RunContext

from . import kennel
from .doctrine_render import render_decision_detail
from .state import DISABLED_TOOL_ERROR, is_enabled
from .time_utils import now_iso

_VALID_STATUSES = ("proposed", "active", "superseded", "rejected")
_VALID_CONFIDENCE = ("low", "medium", "high")
_MAX_LIST_RESULTS = 200
_REPO_ALIAS_SUFFIX_PATTERNS = (
    r"(?:[_-]backup[_-]?\d{6,})$",
    r"(?:[_-]copy)$",
    r"(?:[_-]\d{8,})$",
)


@dataclass(slots=True, frozen=True)
class DecisionRecord:
    """Stored Decision v0 record."""

    id: str
    title: str
    status: str
    confidence: str
    summary: str
    rationale: str
    affected_repos: list[str]
    evidence_artifact_ids: list[str]
    created_at: str
    last_reviewed_at: str
    supersedes: list[str]
    superseded_by: list[str]


class DecisionModel(BaseModel):
    """Tool-facing Decision v0 payload."""

    id: str
    title: str
    status: str
    confidence: str
    summary: str
    rationale: str
    affected_repos: list[str] = Field(default_factory=list)
    evidence_artifact_ids: list[str] = Field(default_factory=list)
    created_at: str
    last_reviewed_at: str
    supersedes: list[str] = Field(default_factory=list)
    superseded_by: list[str] = Field(default_factory=list)


class KennelDecisionWriteOutput(BaseModel):
    """Output for ``kennel_upsert_decision``."""

    decision: DecisionModel | None = None
    created: bool = False
    error: str | None = None


class KennelDecisionListOutput(BaseModel):
    """Output for list-style decision queries."""

    total: int
    decisions: list[DecisionModel] = Field(default_factory=list)
    error: str | None = None


class KennelDecisionGetOutput(BaseModel):
    """Output for ``kennel_get_decision``."""

    decision: DecisionModel | None = None
    rendered: str = ""
    error: str | None = None


def _clean_scalar(value: str) -> str:
    return (value or "").strip()


def _clean_list(values: list[str] | None) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for raw in values or []:
        item = _clean_scalar(raw)
        if not item or item in seen:
            continue
        seen.add(item)
        cleaned.append(item)
    return cleaned


def _normalize_status(value: str) -> str:
    normalized = _clean_scalar(value).lower()
    if normalized not in _VALID_STATUSES:
        allowed = ", ".join(_VALID_STATUSES)
        raise ValueError(f"Invalid status '{value}'. Expected one of: {allowed}.")
    return normalized


def _normalize_confidence(value: str) -> str:
    normalized = _clean_scalar(value).lower()
    if normalized not in _VALID_CONFIDENCE:
        allowed = ", ".join(_VALID_CONFIDENCE)
        raise ValueError(f"Invalid confidence '{value}'. Expected one of: {allowed}.")
    return normalized


def _slugify_decision_id(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:80]


def _record_to_model(record: DecisionRecord) -> DecisionModel:
    return DecisionModel(
        id=record.id,
        title=record.title,
        status=record.status,
        confidence=record.confidence,
        summary=record.summary,
        rationale=record.rationale,
        affected_repos=list(record.affected_repos),
        evidence_artifact_ids=list(record.evidence_artifact_ids),
        created_at=record.created_at,
        last_reviewed_at=record.last_reviewed_at,
        supersedes=list(record.supersedes),
        superseded_by=list(record.superseded_by),
    )


def _row_to_decision(row: Any) -> DecisionRecord:
    return DecisionRecord(
        id=row["id"],
        title=row["title"],
        status=row["status"],
        confidence=row["confidence"],
        summary=row["summary"],
        rationale=row["rationale"],
        affected_repos=[],
        evidence_artifact_ids=[],
        created_at=row["created_at"],
        last_reviewed_at=row["last_reviewed_at"],
        supersedes=json.loads(row["supersedes_json"] or "[]"),
        superseded_by=json.loads(row["superseded_by_json"] or "[]"),
    )


def _link_values(conn: Any, table: str, column: str, decision_id: str) -> list[str]:
    rows = conn.execute(
        f"SELECT {column} FROM {table} WHERE decision_id = ? ORDER BY {column} ASC",
        (decision_id,),
    ).fetchall()
    return [_clean_scalar(row[column]) for row in rows if _clean_scalar(row[column])]


def _hydrate_decision(conn: Any, row: Any) -> DecisionRecord:
    base = _row_to_decision(row)
    return DecisionRecord(
        id=base.id,
        title=base.title,
        status=base.status,
        confidence=base.confidence,
        summary=base.summary,
        rationale=base.rationale,
        affected_repos=_link_values(conn, "decision_repos", "repo_name", base.id),
        evidence_artifact_ids=_link_values(
            conn,
            "decision_evidence_artifacts",
            "artifact_id",
            base.id,
        ),
        created_at=base.created_at,
        last_reviewed_at=base.last_reviewed_at,
        supersedes=base.supersedes,
        superseded_by=base.superseded_by,
    )


def get_decision(decision_id: str) -> DecisionRecord | None:
    """Fetch one decision by id."""
    resolved_id = _clean_scalar(decision_id)
    if not resolved_id:
        return None
    with kennel._connect() as conn:  # noqa: SLF001 - internal package seam.
        row = conn.execute(
            "SELECT * FROM decisions WHERE id = ?",
            (resolved_id,),
        ).fetchone()
        if row is None:
            return None
        return _hydrate_decision(conn, row)


def list_decisions(limit: int = 100) -> list[DecisionRecord]:
    """Return all decisions newest-reviewed first, active first."""
    resolved_limit = max(1, min(int(limit), _MAX_LIST_RESULTS))
    with kennel._connect() as conn:  # noqa: SLF001 - internal package seam.
        rows = conn.execute(
            """
            SELECT * FROM decisions
            ORDER BY
                CASE status
                    WHEN 'active' THEN 0
                    WHEN 'proposed' THEN 1
                    WHEN 'superseded' THEN 2
                    ELSE 3
                END,
                last_reviewed_at DESC,
                created_at DESC,
                id ASC
            LIMIT ?
            """,
            (resolved_limit,),
        ).fetchall()
        return [_hydrate_decision(conn, row) for row in rows]


def get_active_decisions(repo: str, limit: int = 100) -> list[DecisionRecord]:
    """Return active decisions that affect the named repo."""
    repo_name = _clean_scalar(repo)
    if not repo_name:
        return []
    resolved_limit = max(1, min(int(limit), _MAX_LIST_RESULTS))
    with kennel._connect() as conn:  # noqa: SLF001 - internal package seam.
        rows = conn.execute(
            """
            SELECT d.*
            FROM decisions d
            JOIN decision_repos r ON r.decision_id = d.id
            WHERE d.status = 'active' AND LOWER(r.repo_name) = LOWER(?)
            ORDER BY d.last_reviewed_at DESC, d.created_at DESC, d.id ASC
            LIMIT ?
            """,
            (repo_name, resolved_limit),
        ).fetchall()
        return [_hydrate_decision(conn, row) for row in rows]


def repo_name_candidates_for_cwd(cwd: str | Path | None) -> list[str]:
    """Infer likely logical repo names from a cwd path.

    This lets doctrine tagged to ``code_puppy`` still surface when the local
    checkout is named something like ``code_puppy_backup_20260617``.
    """
    raw_name = Path(str(cwd or "")).name.strip()
    if not raw_name:
        return []

    candidates: list[str] = []
    seen: set[str] = set()

    def _add(value: str) -> None:
        cleaned = _clean_scalar(value)
        if not cleaned:
            return
        lowered = cleaned.lower()
        if lowered in seen:
            return
        seen.add(lowered)
        candidates.append(cleaned)

    _add(raw_name)
    normalized = raw_name
    for pattern in _REPO_ALIAS_SUFFIX_PATTERNS:
        normalized = re.sub(pattern, "", normalized, flags=re.IGNORECASE)
    _add(normalized)
    return candidates


def get_active_decisions_for_cwd(
    cwd: str | Path | None,
    limit: int = 100,
) -> list[DecisionRecord]:
    """Return active decisions affecting the logical repo inferred from ``cwd``."""
    resolved_limit = max(1, min(int(limit), _MAX_LIST_RESULTS))
    seen_ids: set[str] = set()
    records: list[DecisionRecord] = []
    for candidate in repo_name_candidates_for_cwd(cwd):
        for decision in get_active_decisions(candidate, limit=resolved_limit):
            if decision.id in seen_ids:
                continue
            seen_ids.add(decision.id)
            records.append(decision)
            if len(records) >= resolved_limit:
                return records
    return records


def render_active_decision_lines_for_cwd(
    cwd: str | Path | None,
    limit: int = 5,
) -> list[str]:
    """Render compact one-line doctrine bullets for the active repo."""
    records = get_active_decisions_for_cwd(cwd, limit=limit)
    return [
        f"- {record.title} — status: {record.status}, confidence: {record.confidence}"
        for record in records
    ]


def upsert_decision(record: DecisionRecord) -> tuple[DecisionRecord, bool]:
    """Insert or update a Decision v0 record."""
    resolved_id = _clean_scalar(record.id) or _slugify_decision_id(record.title)
    title = _clean_scalar(record.title)
    summary = _clean_scalar(record.summary)
    rationale = _clean_scalar(record.rationale)
    if not resolved_id:
        raise ValueError("Decision id is required (or deriveable from title).")
    if not title:
        raise ValueError("Decision title is required.")
    if not summary:
        raise ValueError("Decision summary is required.")
    if not rationale:
        raise ValueError("Decision rationale is required.")

    status = _normalize_status(record.status)
    confidence = _normalize_confidence(record.confidence)
    affected_repos = _clean_list(record.affected_repos)
    evidence_artifact_ids = _clean_list(record.evidence_artifact_ids)
    supersedes = _clean_list(record.supersedes)
    superseded_by = _clean_list(record.superseded_by)

    with kennel._connect() as conn:  # noqa: SLF001 - internal package seam.
        existing = conn.execute(
            "SELECT created_at FROM decisions WHERE id = ?",
            (resolved_id,),
        ).fetchone()
        created = existing is None
        created_at = _clean_scalar(record.created_at) or (
            existing["created_at"] if existing else now_iso()
        )
        last_reviewed_at = _clean_scalar(record.last_reviewed_at) or now_iso()

        conn.execute(
            """
            INSERT INTO decisions(
                id,
                title,
                status,
                confidence,
                summary,
                rationale,
                created_at,
                last_reviewed_at,
                supersedes_json,
                superseded_by_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                status = excluded.status,
                confidence = excluded.confidence,
                summary = excluded.summary,
                rationale = excluded.rationale,
                created_at = excluded.created_at,
                last_reviewed_at = excluded.last_reviewed_at,
                supersedes_json = excluded.supersedes_json,
                superseded_by_json = excluded.superseded_by_json
            """,
            (
                resolved_id,
                title,
                status,
                confidence,
                summary,
                rationale,
                created_at,
                last_reviewed_at,
                json.dumps(supersedes),
                json.dumps(superseded_by),
            ),
        )
        conn.execute("DELETE FROM decision_repos WHERE decision_id = ?", (resolved_id,))
        conn.execute(
            "DELETE FROM decision_evidence_artifacts WHERE decision_id = ?",
            (resolved_id,),
        )
        conn.executemany(
            "INSERT INTO decision_repos(decision_id, repo_name) VALUES (?, ?)",
            [(resolved_id, repo_name) for repo_name in affected_repos],
        )
        conn.executemany(
            """
            INSERT INTO decision_evidence_artifacts(decision_id, artifact_id)
            VALUES (?, ?)
            """,
            [(resolved_id, artifact_id) for artifact_id in evidence_artifact_ids],
        )
        row = conn.execute(
            "SELECT * FROM decisions WHERE id = ?",
            (resolved_id,),
        ).fetchone()
        assert row is not None
        return _hydrate_decision(conn, row), created


def register_kennel_upsert_decision(agent: Any) -> None:
    """Register ``kennel_upsert_decision``."""

    @agent.tool
    async def kennel_upsert_decision(
        context: RunContext,
        title: str,
        rationale: str,
        id: str = "",
        status: str = "proposed",
        confidence: str = "medium",
        summary: str = "",
        affected_repos: list[str] | None = None,
        evidence_artifact_ids: list[str] | None = None,
        created_at: str = "",
        last_reviewed_at: str = "",
        supersedes: list[str] | None = None,
        superseded_by: list[str] | None = None,
    ) -> KennelDecisionWriteOutput:
        """Create or update a Decision v0 record.

        This is the first durable knowledge primitive in the kennel's shift
        from transcript archive toward truth refinery.
        """
        _ = context
        if not is_enabled():
            return KennelDecisionWriteOutput(error=DISABLED_TOOL_ERROR)
        try:
            stored, created = upsert_decision(
                DecisionRecord(
                    id=_clean_scalar(id) or _slugify_decision_id(title),
                    title=title,
                    status=status,
                    confidence=confidence,
                    summary=_clean_scalar(summary) or _clean_scalar(title),
                    rationale=rationale,
                    affected_repos=affected_repos or [],
                    evidence_artifact_ids=evidence_artifact_ids or [],
                    created_at=created_at,
                    last_reviewed_at=last_reviewed_at,
                    supersedes=supersedes or [],
                    superseded_by=superseded_by or [],
                )
            )
            return KennelDecisionWriteOutput(
                decision=_record_to_model(stored),
                created=created,
            )
        except Exception as exc:  # noqa: BLE001 - tool must fail soft.
            return KennelDecisionWriteOutput(
                error=f"kennel_upsert_decision failed: {exc}"
            )


def register_kennel_list_decisions(agent: Any) -> None:
    """Register ``kennel_list_decisions``."""

    @agent.tool
    async def kennel_list_decisions(
        context: RunContext,
        limit: int = 50,
    ) -> KennelDecisionListOutput:
        """List stored decisions, active ones first."""
        _ = context
        if not is_enabled():
            return KennelDecisionListOutput(total=0, error=DISABLED_TOOL_ERROR)
        try:
            records = list_decisions(limit=limit)
            return KennelDecisionListOutput(
                total=len(records),
                decisions=[_record_to_model(record) for record in records],
            )
        except Exception as exc:  # noqa: BLE001 - tool must fail soft.
            return KennelDecisionListOutput(
                total=0,
                error=f"kennel_list_decisions failed: {exc!r}",
            )


def register_kennel_get_active_decisions(agent: Any) -> None:
    """Register ``kennel_get_active_decisions``."""

    @agent.tool
    async def kennel_get_active_decisions(
        context: RunContext,
        repo: str,
        limit: int = 50,
    ) -> KennelDecisionListOutput:
        """Return active decisions that constrain work in a repo."""
        _ = context
        repo_name = _clean_scalar(repo)
        if not is_enabled():
            return KennelDecisionListOutput(total=0, error=DISABLED_TOOL_ERROR)
        if not repo_name:
            return KennelDecisionListOutput(
                total=0,
                error="Repo is required for kennel_get_active_decisions.",
            )
        try:
            records = get_active_decisions(repo=repo_name, limit=limit)
            return KennelDecisionListOutput(
                total=len(records),
                decisions=[_record_to_model(record) for record in records],
            )
        except Exception as exc:  # noqa: BLE001 - tool must fail soft.
            return KennelDecisionListOutput(
                total=0,
                error=f"kennel_get_active_decisions failed: {exc!r}",
            )


def register_kennel_get_decision(agent: Any) -> None:
    """Register ``kennel_get_decision``."""

    @agent.tool
    async def kennel_get_decision(
        context: RunContext,
        decision_id: str,
    ) -> KennelDecisionGetOutput:
        """Return one decision with rationale/evidence drill-down text."""
        _ = context
        resolved_id = _clean_scalar(decision_id)
        if not is_enabled():
            return KennelDecisionGetOutput(error=DISABLED_TOOL_ERROR)
        if not resolved_id:
            return KennelDecisionGetOutput(
                error="decision_id is required for kennel_get_decision.",
            )
        try:
            record = get_decision(resolved_id)
            if record is None:
                return KennelDecisionGetOutput(
                    error=f"Decision not found: {resolved_id}",
                )
            return KennelDecisionGetOutput(
                decision=_record_to_model(record),
                rendered=render_decision_detail(record),
            )
        except Exception as exc:  # noqa: BLE001 - tool must fail soft.
            return KennelDecisionGetOutput(
                error=f"kennel_get_decision failed: {exc!r}",
            )
