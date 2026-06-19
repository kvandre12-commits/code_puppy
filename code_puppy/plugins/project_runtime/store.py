"""Persistent Project Run store for the Project OS runtime primitive."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from typing import Any

from code_puppy.config import STATE_DIR

STATE_FILE = os.path.join(STATE_DIR, "project_runs.json")

RUN_STATUSES = {
    "created",
    "ready",
    "running",
    "sleeping",
    "waiting_event",
    "waiting_approval",
    "blocked",
    "suspended",
    "completed",
    "failed",
    "archived",
}


@dataclass(frozen=True, slots=True)
class WorkItem:
    title: str
    status: str = "planned"


@dataclass(frozen=True, slots=True)
class JournalEvent:
    ts: str
    action: str
    detail: str = ""


@dataclass(frozen=True, slots=True)
class ProjectRun:
    run_id: str
    project: str
    objective: str
    work_items: tuple[WorkItem, ...] = ()
    status: str = "sleeping"
    checkpoint: str = ""
    next_action: str = ""
    created_at: str = ""
    updated_at: str = ""
    resumed_at: str = ""
    completed_at: str = ""
    journal: tuple[JournalEvent, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class EventRecord:
    event_id: str
    run_id: str
    event_type: str
    timestamp: str
    source: str
    payload_summary: str = ""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slugify(value: str) -> str:
    """Return a conservative id fragment."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "run"


def normalize_status(status: str) -> str:
    normalized = status.strip().lower().replace("-", "_")
    if normalized == "sleep":
        normalized = "sleeping"
    if normalized not in RUN_STATUSES:
        allowed = ", ".join(sorted(RUN_STATUSES))
        raise ValueError(f"unknown run status {status!r}; allowed: {allowed}")
    return normalized


def empty_state() -> dict[str, Any]:
    return {"version": 1, "runs": {}, "events": {}}


def load_state() -> dict[str, Any]:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as fh:
            state = json.load(fh)
    except FileNotFoundError:
        return empty_state()
    except json.JSONDecodeError:
        return empty_state()
    if not isinstance(state, dict) or not isinstance(state.get("runs"), dict):
        return empty_state()
    state.setdefault("version", 1)
    if not isinstance(state.get("events"), dict):
        state["events"] = {}
    return state


def save_state(state: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), mode=0o700, exist_ok=True)
    tmp_path = f"{STATE_FILE}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp_path, STATE_FILE)


def _work_item_from_raw(raw: Any) -> WorkItem:
    if isinstance(raw, dict):
        return WorkItem(
            title=str(raw.get("title") or "").strip(),
            status=str(raw.get("status") or "planned").strip() or "planned",
        )
    return WorkItem(title=str(raw).strip(), status="planned")


def _journal_from_raw(raw: Any) -> JournalEvent:
    if isinstance(raw, dict):
        return JournalEvent(
            ts=str(raw.get("ts") or ""),
            action=str(raw.get("action") or ""),
            detail=str(raw.get("detail") or ""),
        )
    return JournalEvent(ts="", action="unknown", detail=str(raw))


def run_from_dict(raw: dict[str, Any]) -> ProjectRun:
    work_items = tuple(
        item
        for item in (_work_item_from_raw(v) for v in raw.get("work_items", []))
        if item.title
    )
    journal = tuple(
        event
        for event in (_journal_from_raw(v) for v in raw.get("journal", []))
        if event.action
    )
    return ProjectRun(
        run_id=str(raw.get("run_id") or ""),
        project=str(raw.get("project") or ""),
        objective=str(raw.get("objective") or ""),
        work_items=work_items,
        status=normalize_status(str(raw.get("status") or "sleeping")),
        checkpoint=str(raw.get("checkpoint") or ""),
        next_action=str(raw.get("next_action") or ""),
        created_at=str(raw.get("created_at") or ""),
        updated_at=str(raw.get("updated_at") or ""),
        resumed_at=str(raw.get("resumed_at") or ""),
        completed_at=str(raw.get("completed_at") or ""),
        journal=journal,
    )


def run_to_dict(run: ProjectRun) -> dict[str, Any]:
    return asdict(run)


def event_from_dict(raw: dict[str, Any]) -> EventRecord:
    return EventRecord(
        event_id=str(raw.get("event_id") or ""),
        run_id=str(raw.get("run_id") or ""),
        event_type=str(raw.get("event_type") or ""),
        timestamp=str(raw.get("timestamp") or ""),
        source=str(raw.get("source") or ""),
        payload_summary=str(raw.get("payload_summary") or ""),
    )


def event_to_dict(event: EventRecord) -> dict[str, Any]:
    return asdict(event)


def append_journal(run: ProjectRun, action: str, detail: str = "") -> ProjectRun:
    event = JournalEvent(ts=utc_now_iso(), action=action, detail=detail)
    return replace(run, journal=(*run.journal, event))


def list_runs(status: str | None = None) -> list[ProjectRun]:
    state = load_state()
    wanted_status = normalize_status(status) if status else None
    runs = [run_from_dict(raw) for raw in state.get("runs", {}).values()]
    if wanted_status:
        runs = [run for run in runs if run.status == wanted_status]
    return sorted(runs, key=lambda run: (run.updated_at, run.run_id), reverse=True)


def get_run(run_id: str) -> ProjectRun:
    raw = load_state().get("runs", {}).get(run_id)
    if not isinstance(raw, dict):
        raise KeyError(f"Project Run not found: {run_id}")
    return run_from_dict(raw)


def _next_event_id(state: dict[str, Any], event_type: str) -> str:
    events = state.setdefault("events", {})
    return f"evt-{len(events) + 1:06d}-{slugify(event_type)}"


def _append_event(
    state: dict[str, Any],
    *,
    run_id: str,
    event_type: str,
    payload_summary: str = "",
    source: str = "project_runtime",
) -> EventRecord:
    event = EventRecord(
        event_id=_next_event_id(state, event_type),
        run_id=run_id,
        event_type=event_type,
        timestamp=utc_now_iso(),
        source=source,
        payload_summary=payload_summary.strip(),
    )
    state.setdefault("events", {})[event.event_id] = event_to_dict(event)
    return event


def _put_run(run: ProjectRun) -> ProjectRun:
    state = load_state()
    state.setdefault("runs", {})[run.run_id] = run_to_dict(run)
    save_state(state)
    return run


def _put_run_and_record_event(
    run: ProjectRun,
    *,
    event_type: str,
    payload_summary: str = "",
) -> ProjectRun:
    state = load_state()
    state.setdefault("runs", {})[run.run_id] = run_to_dict(run)
    _append_event(
        state,
        run_id=run.run_id,
        event_type=event_type,
        payload_summary=payload_summary,
    )
    save_state(state)
    return run


def list_events(run_id: str) -> list[EventRecord]:
    get_run(run_id)
    events = [
        event_from_dict(raw)
        for raw in load_state().get("events", {}).values()
        if isinstance(raw, dict) and raw.get("run_id") == run_id
    ]
    return sorted(events, key=lambda event: (event.timestamp, event.event_id))


def create_run(
    *,
    project: str,
    objective: str,
    run_id: str = "",
    work_items: list[str] | tuple[str, ...] = (),
    checkpoint: str = "",
    next_action: str = "",
    status: str = "sleeping",
) -> ProjectRun:
    project = project.strip()
    objective = objective.strip()
    if not project:
        raise ValueError("project is required")
    if not objective:
        raise ValueError("objective is required")
    final_run_id = run_id.strip() or f"run-{slugify(project)}-{slugify(objective)}"
    if final_run_id in load_state().get("runs", {}):
        raise ValueError(f"Project Run already exists: {final_run_id}")
    now = utc_now_iso()
    run = ProjectRun(
        run_id=final_run_id,
        project=project,
        objective=objective,
        work_items=tuple(
            WorkItem(title=item.strip()) for item in work_items if item.strip()
        ),
        status=normalize_status(status),
        checkpoint=checkpoint.strip(),
        next_action=next_action.strip(),
        created_at=now,
        updated_at=now,
    )
    return _put_run_and_record_event(
        append_journal(run, "created", "Project Run created"),
        event_type="run_created",
        payload_summary="Project Run created",
    )


def checkpoint_run(
    run_id: str,
    *,
    checkpoint: str,
    next_action: str = "",
    status: str | None = None,
) -> ProjectRun:
    run = get_run(run_id)
    updated = replace(
        run,
        checkpoint=checkpoint.strip(),
        next_action=next_action.strip() or run.next_action,
        status=normalize_status(status) if status else run.status,
        updated_at=utc_now_iso(),
    )
    detail = checkpoint.strip()
    return _put_run_and_record_event(
        append_journal(updated, "checkpoint", detail),
        event_type="checkpoint_saved",
        payload_summary=detail,
    )


def resume_run(run_id: str) -> ProjectRun:
    run = get_run(run_id)
    now = utc_now_iso()
    updated = replace(run, status="running", resumed_at=now, updated_at=now)
    return _put_run_and_record_event(
        append_journal(updated, "resumed", "Project Run resumed"),
        event_type="project_run_resumed",
        payload_summary="Project Run resumed",
    )


def complete_run(run_id: str, detail: str = "") -> ProjectRun:
    run = get_run(run_id)
    now = utc_now_iso()
    final_detail = detail.strip()
    updated = replace(run, status="completed", completed_at=now, updated_at=now)
    return _put_run_and_record_event(
        append_journal(updated, "completed", final_detail),
        event_type="project_run_completed",
        payload_summary=final_detail or "Project Run completed",
    )
