"""Persistent Project Run store for the Project OS runtime primitive."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
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
class EventType:
    name: str
    category: str
    description: str


@dataclass(frozen=True, slots=True)
class EventRecord:
    event_id: str
    run_id: str
    event_type: str
    timestamp: str
    source: str
    payload_summary: str = ""
    parent_event_id: str = ""


@dataclass(frozen=True, slots=True)
class AuthorityGrant:
    grant_id: str
    subject_identity: str
    allowed_action_scope: str
    allowed_capability_scope: str
    boundary: str
    issuer: str
    issued_at: str
    expires_at: str = ""
    revoked_at: str = ""
    project_id: str = ""
    run_id: str = ""
    reason: str = ""
    precedent_id: str = ""


EVENT_TYPE_CATALOG = (
    EventType("run_created", "lifecycle", "A Project Run was created"),
    EventType("checkpoint_saved", "lifecycle", "A Project Run checkpoint was saved"),
    EventType("project_run_resumed", "lifecycle", "A Project Run was resumed"),
    EventType("project_run_slept", "lifecycle", "A Project Run was put to sleep"),
    EventType("project_run_completed", "lifecycle", "A Project Run completed"),
    EventType("work_item_completed", "work", "A work item completed"),
    EventType("objective_changed", "work", "A Project Run objective changed"),
    EventType("artifact_created", "work", "A related artifact was created"),
    EventType("approval_requested", "governance", "Operator approval was requested"),
    EventType("approval_granted", "governance", "Operator approval was granted"),
    EventType(
        "authority_grant_created",
        "governance",
        "AuthorityGrant evidence was created",
    ),
    EventType("run_blocked", "blocking", "A Project Run became blocked"),
    EventType("run_unblocked", "blocking", "A Project Run was unblocked"),
)

_EVENT_TYPES_BY_NAME = {
    event_type.name: event_type for event_type in EVENT_TYPE_CATALOG
}


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


def normalize_event_type(event_type: str) -> str:
    normalized = event_type.strip().lower().replace("-", "_")
    if normalized not in _EVENT_TYPES_BY_NAME:
        allowed = ", ".join(sorted(_EVENT_TYPES_BY_NAME))
        raise ValueError(f"unknown event type {event_type!r}; allowed: {allowed}")
    return normalized


def list_event_types() -> tuple[EventType, ...]:
    return EVENT_TYPE_CATALOG


def empty_state() -> dict[str, Any]:
    return {"version": 1, "runs": {}, "events": {}, "authority_grants": {}}


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
    if not isinstance(state.get("authority_grants"), dict):
        state["authority_grants"] = {}
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
    raw_event_type = str(raw.get("event_type") or "")
    try:
        event_type = normalize_event_type(raw_event_type)
    except ValueError:
        event_type = raw_event_type
    return EventRecord(
        event_id=str(raw.get("event_id") or ""),
        run_id=str(raw.get("run_id") or ""),
        event_type=event_type,
        timestamp=str(raw.get("timestamp") or ""),
        source=str(raw.get("source") or ""),
        payload_summary=str(raw.get("payload_summary") or ""),
        parent_event_id=str(raw.get("parent_event_id") or ""),
    )


def event_to_dict(event: EventRecord) -> dict[str, Any]:
    return asdict(event)


def authority_grant_from_dict(raw: dict[str, Any]) -> AuthorityGrant:
    return AuthorityGrant(
        grant_id=str(raw.get("grant_id") or ""),
        subject_identity=str(raw.get("subject_identity") or ""),
        allowed_action_scope=str(raw.get("allowed_action_scope") or ""),
        allowed_capability_scope=str(raw.get("allowed_capability_scope") or ""),
        boundary=str(raw.get("boundary") or "project_run"),
        issuer=str(raw.get("issuer") or ""),
        issued_at=str(raw.get("issued_at") or ""),
        expires_at=str(raw.get("expires_at") or ""),
        revoked_at=str(raw.get("revoked_at") or ""),
        project_id=str(raw.get("project_id") or ""),
        run_id=str(raw.get("run_id") or ""),
        reason=str(raw.get("reason") or ""),
        precedent_id=str(raw.get("precedent_id") or ""),
    )


def authority_grant_to_dict(grant: AuthorityGrant) -> dict[str, Any]:
    return asdict(grant)


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


def create_authority_grant_record(
    record: Mapping[str, str],
) -> tuple[AuthorityGrant, EventRecord]:
    """Persist an AuthorityGrant record and its audit EventRecord."""
    grant = authority_grant_from_dict(dict(record))
    if not grant.grant_id:
        raise ValueError("grant_id is required")
    if not grant.run_id:
        raise ValueError("run_id is required")
    get_run(grant.run_id)
    state = load_state()
    grants = state.setdefault("authority_grants", {})
    if grant.grant_id in grants:
        raise ValueError(f"AuthorityGrant already exists: {grant.grant_id}")
    grants[grant.grant_id] = authority_grant_to_dict(grant)
    event = _append_event(
        state,
        run_id=grant.run_id,
        event_type="authority_grant_created",
        payload_summary=f"AuthorityGrant created: {grant.grant_id}",
    )
    save_state(state)
    return grant, event


def list_authority_grants(
    state: Mapping[str, Any] | None = None,
) -> tuple[AuthorityGrant, ...]:
    raw_state = state if state is not None else load_state()
    raw_grants = raw_state.get("authority_grants", {})
    if not isinstance(raw_grants, dict):
        return ()
    grants = tuple(
        authority_grant_from_dict(raw)
        for raw in raw_grants.values()
        if isinstance(raw, dict)
    )
    return tuple(sorted(grants, key=lambda grant: grant.grant_id))


def _next_event_id(state: dict[str, Any], event_type: str) -> str:
    events = state.setdefault("events", {})
    return f"evt-{len(events) + 1:06d}-{slugify(event_type)}"


def _require_parent_event(state: dict[str, Any], parent_event_id: str) -> str:
    parent = parent_event_id.strip()
    if parent and parent not in state.setdefault("events", {}):
        raise ValueError(f"parent Event Record not found: {parent}")
    return parent


def _append_event(
    state: dict[str, Any],
    *,
    run_id: str,
    event_type: str,
    payload_summary: str = "",
    source: str = "project_runtime",
    parent_event_id: str = "",
) -> EventRecord:
    normalized_event_type = normalize_event_type(event_type)
    parent = _require_parent_event(state, parent_event_id)
    event = EventRecord(
        event_id=_next_event_id(state, normalized_event_type),
        run_id=run_id,
        event_type=normalized_event_type,
        timestamp=utc_now_iso(),
        source=source.strip() or "project_runtime",
        payload_summary=payload_summary.strip(),
        parent_event_id=parent,
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
    parent_event_id: str = "",
) -> ProjectRun:
    state = load_state()
    state.setdefault("runs", {})[run.run_id] = run_to_dict(run)
    _append_event(
        state,
        run_id=run.run_id,
        event_type=event_type,
        payload_summary=payload_summary,
        parent_event_id=parent_event_id,
    )
    save_state(state)
    return run


def record_event(
    run_id: str,
    event_type: str,
    *,
    payload_summary: str = "",
    source: str = "project_runtime",
    parent_event_id: str = "",
) -> EventRecord:
    get_run(run_id)
    state = load_state()
    event = _append_event(
        state,
        run_id=run_id,
        event_type=event_type,
        payload_summary=payload_summary,
        source=source,
        parent_event_id=parent_event_id,
    )
    save_state(state)
    return event


def get_event(event_id: str) -> EventRecord:
    raw = load_state().get("events", {}).get(event_id)
    if not isinstance(raw, dict):
        raise KeyError(f"Event Record not found: {event_id}")
    return event_from_dict(raw)


def trace_event(event_id: str) -> list[EventRecord]:
    state = load_state()
    events = state.get("events", {})
    chain: list[EventRecord] = []
    seen: set[str] = set()
    current_id = event_id
    while current_id:
        if current_id in seen:
            raise ValueError(f"Event causality cycle detected at {current_id}")
        seen.add(current_id)
        raw = events.get(current_id)
        if not isinstance(raw, dict):
            raise KeyError(f"Event Record not found: {current_id}")
        event = event_from_dict(raw)
        chain.append(event)
        current_id = event.parent_event_id
    return list(reversed(chain))


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
