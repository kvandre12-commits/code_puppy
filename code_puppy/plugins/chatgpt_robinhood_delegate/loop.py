"""Two-phase loop helpers for ChatGPT Robinhood delegation flows."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from pydantic import BaseModel, Field

from .audit import ingest_connector_audit
from .tooling import (
    DEFAULT_BRIDGE_HANDOFF_NAME,
    DEFAULT_BRIDGE_REPO_ROOT,
    DEFAULT_BRIDGE_TIMEOUT_SECONDS,
    DEFAULT_OUTPUT_DIR,
    _sanitize_artifact_name,
    _utc_now,
    prepare_delegation_from_bridge_handoff,
    prepare_delegation_from_signal,
)

DEFAULT_LOOP_ARTIFACT_NAME = "chatgpt_robinhood_loop"
LOOP_STATE_SCHEMA = "sharpedge.chatgpt_robinhood_loop.v1"


class ChatGPTRobinhoodLoopOutput(BaseModel):
    """Tool output for the delegation loop helper."""

    status: str
    phase: str
    loop_id: str
    loop_json_path: str
    delegation_json_path: str = ""
    delegation_text_path: str = ""
    source_handoff_path: str = ""
    audit_json_path: str = ""
    journal_json_path: str = ""
    journal_markdown_path: str = ""
    next_step: str = ""
    warnings: list[str] = Field(default_factory=list)


def _output_root(
    *, output_dir: str = DEFAULT_OUTPUT_DIR, base_dir: Path | None = None
) -> Path:
    root = Path(base_dir) if base_dir is not None else Path.cwd()
    output_path = root / output_dir
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path


def _loop_paths(
    *,
    artifact_name: str = DEFAULT_LOOP_ARTIFACT_NAME,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    base_dir: Path | None = None,
) -> dict[str, Path]:
    safe_name = _sanitize_artifact_name(artifact_name)
    output_root = _output_root(output_dir=output_dir, base_dir=base_dir)
    return {
        "safe_name": safe_name,
        "loop_json": output_root / f"{safe_name}_loop.json",
        "delegation_json": output_root / f"{safe_name}_delegation.json",
        "delegation_text": output_root / f"{safe_name}_delegation.txt",
        "audit_json": output_root / f"{safe_name}_audit.json",
        "audit_journal_json": output_root / f"{safe_name}_audit_journal_stub.json",
        "audit_journal_md": output_root / f"{safe_name}_audit_journal_stub.md",
    }


def _write_loop_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def _load_loop_state(loop_json_path: str | Path) -> tuple[Path, dict]:
    path = Path(loop_json_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Loop state file not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Loop state file is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema") != LOOP_STATE_SCHEMA:
        raise ValueError(
            f"Unsupported loop state schema '{payload.get('schema') if isinstance(payload, dict) else '<invalid>'}'."
        )
    return path, payload


def _finalize_instruction(loop_json_path: Path) -> str:
    return (
        "After the ChatGPT Robinhood connector responds, call "
        "chatgpt_robinhood_loop(action='finish', loop_json_path='"
        f"{loop_json_path}'"
        ", response_text='...' or response_json='...') to ingest the result."
    )


def start_delegation_loop(
    *,
    artifact_name: str = DEFAULT_LOOP_ARTIFACT_NAME,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    base_dir: Path | None = None,
    handoff_path: str = "",
    bridge_root: str = DEFAULT_BRIDGE_REPO_ROOT,
    signal_path: str = "",
    bridge_command_name: str = "order_submit",
    test: bool = False,
    handoff_output_dir: str = "",
    handoff_latest_name: str = DEFAULT_BRIDGE_HANDOFF_NAME,
    bridge_timeout_seconds: int = DEFAULT_BRIDGE_TIMEOUT_SECONDS,
    required_result: str = "",
    objective: str = "",
    supporting_context: str = "",
    constraints: str = "",
    risk_notes: str = "",
) -> ChatGPTRobinhoodLoopOutput:
    """Start a bridge -> delegation loop and persist a loop state manifest."""
    paths = _loop_paths(
        artifact_name=artifact_name,
        output_dir=output_dir,
        base_dir=base_dir,
    )
    safe_name = str(paths["safe_name"])
    delegation_artifact = f"{safe_name}_delegation"
    audit_artifact = f"{safe_name}_audit"

    if (handoff_path or "").strip():
        delegation = prepare_delegation_from_bridge_handoff(
            handoff_path=handoff_path,
            artifact_name=delegation_artifact,
            output_dir=output_dir,
            base_dir=base_dir,
            required_result=required_result,
            objective=objective,
            supporting_context=supporting_context,
            constraints=constraints,
            risk_notes=risk_notes,
        )
        source_mode = "handoff"
    else:
        delegation = prepare_delegation_from_signal(
            bridge_root=bridge_root,
            signal_path=signal_path,
            bridge_command_name=bridge_command_name,
            test=test,
            handoff_output_dir=handoff_output_dir,
            handoff_latest_name=handoff_latest_name,
            bridge_timeout_seconds=bridge_timeout_seconds,
            artifact_name=delegation_artifact,
            output_dir=output_dir,
            base_dir=base_dir,
            required_result=required_result,
            objective=objective,
            supporting_context=supporting_context,
            constraints=constraints,
            risk_notes=risk_notes,
        )
        source_mode = "signal"

    loop_id = f"{safe_name}-{uuid.uuid4().hex[:10]}"
    loop_state = {
        "schema": LOOP_STATE_SCHEMA,
        "loop_id": loop_id,
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
        "status": "awaiting_connector_response",
        "phase": "prepared",
        "artifact_name": safe_name,
        "output_dir": output_dir,
        "base_dir": str(Path(base_dir) if base_dir is not None else Path.cwd()),
        "source": {
            "mode": source_mode,
            "signal_path": str(signal_path or ""),
            "bridge_root": str(bridge_root or ""),
            "bridge_command_name": str(bridge_command_name or ""),
            "test": bool(test),
            "source_handoff_path": str(delegation.source_handoff_path or ""),
        },
        "delegation": {
            "task_type": delegation.task_type,
            "objective": delegation.objective,
            "approval_policy": delegation.approval_policy,
            "handoff_json_path": delegation.handoff_json_path,
            "handoff_text_path": delegation.handoff_text_path,
            "warnings": delegation.warnings,
        },
        "audit": {
            "artifact_name": audit_artifact,
            "expected_json_path": str(paths["audit_json"]),
            "expected_journal_json_path": str(paths["audit_journal_json"]),
            "expected_journal_markdown_path": str(paths["audit_journal_md"]),
        },
        "completion": {
            "audit_json_path": "",
            "journal_json_path": "",
            "journal_markdown_path": "",
            "connector_status": "",
            "fill_status": "",
        },
        "recommended_next_step": _finalize_instruction(paths["loop_json"]),
    }
    _write_loop_state(paths["loop_json"], loop_state)

    return ChatGPTRobinhoodLoopOutput(
        status="prepared",
        phase="prepared",
        loop_id=loop_id,
        loop_json_path=str(paths["loop_json"]),
        delegation_json_path=delegation.handoff_json_path,
        delegation_text_path=delegation.handoff_text_path,
        source_handoff_path=delegation.source_handoff_path,
        next_step=loop_state["recommended_next_step"],
        warnings=delegation.warnings,
    )


def finish_delegation_loop(
    *,
    loop_json_path: str,
    response_text: str = "",
    response_json: str = "",
    response_file_path: str = "",
    append_log: bool = True,
) -> ChatGPTRobinhoodLoopOutput:
    """Close a prepared loop by ingesting the connector response."""
    loop_path, loop_state = _load_loop_state(loop_json_path)
    audit = ingest_connector_audit(
        response_text=response_text,
        response_json=response_json,
        response_file_path=response_file_path,
        handoff_path=str(
            (loop_state.get("source") or {}).get("source_handoff_path") or ""
        ),
        artifact_name=str((loop_state.get("audit") or {}).get("artifact_name") or ""),
        output_dir=str(loop_state.get("output_dir") or DEFAULT_OUTPUT_DIR),
        base_dir=Path(str(loop_state.get("base_dir") or loop_path.parent.parent)),
        append_log=append_log,
    )
    loop_state["updated_at"] = _utc_now()
    loop_state["status"] = "completed"
    loop_state["phase"] = "completed"
    loop_state["completion"] = {
        "audit_json_path": audit.audit_json_path,
        "journal_json_path": audit.journal_json_path,
        "journal_markdown_path": audit.journal_markdown_path,
        "connector_status": audit.connector_status,
        "fill_status": audit.fill_status,
        "source_response_path": audit.source_response_path,
    }
    loop_state["recommended_next_step"] = (
        "Optional but smart: rerun the SharpEdge operator surfaces so the latest connector audit "
        "shows up in operator_brief, operator_session_review, and Android packet exports."
    )
    _write_loop_state(loop_path, loop_state)

    return ChatGPTRobinhoodLoopOutput(
        status="completed",
        phase="completed",
        loop_id=str(loop_state.get("loop_id") or ""),
        loop_json_path=str(loop_path),
        delegation_json_path=str(
            (loop_state.get("delegation") or {}).get("handoff_json_path") or ""
        ),
        delegation_text_path=str(
            (loop_state.get("delegation") or {}).get("handoff_text_path") or ""
        ),
        source_handoff_path=str(
            (loop_state.get("source") or {}).get("source_handoff_path") or ""
        ),
        audit_json_path=audit.audit_json_path,
        journal_json_path=audit.journal_json_path,
        journal_markdown_path=audit.journal_markdown_path,
        next_step=str(loop_state.get("recommended_next_step") or ""),
        warnings=audit.warnings,
    )


def get_delegation_loop_status(*, loop_json_path: str) -> ChatGPTRobinhoodLoopOutput:
    """Read a loop state manifest without mutating it."""
    loop_path, loop_state = _load_loop_state(loop_json_path)
    completion = loop_state.get("completion") or {}
    delegation = loop_state.get("delegation") or {}
    source = loop_state.get("source") or {}
    return ChatGPTRobinhoodLoopOutput(
        status=str(loop_state.get("status") or "unknown"),
        phase=str(loop_state.get("phase") or "unknown"),
        loop_id=str(loop_state.get("loop_id") or ""),
        loop_json_path=str(loop_path),
        delegation_json_path=str(delegation.get("handoff_json_path") or ""),
        delegation_text_path=str(delegation.get("handoff_text_path") or ""),
        source_handoff_path=str(source.get("source_handoff_path") or ""),
        audit_json_path=str(completion.get("audit_json_path") or ""),
        journal_json_path=str(completion.get("journal_json_path") or ""),
        journal_markdown_path=str(completion.get("journal_markdown_path") or ""),
        next_step=str(loop_state.get("recommended_next_step") or ""),
        warnings=list(delegation.get("warnings") or []),
    )
