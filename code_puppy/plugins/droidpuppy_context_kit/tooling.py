"""Tooling for DroidPuppy's canonical workflow-context bundle."""

from __future__ import annotations

import copy
import json
from typing import Any

from .repo_governance import (
    droidpuppy_context_install_repo_governance as install_repo_governance_impl,
)
from .store import (
    append_jsonl,
    approval_decision_default,
    ensure_layout,
    execution_plan_default,
    intent_handshake_default,
    journal_default,
    load_bundle,
    load_governance,
    paths,
    read_jsonl_tail,
    save_bundle,
    save_governance,
    utc_now,
    workflow_commit_default,
    workflow_state_default,
)

_CANONICAL_OBJECTS = [
    "workflow_state",
    "execution_plan",
    "approval_decision",
    "journal",
]
_APPROVAL_READY = {"approved", "operator_confirmed", "lease_ready", "delegated"}


def _parse_json_object(text: str, *, field: str) -> tuple[dict[str, Any] | None, str]:
    if not text.strip():
        return {}, ""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"{field} is not valid JSON: {exc}"
    if not isinstance(payload, dict):
        return None, f"{field} must decode to a JSON object"
    return payload, ""


def _clean_list(values: list[str] | None) -> list[str]:
    cleaned: list[str] = []
    for value in values or []:
        text = str(value).strip()
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned


def _merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in patch.items():
        if key in {"schema_version", "workflow_id"}:
            continue
        merged[key] = value
    return merged


def _workflow_id_from_bundle(bundle: dict[str, dict[str, Any]]) -> str:
    for key in _CANONICAL_OBJECTS:
        workflow_id = str(bundle[key].get("workflow_id") or "").strip()
        if workflow_id:
            return workflow_id
    return "default-workflow"


def _workflow_id_from_governance(governance: dict[str, dict[str, Any]]) -> str:
    for key in ("intent_handshake", "workflow_commit"):
        workflow_id = str(governance[key].get("workflow_id") or "").strip()
        if workflow_id:
            return workflow_id
    return "default-workflow"


def _touch_governance(
    governance: dict[str, dict[str, Any]],
    *,
    workflow_id: str,
) -> dict[str, dict[str, Any]]:
    stamp = utc_now()
    for key in ("intent_handshake", "workflow_commit"):
        governance[key]["workflow_id"] = workflow_id
        governance[key]["updated_at"] = stamp
    return governance


def _commit_status(approval_status: str) -> str:
    return (
        "committed_ready"
        if approval_status.strip().lower() in _APPROVAL_READY
        else "committed_pending_approval"
    )


def _touch_bundle(
    bundle: dict[str, dict[str, Any]],
    *,
    workflow_id: str,
) -> dict[str, dict[str, Any]]:
    stamp = utc_now()
    for key in _CANONICAL_OBJECTS:
        bundle[key]["workflow_id"] = workflow_id
        bundle[key]["updated_at"] = stamp
    return bundle


def _append_event(root: str, payload: dict[str, Any]) -> dict[str, Any]:
    event = {
        "timestamp": utc_now(),
        "event_type": "workflow.context.recorded",
        "payload": payload,
    }
    append_jsonl(paths(root)["journal_events"], event)
    return event


def droidpuppy_context_doctor(root: str = "") -> dict[str, Any]:
    resolved = paths(root)
    bundle = load_bundle(root)
    governance = load_governance(root)
    return {
        "success": True,
        "root": str(resolved["root"]),
        "files": {key: str(path) for key, path in resolved.items() if key != "root"},
        "exists": {
            key: path.exists() for key, path in resolved.items() if key != "root"
        },
        "canonical_objects": list(_CANONICAL_OBJECTS),
        "authority_rule": "approval_decision is the only authoritative permission object.",
        "workflow_id": _workflow_id_from_bundle(bundle),
        "handshake_status": governance["intent_handshake"].get("status", "draft"),
        "commit_status": governance["workflow_commit"].get("status", "uncommitted"),
        "guidance": [
            "Initialize once with droidpuppy_context_init.",
            "Use droidpuppy_context_handshake to turn plain-English intent into a governed request packet.",
            "Use droidpuppy_context_record for plain-English who/what/when/why updates.",
            "Use droidpuppy_context_apply_packet when you already have structured JSON objects.",
            "Use droidpuppy_context_commit_workflow to freeze a workflow receipt before skill/tool graduation.",
            "Treat workflow_state, execution_plan, and journal as descriptive; only approval_decision authorizes.",
        ],
    }


def droidpuppy_context_init(
    root: str = "",
    workflow_id: str = "default-workflow",
    operator: str = "operator",
    authority: str = "operator",
    title: str = "",
    overwrite: bool = False,
) -> dict[str, Any]:
    ensure_layout(root)
    existing = load_bundle(
        root, workflow_id=workflow_id, operator=operator, authority=authority
    )
    existing_governance = load_governance(
        root, workflow_id=workflow_id, requester=operator
    )
    if overwrite:
        bundle = {
            "workflow_state": workflow_state_default(
                workflow_id=workflow_id, operator=operator
            ),
            "execution_plan": execution_plan_default(workflow_id=workflow_id),
            "approval_decision": approval_decision_default(
                workflow_id=workflow_id, authority=authority
            ),
            "journal": journal_default(workflow_id=workflow_id),
        }
        governance = {
            "intent_handshake": intent_handshake_default(
                workflow_id=workflow_id, requester=operator
            ),
            "workflow_commit": workflow_commit_default(workflow_id=workflow_id),
        }
    else:
        bundle = existing
        governance = existing_governance
    if title.strip():
        bundle["workflow_state"]["title"] = title.strip()
    bundle = _touch_bundle(bundle, workflow_id=workflow_id)
    governance = _touch_governance(governance, workflow_id=workflow_id)
    save_bundle(root, bundle)
    save_governance(root, governance)
    event = _append_event(
        root,
        {
            "workflow_id": workflow_id,
            "actor": operator,
            "what": "workflow initialized",
            "why": "establish canonical context objects",
            "result": "ready",
        },
    )
    return {
        "success": True,
        "workflow_id": workflow_id,
        "event": event,
        "packet": bundle,
        "intent_handshake": governance["intent_handshake"],
        "workflow_commit": governance["workflow_commit"],
    }


def droidpuppy_context_record(
    what: str,
    why: str,
    result: str,
    root: str = "",
    actor: str = "operator",
    workflow_id: str = "",
    workflow_status: str = "",
    current_goal: str = "",
    current_step: str = "",
    next_steps: list[str] | None = None,
    blockers: list[str] | None = None,
    evidence_refs: list[str] | None = None,
    approved_actions: list[str] | None = None,
    blocked_actions: list[str] | None = None,
    approval_status: str = "",
    authority: str = "operator",
) -> dict[str, Any]:
    if not str(what).strip():
        return {"success": False, "reason": "what is required"}
    if not str(why).strip():
        return {"success": False, "reason": "why is required"}
    if not str(result).strip():
        return {"success": False, "reason": "result is required"}

    bundle = load_bundle(
        root,
        workflow_id=workflow_id or "default-workflow",
        operator=actor,
        authority=authority,
    )
    resolved_workflow_id = workflow_id.strip() or _workflow_id_from_bundle(bundle)
    del approved_actions, blocked_actions, approval_status
    evidence = _clean_list(evidence_refs)
    state_patch: dict[str, Any] = {
        "summary": str(what).strip(),
        "last_actor": actor,
    }
    if workflow_status.strip():
        state_patch["status"] = workflow_status.strip()
    if current_goal.strip():
        state_patch["current_goal"] = str(current_goal).strip()
    if current_step.strip():
        state_patch["current_step"] = str(current_step).strip()
    if blockers is not None:
        state_patch["blockers"] = _clean_list(blockers)
    if evidence_refs is not None:
        state_patch["evidence_refs"] = evidence
    bundle["workflow_state"] = _merge(bundle["workflow_state"], state_patch)

    plan_patch: dict[str, Any] = {}
    cleaned_next_steps = _clean_list(next_steps)
    if next_steps is not None:
        plan_patch["next_steps"] = cleaned_next_steps
        if cleaned_next_steps:
            plan_patch["status"] = "ready"
    if blockers is not None:
        plan_patch["dependencies"] = _clean_list(blockers)
    if plan_patch:
        bundle["execution_plan"] = _merge(bundle["execution_plan"], plan_patch)

    entry = {
        "timestamp": utc_now(),
        "actor": actor,
        "what": str(what).strip(),
        "why": str(why).strip(),
        "result": str(result).strip(),
        "evidence_refs": evidence,
        "next_steps": _clean_list(next_steps),
    }
    entries = list(bundle["journal"].get("entries") or [])
    entries.append(entry)
    bundle["journal"] = _merge(
        bundle["journal"],
        {
            "latest_summary": entry["what"],
            "latest_result": entry["result"],
            "latest_why": entry["why"],
            "entries": entries[-25:],
        },
    )
    bundle = _touch_bundle(bundle, workflow_id=resolved_workflow_id)
    save_bundle(root, bundle)
    event = _append_event(root, {"workflow_id": resolved_workflow_id, **entry})
    return {
        "success": True,
        "workflow_id": resolved_workflow_id,
        "event": event,
        "authority_rule": "approval_decision is the only authoritative permission object.",
        "packet": bundle,
    }


def droidpuppy_context_packet(
    root: str = "", history_limit: int = 10
) -> dict[str, Any]:
    bundle = load_bundle(root)
    governance = load_governance(root)
    resolved = paths(root)
    return {
        "success": True,
        "workflow_id": _workflow_id_from_bundle(bundle),
        "authority_rule": "approval_decision is the only authoritative permission object.",
        "packet": bundle,
        "intent_handshake": governance["intent_handshake"],
        "workflow_commit": governance["workflow_commit"],
        "journal_event_tail": read_jsonl_tail(
            resolved["journal_events"], limit=history_limit
        ),
    }


def droidpuppy_context_append_journal(
    what: str,
    why: str,
    result: str,
    root: str = "",
    actor: str = "operator",
    workflow_id: str = "",
    evidence_refs: list[str] | None = None,
    next_steps: list[str] | None = None,
) -> dict[str, Any]:
    if not str(what).strip():
        return {"success": False, "reason": "what is required"}
    if not str(why).strip():
        return {"success": False, "reason": "why is required"}
    if not str(result).strip():
        return {"success": False, "reason": "result is required"}

    bundle = load_bundle(
        root, workflow_id=workflow_id or "default-workflow", operator=actor
    )
    resolved_workflow_id = workflow_id.strip() or _workflow_id_from_bundle(bundle)
    entry = {
        "timestamp": utc_now(),
        "actor": actor,
        "what": str(what).strip(),
        "why": str(why).strip(),
        "result": str(result).strip(),
        "evidence_refs": _clean_list(evidence_refs),
        "next_steps": _clean_list(next_steps),
    }
    entries = list(bundle["journal"].get("entries") or [])
    entries.append(entry)
    bundle["journal"] = _merge(
        bundle["journal"],
        {
            "latest_summary": entry["what"],
            "latest_result": entry["result"],
            "latest_why": entry["why"],
            "entries": entries[-50:],
        },
    )
    bundle = _touch_bundle(bundle, workflow_id=resolved_workflow_id)
    save_bundle(root, bundle)
    event = {
        "timestamp": utc_now(),
        "event_type": "workflow.journaled",
        "payload": {"workflow_id": resolved_workflow_id, **entry},
    }
    append_jsonl(paths(root)["journal_events"], event)
    return {
        "success": True,
        "workflow_id": resolved_workflow_id,
        "event": event,
        "packet": bundle,
    }


def droidpuppy_context_handshake(
    raw_request: str,
    root: str = "",
    workflow_id: str = "",
    requester: str = "operator",
    intent_summary: str = "",
    requested_capabilities: list[str] | None = None,
    constraints: list[str] | None = None,
    target_surface: str = "",
    risk_tier: str = "review_required",
) -> dict[str, Any]:
    if not str(raw_request).strip():
        return {"success": False, "reason": "raw_request is required"}

    bundle = load_bundle(root, workflow_id=workflow_id or "default-workflow")
    governance = load_governance(
        root,
        workflow_id=workflow_id or _workflow_id_from_bundle(bundle),
        requester=requester,
    )
    resolved_workflow_id = (
        workflow_id.strip()
        or _workflow_id_from_bundle(bundle)
        or _workflow_id_from_governance(governance)
    )
    handshake = governance["intent_handshake"]
    handshake.update(
        {
            "workflow_id": resolved_workflow_id,
            "status": "handshake_recorded",
            "requester": requester,
            "raw_request": str(raw_request).strip(),
            "intent_summary": str(intent_summary).strip()
            or str(raw_request).strip()[:240],
            "requested_capabilities": _clean_list(requested_capabilities),
            "constraints": _clean_list(constraints),
            "target_surface": str(target_surface).strip(),
            "risk_tier": str(risk_tier).strip() or "review_required",
        }
    )
    governance = _touch_governance(governance, workflow_id=resolved_workflow_id)
    save_governance(root, governance)
    event = _append_event(
        root,
        {
            "workflow_id": resolved_workflow_id,
            "actor": requester,
            "what": "intent handshake recorded",
            "why": handshake["intent_summary"],
            "result": handshake["status"],
        },
    )
    return {
        "success": True,
        "workflow_id": resolved_workflow_id,
        "event": event,
        "intent_handshake": governance["intent_handshake"],
        "workflow_commit": governance["workflow_commit"],
        "authority_rule": "approval_decision is still the only authoritative permission object.",
    }


def droidpuppy_context_commit_workflow(
    root: str = "",
    workflow_id: str = "",
    committed_by: str = "operator",
    commit_message: str = "",
) -> dict[str, Any]:
    bundle = load_bundle(root, workflow_id=workflow_id or "default-workflow")
    governance = load_governance(root, workflow_id=workflow_id or "default-workflow")
    resolved_workflow_id = (
        workflow_id.strip()
        or _workflow_id_from_bundle(bundle)
        or _workflow_id_from_governance(governance)
    )
    handshake = governance["intent_handshake"]
    approval = bundle["approval_decision"]
    plan = bundle["execution_plan"]
    state = bundle["workflow_state"]
    if not str(handshake.get("raw_request") or "").strip():
        return {
            "success": False,
            "reason": "intent handshake is required before commit",
        }
    if not (
        plan.get("next_steps") or state.get("current_goal") or state.get("summary")
    ):
        return {
            "success": False,
            "reason": "workflow needs at least a goal or next step before commit",
        }

    approval_status = str(approval.get("status") or "review_required")
    commit_status = _commit_status(approval_status)
    commit_token = f"{resolved_workflow_id}:{utc_now()}"
    commit = governance["workflow_commit"]
    commit.update(
        {
            "workflow_id": resolved_workflow_id,
            "status": commit_status,
            "commit_token": commit_token,
            "commit_summary": str(
                state.get("summary")
                or handshake.get("intent_summary")
                or resolved_workflow_id
            ),
            "commit_message": str(commit_message).strip()
            or str(handshake.get("intent_summary") or ""),
            "handshake_status": str(handshake.get("status") or "draft"),
            "approval_status": approval_status,
            "allowed_actions_snapshot": _clean_list(approval.get("allowed_actions")),
            "blocked_actions_snapshot": _clean_list(approval.get("blocked_actions")),
            "evidence_refs": _clean_list(approval.get("evidence_refs"))
            + _clean_list(state.get("evidence_refs")),
            "committed_at": utc_now(),
            "committed_by": committed_by,
        }
    )
    governance = _touch_governance(governance, workflow_id=resolved_workflow_id)
    save_governance(root, governance)
    event = _append_event(
        root,
        {
            "workflow_id": resolved_workflow_id,
            "actor": committed_by,
            "what": "workflow committed",
            "why": commit.get("commit_message") or "governed workflow commit",
            "result": commit_status,
        },
    )
    return {
        "success": True,
        "workflow_id": resolved_workflow_id,
        "event": event,
        "intent_handshake": governance["intent_handshake"],
        "workflow_commit": governance["workflow_commit"],
        "packet": bundle,
        "authority_rule": "workflow commits freeze intent and approval state; only approval_decision authorizes action.",
    }


def droidpuppy_context_install_repo_governance(
    target_root: str = "",
    overwrite: bool = False,
    include_readme: bool = True,
) -> dict[str, Any]:
    return install_repo_governance_impl(
        target_root=target_root,
        overwrite=overwrite,
        include_readme=include_readme,
    )


def droidpuppy_context_apply_packet(
    root: str = "",
    workflow_state_json: str = "",
    execution_plan_json: str = "",
    approval_decision_json: str = "",
    journal_json: str = "",
) -> dict[str, Any]:
    patches: dict[str, dict[str, Any]] = {}
    for key, raw in (
        ("workflow_state", workflow_state_json),
        ("execution_plan", execution_plan_json),
        ("approval_decision", approval_decision_json),
        ("journal", journal_json),
    ):
        patch, error = _parse_json_object(raw, field=f"{key}_json")
        if error or patch is None:
            return {"success": False, "reason": error}
        if patch:
            patches[key] = patch

    bundle = load_bundle(root)
    for key, patch in patches.items():
        bundle[key] = _merge(bundle[key], patch)

    resolved_workflow_id = _workflow_id_from_bundle(bundle)
    bundle = _touch_bundle(bundle, workflow_id=resolved_workflow_id)
    save_bundle(root, bundle)
    event = _append_event(
        root,
        {
            "workflow_id": resolved_workflow_id,
            "actor": "packet",
            "what": "canonical packet applied",
            "why": "structured context update",
            "result": f"updated {', '.join(sorted(patches)) or 'nothing'}",
        },
    )
    return {
        "success": True,
        "workflow_id": resolved_workflow_id,
        "updated_objects": sorted(patches),
        "event": event,
        "packet": bundle,
    }
