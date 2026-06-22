"""Durable storage for DroidPuppy's governed workflow-context objects."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

WORKFLOW_STATE_SCHEMA = "droidpuppy.workflow_state.v1"
EXECUTION_PLAN_SCHEMA = "droidpuppy.execution_plan.v1"
APPROVAL_DECISION_SCHEMA = "droidpuppy.approval_decision.v1"
JOURNAL_SCHEMA = "droidpuppy.journal.v1"
INTENT_HANDSHAKE_SCHEMA = "droidpuppy.intent_handshake.v1"
WORKFLOW_COMMIT_SCHEMA = "droidpuppy.workflow_commit.v1"
DEFAULT_ROOT = Path.home() / ".project_os" / "droidpuppy_context"


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def resolve_root(root: str = "") -> Path:
    return Path(root).expanduser().resolve() if root.strip() else DEFAULT_ROOT


def paths(root: str = "") -> dict[str, Path]:
    base = resolve_root(root)
    return {
        "root": base,
        "workflow_state": base / "workflow_state.json",
        "execution_plan": base / "execution_plan.json",
        "approval_decision": base / "approval_decision.json",
        "journal": base / "journal.json",
        "intent_handshake": base / "intent_handshake.json",
        "workflow_commit": base / "workflow_commit.json",
        "journal_events": base / "journal_events.jsonl",
    }


def ensure_layout(root: str = "") -> dict[str, Path]:
    resolved = paths(root)
    resolved["root"].mkdir(parents=True, exist_ok=True)
    return resolved


def read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return dict(default)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return dict(default)
    return payload if isinstance(payload, dict) else dict(default)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def read_jsonl_tail(path: Path, limit: int = 20) -> list[dict[str, Any]]:
    if not path.exists() or limit <= 0:
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines()[-limit:]:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            events.append(payload)
    return events


def workflow_state_default(
    workflow_id: str = "default-workflow",
    operator: str = "operator",
) -> dict[str, Any]:
    return {
        "schema_version": WORKFLOW_STATE_SCHEMA,
        "workflow_id": workflow_id,
        "title": workflow_id,
        "status": "active",
        "summary": "",
        "current_goal": "",
        "current_step": "",
        "blockers": [],
        "facts": [],
        "evidence_refs": [],
        "last_actor": operator,
        "updated_at": utc_now(),
    }


def execution_plan_default(workflow_id: str = "default-workflow") -> dict[str, Any]:
    return {
        "schema_version": EXECUTION_PLAN_SCHEMA,
        "workflow_id": workflow_id,
        "status": "draft",
        "next_steps": [],
        "stop_conditions": [],
        "assumptions": [],
        "dependencies": [],
        "updated_at": utc_now(),
    }


def approval_decision_default(
    workflow_id: str = "default-workflow",
    authority: str = "operator",
) -> dict[str, Any]:
    return {
        "schema_version": APPROVAL_DECISION_SCHEMA,
        "workflow_id": workflow_id,
        "authority": authority,
        "status": "review_required",
        "allowed_actions": [],
        "blocked_actions": [],
        "rationale": "",
        "evidence_refs": [],
        "updated_at": utc_now(),
    }


def journal_default(workflow_id: str = "default-workflow") -> dict[str, Any]:
    return {
        "schema_version": JOURNAL_SCHEMA,
        "workflow_id": workflow_id,
        "latest_summary": "",
        "latest_result": "",
        "latest_why": "",
        "entries": [],
        "updated_at": utc_now(),
    }


def intent_handshake_default(
    workflow_id: str = "default-workflow",
    requester: str = "operator",
) -> dict[str, Any]:
    return {
        "schema_version": INTENT_HANDSHAKE_SCHEMA,
        "workflow_id": workflow_id,
        "status": "draft",
        "requester": requester,
        "raw_request": "",
        "intent_summary": "",
        "requested_capabilities": [],
        "constraints": [],
        "target_surface": "",
        "risk_tier": "review_required",
        "updated_at": utc_now(),
    }


def workflow_commit_default(
    workflow_id: str = "default-workflow",
) -> dict[str, Any]:
    return {
        "schema_version": WORKFLOW_COMMIT_SCHEMA,
        "workflow_id": workflow_id,
        "status": "uncommitted",
        "commit_token": "",
        "commit_summary": "",
        "commit_message": "",
        "handshake_status": "draft",
        "approval_status": "review_required",
        "allowed_actions_snapshot": [],
        "blocked_actions_snapshot": [],
        "evidence_refs": [],
        "committed_at": "",
        "committed_by": "",
        "updated_at": utc_now(),
    }


def load_bundle(
    root: str = "",
    workflow_id: str = "default-workflow",
    operator: str = "operator",
    authority: str = "operator",
) -> dict[str, dict[str, Any]]:
    resolved = paths(root)
    return {
        "workflow_state": read_json(
            resolved["workflow_state"],
            workflow_state_default(workflow_id=workflow_id, operator=operator),
        ),
        "execution_plan": read_json(
            resolved["execution_plan"],
            execution_plan_default(workflow_id=workflow_id),
        ),
        "approval_decision": read_json(
            resolved["approval_decision"],
            approval_decision_default(workflow_id=workflow_id, authority=authority),
        ),
        "journal": read_json(
            resolved["journal"],
            journal_default(workflow_id=workflow_id),
        ),
    }


def load_governance(
    root: str = "",
    workflow_id: str = "default-workflow",
    requester: str = "operator",
) -> dict[str, dict[str, Any]]:
    resolved = paths(root)
    return {
        "intent_handshake": read_json(
            resolved["intent_handshake"],
            intent_handshake_default(workflow_id=workflow_id, requester=requester),
        ),
        "workflow_commit": read_json(
            resolved["workflow_commit"],
            workflow_commit_default(workflow_id=workflow_id),
        ),
    }


def save_bundle(root: str, bundle: dict[str, dict[str, Any]]) -> None:
    resolved = ensure_layout(root)
    for key in (
        "workflow_state",
        "execution_plan",
        "approval_decision",
        "journal",
    ):
        write_json(resolved[key], bundle[key])


def save_governance(root: str, governance: dict[str, dict[str, Any]]) -> None:
    resolved = ensure_layout(root)
    for key in ("intent_handshake", "workflow_commit"):
        write_json(resolved[key], governance[key])
