"""SQLite storage for the persistent prompt queue plugin."""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

DEFAULT_DB_RELATIVE_PATH = "outputs/prompt_queue.sqlite3"
_ACTIVE_STATUSES = ("queued", "claimed", "running")
_TERMINAL_STATUSES = ("succeeded", "dead_letter", "cancelled")
_ALL_STATUSES = _ACTIVE_STATUSES + _TERMINAL_STATUSES


@dataclass(slots=True)
class QueueJob:
    job_id: int
    agent_name: str
    prompt: str
    session_id: str | None
    status: str
    priority: int
    attempt_count: int
    max_attempts: int
    available_at: str
    claim_token: str | None
    claimed_by: str | None
    claim_expires_at: str | None
    payload_json: str
    last_error: str | None
    result_json: str | None
    created_at: str
    updated_at: str
    started_at: str | None
    finished_at: str | None

    @property
    def payload(self) -> dict[str, Any]:
        try:
            loaded = json.loads(self.payload_json or "{}")
        except json.JSONDecodeError:
            return {}
        return loaded if isinstance(loaded, dict) else {}

    @property
    def result(self) -> dict[str, Any]:
        try:
            loaded = json.loads(self.result_json or "{}")
        except json.JSONDecodeError:
            return {}
        return loaded if isinstance(loaded, dict) else {}

    def to_dict(self, *, include_prompt: bool = True) -> dict[str, Any]:
        response = self.result.get("response")
        response_preview = None
        if isinstance(response, str) and response.strip():
            response_preview = response.strip().replace("\n", " ")[:160]
        return {
            "job_id": self.job_id,
            "agent_name": self.agent_name,
            "prompt": self.prompt if include_prompt else None,
            "session_id": self.session_id,
            "status": self.status,
            "priority": self.priority,
            "attempt_count": self.attempt_count,
            "max_attempts": self.max_attempts,
            "available_at": self.available_at,
            "claimed_by": self.claimed_by,
            "claim_expires_at": self.claim_expires_at,
            "payload": self.payload,
            "last_error": self.last_error,
            "result": self.result,
            "response_preview": response_preview,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _coerce_root(root: str = "") -> Path:
    return Path(root or ".").expanduser().resolve()


def resolve_db_path(*, root: str = "", db_path: str = "") -> Path:
    if db_path:
        path = Path(db_path).expanduser()
        if not path.is_absolute():
            path = _coerce_root(root) / path
    else:
        path = _coerce_root(root) / DEFAULT_DB_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def initialize_db(*, root: str = "", db_path: str = "") -> Path:
    path = resolve_db_path(root=root, db_path=db_path)
    with _connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS queue_jobs (
                job_id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                prompt TEXT NOT NULL,
                session_id TEXT,
                status TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 100,
                attempt_count INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL DEFAULT 3,
                available_at TEXT NOT NULL,
                claim_token TEXT,
                claimed_by TEXT,
                claim_expires_at TEXT,
                payload_json TEXT NOT NULL DEFAULT '{}',
                last_error TEXT,
                result_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_queue_jobs_status_available
                ON queue_jobs(status, available_at, priority, job_id);
            CREATE INDEX IF NOT EXISTS idx_queue_jobs_claim_expiry
                ON queue_jobs(status, claim_expires_at);
            CREATE TABLE IF NOT EXISTS queue_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                event_at TEXT NOT NULL,
                details_json TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY(job_id) REFERENCES queue_jobs(job_id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_queue_events_job_id
                ON queue_events(job_id, event_at);
            """
        )
    return path


def _row_to_job(row: sqlite3.Row | None) -> QueueJob | None:
    if row is None:
        return None
    return QueueJob(
        job_id=int(row["job_id"]),
        agent_name=str(row["agent_name"]),
        prompt=str(row["prompt"]),
        session_id=row["session_id"],
        status=str(row["status"]),
        priority=int(row["priority"]),
        attempt_count=int(row["attempt_count"]),
        max_attempts=int(row["max_attempts"]),
        available_at=str(row["available_at"]),
        claim_token=row["claim_token"],
        claimed_by=row["claimed_by"],
        claim_expires_at=row["claim_expires_at"],
        payload_json=str(row["payload_json"] or "{}"),
        last_error=row["last_error"],
        result_json=row["result_json"],
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        started_at=row["started_at"],
        finished_at=row["finished_at"],
    )


def _append_event(
    conn: sqlite3.Connection,
    *,
    job_id: int,
    event_type: str,
    details: dict[str, Any] | None = None,
) -> None:
    conn.execute(
        "INSERT INTO queue_events(job_id, event_type, event_at, details_json) VALUES (?, ?, ?, ?)",
        (
            job_id,
            event_type,
            _iso(_utc_now()),
            json.dumps(details or {}, sort_keys=True),
        ),
    )


def enqueue_job(
    *,
    agent_name: str,
    prompt: str,
    session_id: str | None = None,
    priority: int = 100,
    max_attempts: int = 3,
    available_in_seconds: int = 0,
    payload: dict[str, Any] | None = None,
    root: str = "",
    db_path: str = "",
) -> dict[str, Any]:
    if not agent_name.strip():
        raise ValueError("agent_name cannot be empty")
    if not prompt.strip():
        raise ValueError("prompt cannot be empty")
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    path = initialize_db(root=root, db_path=db_path)
    now = _utc_now()
    available_at = _iso(now + timedelta(seconds=max(0, available_in_seconds)))
    created_at = _iso(now)
    encoded_payload = json.dumps(payload or {}, sort_keys=True)

    with _connect(path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO queue_jobs(
                agent_name, prompt, session_id, status, priority, attempt_count,
                max_attempts, available_at, payload_json, created_at, updated_at
            ) VALUES (?, ?, ?, 'queued', ?, 0, ?, ?, ?, ?, ?)
            """,
            (
                agent_name.strip(),
                prompt,
                session_id,
                int(priority),
                int(max_attempts),
                available_at,
                encoded_payload,
                created_at,
                created_at,
            ),
        )
        job_id = int(cursor.lastrowid)
        _append_event(
            conn,
            job_id=job_id,
            event_type="enqueued",
            details={"priority": int(priority)},
        )
        row = conn.execute(
            "SELECT * FROM queue_jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        job = _row_to_job(row)
    return {
        "ok": True,
        "db_path": str(path),
        "job": job.to_dict() if job else {"job_id": job_id},
    }


def get_job(*, job_id: int, root: str = "", db_path: str = "") -> QueueJob | None:
    path = initialize_db(root=root, db_path=db_path)
    with _connect(path) as conn:
        row = conn.execute(
            "SELECT * FROM queue_jobs WHERE job_id = ?", (int(job_id),)
        ).fetchone()
    return _row_to_job(row)


def list_jobs(
    *,
    status: str = "",
    limit: int = 20,
    root: str = "",
    db_path: str = "",
) -> dict[str, Any]:
    path = initialize_db(root=root, db_path=db_path)
    normalized_status = status.strip().lower()
    sql = (
        "SELECT * FROM queue_jobs "
        "WHERE (? = '' OR status = ?) "
        "ORDER BY CASE status WHEN 'queued' THEN 0 WHEN 'claimed' THEN 1 WHEN 'running' THEN 2 ELSE 3 END, "
        "priority ASC, job_id ASC LIMIT ?"
    )
    with _connect(path) as conn:
        rows = conn.execute(
            sql, (normalized_status, normalized_status, max(1, int(limit)))
        ).fetchall()
    jobs: list[dict[str, Any]] = []
    for row in rows:
        job = _row_to_job(row)
        if job is not None:
            jobs.append(job.to_dict())
    return {
        "ok": True,
        "db_path": str(path),
        "status_filter": normalized_status or None,
        "jobs": jobs,
        "returned": len(jobs),
    }


def _requeue_expired_claims(conn: sqlite3.Connection, *, now_iso: str) -> int:
    rows = conn.execute(
        """
        SELECT job_id, status, claimed_by FROM queue_jobs
        WHERE status IN ('claimed', 'running')
          AND claim_expires_at IS NOT NULL
          AND claim_expires_at <= ?
        """,
        (now_iso,),
    ).fetchall()
    expired = 0
    for row in rows:
        expired += 1
        conn.execute(
            """
            UPDATE queue_jobs
               SET status = 'queued',
                   claim_token = NULL,
                   claimed_by = NULL,
                   claim_expires_at = NULL,
                   updated_at = ?,
                   available_at = ?
             WHERE job_id = ?
            """,
            (now_iso, now_iso, int(row["job_id"])),
        )
        _append_event(
            conn,
            job_id=int(row["job_id"]),
            event_type="claim_expired",
            details={
                "previous_status": str(row["status"]),
                "claimed_by": row["claimed_by"],
            },
        )
    return expired


def claim_next_job(
    *,
    worker_id: str,
    claim_ttl_seconds: int = 900,
    exclude_job_ids: list[int] | None = None,
    root: str = "",
    db_path: str = "",
) -> dict[str, Any]:
    if not worker_id.strip():
        raise ValueError("worker_id cannot be empty")

    path = initialize_db(root=root, db_path=db_path)
    now = _utc_now()
    now_iso = _iso(now)
    expires_at = _iso(now + timedelta(seconds=max(1, int(claim_ttl_seconds))))
    claim_token = uuid.uuid4().hex
    excluded_ids = [int(job_id) for job_id in (exclude_job_ids or [])]
    exclusion_sql = ""
    params: list[Any] = [now_iso]
    if excluded_ids:
        placeholders = ", ".join("?" for _ in excluded_ids)
        exclusion_sql = f" AND job_id NOT IN ({placeholders})"
        params.extend(excluded_ids)

    with _connect(path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        expired_count = _requeue_expired_claims(conn, now_iso=now_iso)
        row = conn.execute(
            f"""
            SELECT * FROM queue_jobs
             WHERE status = 'queued' AND available_at <= ?{exclusion_sql}
             ORDER BY priority ASC, job_id ASC
             LIMIT 1
            """,
            tuple(params),
        ).fetchone()
        job = _row_to_job(row)
        if job is None:
            conn.commit()
            return {
                "ok": True,
                "db_path": str(path),
                "expired_requeued": expired_count,
                "job": None,
            }

        conn.execute(
            """
            UPDATE queue_jobs
               SET status = 'claimed',
                   claim_token = ?,
                   claimed_by = ?,
                   claim_expires_at = ?,
                   updated_at = ?
             WHERE job_id = ?
            """,
            (claim_token, worker_id, expires_at, now_iso, job.job_id),
        )
        _append_event(
            conn,
            job_id=job.job_id,
            event_type="claimed",
            details={"worker_id": worker_id, "claim_expires_at": expires_at},
        )
        claimed_row = conn.execute(
            "SELECT * FROM queue_jobs WHERE job_id = ?", (job.job_id,)
        ).fetchone()
        conn.commit()
    claimed_job = _row_to_job(claimed_row)
    return {
        "ok": True,
        "db_path": str(path),
        "expired_requeued": expired_count,
        "job": claimed_job.to_dict() if claimed_job else None,
        "claim_token": claim_token,
    }


def mark_job_running(
    *, job_id: int, claim_token: str, root: str = "", db_path: str = ""
) -> QueueJob:
    path = initialize_db(root=root, db_path=db_path)
    now_iso = _iso(_utc_now())
    with _connect(path) as conn:
        updated = conn.execute(
            """
            UPDATE queue_jobs
               SET status = 'running',
                   attempt_count = attempt_count + 1,
                   started_at = COALESCE(started_at, ?),
                   updated_at = ?
             WHERE job_id = ? AND claim_token = ? AND status = 'claimed'
            """,
            (now_iso, now_iso, int(job_id), claim_token),
        )
        if updated.rowcount != 1:
            raise ValueError(f"Could not mark job {job_id} as running")
        _append_event(conn, job_id=int(job_id), event_type="running", details={})
        row = conn.execute(
            "SELECT * FROM queue_jobs WHERE job_id = ?", (int(job_id),)
        ).fetchone()
    job = _row_to_job(row)
    if job is None:
        raise ValueError(f"Job {job_id} disappeared while marking running")
    return job


def complete_job(
    *,
    job_id: int,
    claim_token: str,
    result: dict[str, Any],
    root: str = "",
    db_path: str = "",
) -> QueueJob:
    path = initialize_db(root=root, db_path=db_path)
    now_iso = _iso(_utc_now())
    encoded_result = json.dumps(result, sort_keys=True)
    with _connect(path) as conn:
        updated = conn.execute(
            """
            UPDATE queue_jobs
               SET status = 'succeeded',
                   result_json = ?,
                   claim_token = NULL,
                   claimed_by = NULL,
                   claim_expires_at = NULL,
                   updated_at = ?,
                   finished_at = ?
             WHERE job_id = ? AND claim_token = ? AND status = 'running'
            """,
            (encoded_result, now_iso, now_iso, int(job_id), claim_token),
        )
        if updated.rowcount != 1:
            raise ValueError(f"Could not complete job {job_id}")
        _append_event(conn, job_id=int(job_id), event_type="succeeded", details={})
        row = conn.execute(
            "SELECT * FROM queue_jobs WHERE job_id = ?", (int(job_id),)
        ).fetchone()
    job = _row_to_job(row)
    if job is None:
        raise ValueError(f"Job {job_id} disappeared while completing")
    return job


def fail_job(
    *,
    job_id: int,
    claim_token: str,
    error_text: str,
    backoff_seconds: int,
    root: str = "",
    db_path: str = "",
) -> QueueJob:
    path = initialize_db(root=root, db_path=db_path)
    now = _utc_now()
    now_iso = _iso(now)
    with _connect(path) as conn:
        row = conn.execute(
            "SELECT * FROM queue_jobs WHERE job_id = ? AND claim_token = ? AND status = 'running'",
            (int(job_id), claim_token),
        ).fetchone()
        job = _row_to_job(row)
        if job is None:
            raise ValueError(f"Could not fail job {job_id}")

        is_dead = job.attempt_count >= job.max_attempts
        if is_dead:
            conn.execute(
                """
                UPDATE queue_jobs
                   SET status = 'dead_letter',
                       last_error = ?,
                       claim_token = NULL,
                       claimed_by = NULL,
                       claim_expires_at = NULL,
                       updated_at = ?,
                       finished_at = ?
                 WHERE job_id = ?
                """,
                (error_text, now_iso, now_iso, int(job_id)),
            )
            event_type = "dead_lettered"
            details = {"error": error_text, "attempt_count": job.attempt_count}
        else:
            next_available = _iso(now + timedelta(seconds=max(0, int(backoff_seconds))))
            conn.execute(
                """
                UPDATE queue_jobs
                   SET status = 'queued',
                       last_error = ?,
                       claim_token = NULL,
                       claimed_by = NULL,
                       claim_expires_at = NULL,
                       updated_at = ?,
                       available_at = ?
                 WHERE job_id = ?
                """,
                (error_text, now_iso, next_available, int(job_id)),
            )
            event_type = "requeued"
            details = {
                "error": error_text,
                "attempt_count": job.attempt_count,
                "available_at": next_available,
            }
        _append_event(conn, job_id=int(job_id), event_type=event_type, details=details)
        updated_row = conn.execute(
            "SELECT * FROM queue_jobs WHERE job_id = ?", (int(job_id),)
        ).fetchone()
    updated_job = _row_to_job(updated_row)
    if updated_job is None:
        raise ValueError(f"Job {job_id} disappeared while failing")
    return updated_job


def retry_job(*, job_id: int, root: str = "", db_path: str = "") -> dict[str, Any]:
    path = initialize_db(root=root, db_path=db_path)
    now_iso = _iso(_utc_now())
    with _connect(path) as conn:
        updated = conn.execute(
            """
            UPDATE queue_jobs
               SET status = 'queued',
                   attempt_count = 0,
                   claim_token = NULL,
                   claimed_by = NULL,
                   claim_expires_at = NULL,
                   available_at = ?,
                   updated_at = ?,
                   finished_at = NULL
             WHERE job_id = ? AND status IN ('dead_letter', 'cancelled')
            """,
            (now_iso, now_iso, int(job_id)),
        )
        if updated.rowcount != 1:
            return {"ok": False, "error": f"Job {job_id} is not retryable."}
        _append_event(
            conn, job_id=int(job_id), event_type="manually_requeued", details={}
        )
    job = get_job(job_id=job_id, db_path=str(path))
    return {"ok": True, "db_path": str(path), "job": job.to_dict() if job else None}


def cancel_job(*, job_id: int, root: str = "", db_path: str = "") -> dict[str, Any]:
    path = initialize_db(root=root, db_path=db_path)
    now_iso = _iso(_utc_now())
    with _connect(path) as conn:
        updated = conn.execute(
            """
            UPDATE queue_jobs
               SET status = 'cancelled',
                   claim_token = NULL,
                   claimed_by = NULL,
                   claim_expires_at = NULL,
                   updated_at = ?,
                   finished_at = COALESCE(finished_at, ?)
             WHERE job_id = ? AND status IN ('queued', 'claimed', 'running')
            """,
            (now_iso, now_iso, int(job_id)),
        )
        if updated.rowcount != 1:
            return {"ok": False, "error": f"Job {job_id} is not cancellable."}
        _append_event(conn, job_id=int(job_id), event_type="cancelled", details={})
    job = get_job(job_id=job_id, db_path=str(path))
    return {"ok": True, "db_path": str(path), "job": job.to_dict() if job else None}


def queue_status(*, root: str = "", db_path: str = "") -> dict[str, Any]:
    path = initialize_db(root=root, db_path=db_path)
    now_iso = _iso(_utc_now())
    with _connect(path) as conn:
        counts = {
            row["status"]: int(row["count"])
            for row in conn.execute(
                "SELECT status, COUNT(*) AS count FROM queue_jobs GROUP BY status"
            ).fetchall()
        }
        next_row = conn.execute(
            """
            SELECT * FROM queue_jobs
             WHERE status = 'queued'
             ORDER BY available_at ASC, priority ASC, job_id ASC
             LIMIT 1
            """
        ).fetchone()
        next_job = _row_to_job(next_row)
        available_now = conn.execute(
            "SELECT COUNT(*) AS count FROM queue_jobs WHERE status = 'queued' AND available_at <= ?",
            (now_iso,),
        ).fetchone()
        event_count = conn.execute(
            "SELECT COUNT(*) AS count FROM queue_events"
        ).fetchone()
    normalized_counts = {status: int(counts.get(status, 0)) for status in _ALL_STATUSES}
    return {
        "ok": True,
        "db_path": str(path),
        "counts": normalized_counts,
        "available_now": int(available_now["count"] if available_now else 0),
        "event_count": int(event_count["count"] if event_count else 0),
        "next_job": next_job.to_dict(include_prompt=False) if next_job else None,
    }
