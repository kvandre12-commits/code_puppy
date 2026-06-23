"""Tiny persistence layer for doctrine warning/adaptation receipts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .kennel import _connect
from .time_utils import now_iso
from .wings import detect_cwd


@dataclass(slots=True, frozen=True)
class DoctrineReceipt:
    id: int
    ts: str
    decision_id: str
    repo_family: str
    proposed_action: str
    warning_shown: bool
    adapted: bool
    before_summary: str
    after_summary: str


@dataclass(slots=True, frozen=True)
class DoctrineReceiptDecisionStat:
    decision_id: str
    total_count: int
    adapted_count: int


@dataclass(slots=True, frozen=True)
class DoctrineReceiptSummary:
    total_count: int
    adapted_count: int
    unchanged_count: int
    top_decisions: tuple[DoctrineReceiptDecisionStat, ...]


def record_doctrine_receipt(
    *,
    decision_id: str,
    proposed_action: str,
    warning_shown: bool,
    adapted: bool,
    before_summary: str,
    after_summary: str,
    repo_family: str = "",
    timestamp: str = "",
) -> int:
    resolved_repo_family = repo_family.strip() or infer_repo_family()
    resolved_timestamp = timestamp.strip() or now_iso()
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO doctrine_receipts(
                ts,
                decision_id,
                repo_family,
                proposed_action,
                warning_shown,
                adapted,
                before_summary,
                after_summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resolved_timestamp,
                decision_id,
                resolved_repo_family,
                proposed_action,
                int(warning_shown),
                int(adapted),
                before_summary,
                after_summary,
            ),
        )
        return int(cur.lastrowid)


def recent_doctrine_receipts(limit: int = 20) -> list[DoctrineReceipt]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM doctrine_receipts ORDER BY ts DESC, id DESC LIMIT ?",
            (max(1, limit),),
        ).fetchall()
    return [_row_to_receipt(row) for row in rows]


def summarize_doctrine_receipts(top_n: int = 5) -> DoctrineReceiptSummary:
    with _connect() as conn:
        totals = conn.execute(
            """
            SELECT
                COUNT(*) AS total_count,
                COALESCE(SUM(adapted), 0) AS adapted_count
            FROM doctrine_receipts
            """
        ).fetchone()
        top_rows = conn.execute(
            """
            SELECT
                decision_id,
                COUNT(*) AS total_count,
                COALESCE(SUM(adapted), 0) AS adapted_count
            FROM doctrine_receipts
            GROUP BY decision_id
            ORDER BY adapted_count DESC, total_count DESC, decision_id ASC
            LIMIT ?
            """,
            (max(1, top_n),),
        ).fetchall()

    total_count = int(totals["total_count"] or 0)
    adapted_count = int(totals["adapted_count"] or 0)
    return DoctrineReceiptSummary(
        total_count=total_count,
        adapted_count=adapted_count,
        unchanged_count=total_count - adapted_count,
        top_decisions=tuple(
            DoctrineReceiptDecisionStat(
                decision_id=str(row["decision_id"]),
                total_count=int(row["total_count"]),
                adapted_count=int(row["adapted_count"]),
            )
            for row in top_rows
        ),
    )


def infer_repo_family(cwd: Path | None = None) -> str:
    here = (cwd or detect_cwd()).resolve()
    name = here.name.strip().lower() or "unknown"
    for marker in ("_backup_", "-backup-"):
        if marker in name:
            name = name.split(marker, 1)[0].strip() or name
            break
    return name


def _row_to_receipt(row) -> DoctrineReceipt:
    return DoctrineReceipt(
        id=int(row["id"]),
        ts=str(row["ts"]),
        decision_id=str(row["decision_id"]),
        repo_family=str(row["repo_family"]),
        proposed_action=str(row["proposed_action"]),
        warning_shown=bool(row["warning_shown"]),
        adapted=bool(row["adapted"]),
        before_summary=str(row["before_summary"]),
        after_summary=str(row["after_summary"]),
    )
