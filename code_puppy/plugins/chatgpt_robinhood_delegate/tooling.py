"""Helpers for delegating Robinhood requests through ChatGPT.

This plugin is intentionally honest: Code Puppy's current ChatGPT OAuth path
speaks to the Codex backend as a model provider, not to ChatGPT's connector
surface. So the safe v1 is a structured handoff artifact that another system
(or a human in the ChatGPT UI) can execute using an already-authenticated
Robinhood connector.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .prompt_contracts import render_payload_contracts_section

DEFAULT_ARTIFACT_NAME = "chatgpt_robinhood_delegation"
DEFAULT_BRIDGE_ARTIFACT_NAME = "chatgpt_robinhood_from_bridge"
DEFAULT_BRIDGE_REPO_ROOT = "~/SharpEdge-Robinhood-Bridge"
DEFAULT_BRIDGE_HANDOFF_PATH = (
    "~/SharpEdge-System/outputs/robinhood_execution_handoff.json"
)
DEFAULT_BRIDGE_HANDOFF_NAME = "robinhood_execution_handoff.json"
DEFAULT_OUTPUT_DIR = "outputs"
DEFAULT_BRIDGE_TIMEOUT_SECONDS = 120
BRIDGE_HANDOFF_SCHEMA = "sharpedge.robinhood_execution_handoff.v1"
SUPPORTED_TASK_TYPES = {
    "account_read",
    "market_data",
    "order_draft",
    "order_submit",
    "order_cancel",
    "order_replace",
    "other",
}


class ChatGPTRobinhoodDelegationOutput(BaseModel):
    """Tool output for the ChatGPT Robinhood delegation helper."""

    status: str
    delegation_mode: str
    connector_target: str
    direct_connector_access_supported: bool
    task_type: str
    objective: str
    approval_policy: str
    handoff_json_path: str
    handoff_text_path: str
    chatgpt_oauth_detected: bool
    delegation_prompt: str
    source_handoff_path: str = ""
    warnings: list[str] = Field(default_factory=list)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sanitize_artifact_name(value: str) -> str:
    raw = (value or "").strip() or DEFAULT_ARTIFACT_NAME
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", raw).strip("-._")
    return cleaned or DEFAULT_ARTIFACT_NAME


def _normalize_task_type(value: str) -> tuple[str, list[str]]:
    normalized = (value or "").strip().lower().replace(" ", "_") or "other"
    warnings: list[str] = []
    if normalized not in SUPPORTED_TASK_TYPES:
        warnings.append(
            f"Unrecognized task_type '{value}'. Stored as 'other' so the handoff stays generic."
        )
        normalized = "other"
    return normalized, warnings


def _parse_payload(raw_payload: str) -> tuple[Any, list[str]]:
    text = (raw_payload or "").strip()
    if not text:
        return {}, []
    try:
        return json.loads(text), []
    except json.JSONDecodeError:
        return {"raw_text": text}, [
            "broker_payload_json was not valid JSON. Stored as raw_text instead of pretending."
        ]


def detect_chatgpt_oauth() -> bool:
    """Best-effort local hint only — connector availability is still separate."""
    try:
        from code_puppy.plugins.chatgpt_oauth.utils import load_stored_tokens

        tokens = load_stored_tokens() or {}
        return bool(tokens.get("access_token") and tokens.get("account_id"))
    except Exception:
        return False


def build_delegation_packet(
    *,
    task_type: str,
    objective: str,
    required_result: str = "",
    broker_payload_json: str = "",
    supporting_context: str = "",
    constraints: str = "",
    risk_notes: str = "",
    approval_policy: str = "operator_confirm_required",
) -> tuple[dict[str, Any], list[str]]:
    """Build a structured delegation packet and collect non-fatal warnings."""
    normalized_task_type, warnings = _normalize_task_type(task_type)
    broker_payload, payload_warnings = _parse_payload(broker_payload_json)
    warnings.extend(payload_warnings)

    if normalized_task_type in {"order_submit", "order_cancel", "order_replace"}:
        normalized_policy = (
            approval_policy or ""
        ).strip() or "operator_confirm_required"
        if normalized_policy != "operator_confirm_required":
            warnings.append(
                "Approval policy was coerced to operator_confirm_required for live-order style requests."
            )
        approval_policy = "operator_confirm_required"
    else:
        approval_policy = (approval_policy or "").strip() or "operator_confirm_required"

    packet = {
        "generated_at": _utc_now(),
        "delegation_mode": "manual_handoff",
        "connector_target": "chatgpt_robinhood_connector",
        "direct_connector_access_supported": False,
        "task_type": normalized_task_type,
        "objective": (objective or "").strip(),
        "required_result": (required_result or "").strip(),
        "approval_policy": approval_policy,
        "broker_payload": broker_payload,
        "supporting_context": (supporting_context or "").strip(),
        "constraints": (constraints or "").strip(),
        "risk_notes": (risk_notes or "").strip(),
        "warnings": warnings,
        "recommended_next_step": (
            "Paste the generated prompt into a ChatGPT session that already has the Robinhood connector enabled."
        ),
    }
    return packet, warnings


def build_delegation_prompt(packet: dict[str, Any]) -> str:
    """Render a handoff prompt for ChatGPT with the Robinhood connector."""
    approval_policy = packet.get("approval_policy") or "operator_confirm_required"
    broker_payload = packet.get("broker_payload", {})
    payload_contracts_section = render_payload_contracts_section(broker_payload)
    write_guard = (
        "If this is a live trading action, do not execute it silently. Draft the action, "
        "show the exact order details, and wait for explicit confirmation before any submit, "
        "replace, or cancel step."
    )
    parts = [
        "Use your existing Robinhood connector for this request.",
        "Do not assume local API access from Code Puppy — this is a delegation handoff.",
        f"Task type: {packet.get('task_type', 'other')}",
        f"Objective: {packet.get('objective', '')}",
        f"Required result: {packet.get('required_result', '') or 'Return the connector result and any follow-up questions.'}",
        f"Approval policy: {approval_policy}",
        f"Constraints: {packet.get('constraints', '') or '(none provided)'}",
        f"Supporting context: {packet.get('supporting_context', '') or '(none provided)'}",
        f"Risk notes: {packet.get('risk_notes', '') or '(none provided)'}",
    ]
    if payload_contracts_section:
        parts.extend([payload_contracts_section])
    parts.extend(
        [
            "Broker payload:",
            json.dumps(broker_payload, indent=2, sort_keys=True),
            write_guard,
            "Reply with:",
            "1. what you observed or prepared through Robinhood",
            "2. any blockers or missing fields",
            "3. the exact order draft if an order action was requested",
        ]
    )
    return "\n".join(parts)


def _resolve_handoff_path(handoff_path: str | Path) -> Path:
    if isinstance(handoff_path, Path):
        return handoff_path.expanduser()
    text = (handoff_path or "").strip() or DEFAULT_BRIDGE_HANDOFF_PATH
    return Path(text).expanduser()


def _load_bridge_handoff(handoff_path: str | Path) -> dict[str, Any]:
    path = _resolve_handoff_path(handoff_path)
    if not path.exists():
        raise FileNotFoundError(f"Bridge handoff file not found: {path}")
    try:
        handoff = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Bridge handoff is not valid JSON: {exc}") from exc
    if not isinstance(handoff, dict) or not handoff:
        raise ValueError("Bridge handoff must decode to a non-empty JSON object.")
    schema = (handoff.get("schema") or "").strip()
    if schema != BRIDGE_HANDOFF_SCHEMA:
        raise ValueError(
            f"Unsupported bridge handoff schema '{schema or '<missing>'}'. "
            f"Expected {BRIDGE_HANDOFF_SCHEMA}."
        )
    return handoff


def _join_sections(*parts: str) -> str:
    return "\n".join(part.strip() for part in parts if part and part.strip())


def _default_bridge_objective(handoff: dict[str, Any]) -> str:
    command_plan = handoff.get("command_plan") or {}
    signal_summary = handoff.get("signal_summary") or {}
    task_type = command_plan.get("command") or "broker_action"
    symbol = signal_summary.get("symbol") or "the requested symbol"
    return (
        f"Use the SharpEdge bridge handoff to prepare the {task_type} request for {symbol} "
        "exactly as specified, then wait for explicit confirmation before any live broker action."
    )


def _default_bridge_supporting_context(handoff: dict[str, Any]) -> str:
    decision = handoff.get("decision") or {}
    command_plan = handoff.get("command_plan") or {}
    signal_summary = handoff.get("signal_summary") or {}
    notes = handoff.get("notes") or []
    return _join_sections(
        f"Bridge source: {((handoff.get('source') or {}).get('signal_path') or '(unknown signal path)')}",
        f"Bridge decision: {decision.get('action', 'unknown')} — {decision.get('reason', '')}",
        f"Bridge route: {command_plan.get('route', 'unknown')} | status: {command_plan.get('status', 'unknown')}",
        f"Signal summary: {json.dumps(signal_summary, sort_keys=True)}",
        f"Bridge notes: {'; '.join(str(note) for note in notes)}" if notes else "",
    )


def _default_bridge_risk_notes(handoff: dict[str, Any]) -> str:
    risk = handoff.get("risk") or {}
    blocks = risk.get("blocks") or []
    notes = risk.get("notes") or []
    pieces = [str((handoff.get("delegation") or {}).get("risk_notes") or "").strip()]
    if blocks:
        pieces.append("Risk blocks: " + "; ".join(str(block) for block in blocks))
    if notes:
        pieces.append("Risk notes: " + "; ".join(str(note) for note in notes))
    return _join_sections(*pieces)


def build_delegation_packet_from_bridge_handoff(
    *,
    handoff_path: str | Path = DEFAULT_BRIDGE_HANDOFF_PATH,
    objective: str = "",
    required_result: str = "",
    supporting_context: str = "",
    constraints: str = "",
    risk_notes: str = "",
) -> tuple[dict[str, Any], list[str]]:
    """Translate a SharpEdge bridge handoff into a ChatGPT delegation packet."""
    handoff = _load_bridge_handoff(handoff_path)
    decision = handoff.get("decision") or {}
    command_plan = handoff.get("command_plan") or {}
    delegation = handoff.get("delegation") or {}
    operator_gate = handoff.get("operator_gate") or {}
    broker_payload = delegation.get("broker_payload") or {}

    if decision.get("action") != "trade":
        raise ValueError(
            "Bridge handoff action is not 'trade'; refusing to package a broker delegation."
        )
    if command_plan.get("route") != "chatgpt_delegate":
        raise ValueError(
            "Bridge handoff route is not 'chatgpt_delegate'; this is not a connector-bound action."
        )
    if command_plan.get("status") != "awaiting_operator_confirm":
        raise ValueError(
            "Bridge handoff is not approval-ready; expected status 'awaiting_operator_confirm'."
        )
    if not operator_gate.get("required"):
        raise ValueError(
            "Bridge handoff does not require the operator gate; refusing to package a live broker action."
        )
    if not isinstance(broker_payload, dict) or not broker_payload:
        raise ValueError("Bridge handoff did not include a usable broker_payload.")

    packet, warnings = build_delegation_packet(
        task_type=str(
            delegation.get("task_type") or command_plan.get("command") or "other"
        ),
        objective=(objective or "").strip() or _default_bridge_objective(handoff),
        required_result=(required_result or "").strip()
        or str(delegation.get("required_result") or "").strip(),
        broker_payload_json=json.dumps(broker_payload),
        supporting_context=_join_sections(
            _default_bridge_supporting_context(handoff),
            supporting_context,
        ),
        constraints=_join_sections(
            str(delegation.get("constraints") or ""),
            constraints,
        ),
        risk_notes=_join_sections(_default_bridge_risk_notes(handoff), risk_notes),
        approval_policy=str(
            command_plan.get("approval_policy") or "operator_confirm_required"
        ),
    )
    return packet, warnings


def prepare_delegation_from_bridge_handoff(
    *,
    handoff_path: str | Path = DEFAULT_BRIDGE_HANDOFF_PATH,
    artifact_name: str = DEFAULT_BRIDGE_ARTIFACT_NAME,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    base_dir: Path | None = None,
    objective: str = "",
    required_result: str = "",
    supporting_context: str = "",
    constraints: str = "",
    risk_notes: str = "",
) -> ChatGPTRobinhoodDelegationOutput:
    """Load a bridge handoff, package it, and persist ChatGPT delegation artifacts."""
    resolved_handoff_path = _resolve_handoff_path(handoff_path)
    packet, warnings = build_delegation_packet_from_bridge_handoff(
        handoff_path=resolved_handoff_path,
        objective=objective,
        required_result=required_result,
        supporting_context=supporting_context,
        constraints=constraints,
        risk_notes=risk_notes,
    )
    prompt_text = build_delegation_prompt(packet)
    json_path, text_path = write_delegation_artifacts(
        packet,
        prompt_text,
        artifact_name=artifact_name,
        output_dir=output_dir,
        base_dir=base_dir,
    )
    return ChatGPTRobinhoodDelegationOutput(
        status="prepared",
        delegation_mode=packet["delegation_mode"],
        connector_target=packet["connector_target"],
        direct_connector_access_supported=packet["direct_connector_access_supported"],
        task_type=packet["task_type"],
        objective=packet["objective"],
        approval_policy=packet["approval_policy"],
        handoff_json_path=str(json_path),
        handoff_text_path=str(text_path),
        chatgpt_oauth_detected=detect_chatgpt_oauth(),
        delegation_prompt=prompt_text,
        source_handoff_path=str(resolved_handoff_path),
        warnings=warnings,
    )


def _resolve_bridge_root(bridge_root: str | Path) -> Path:
    if isinstance(bridge_root, Path):
        path = bridge_root.expanduser()
    else:
        text = (bridge_root or "").strip() or DEFAULT_BRIDGE_REPO_ROOT
        path = Path(text).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"SharpEdge-Robinhood-Bridge repo not found: {path}")
    return path


def _bridge_handoff_target(
    handoff_output_dir: str | Path | None,
    handoff_latest_name: str,
) -> Path:
    if handoff_output_dir is None:
        output_dir = _resolve_handoff_path(DEFAULT_BRIDGE_HANDOFF_PATH).parent
    elif isinstance(handoff_output_dir, Path):
        output_dir = handoff_output_dir.expanduser()
    else:
        text = (handoff_output_dir or "").strip()
        output_dir = (
            Path(text).expanduser()
            if text
            else _resolve_handoff_path(DEFAULT_BRIDGE_HANDOFF_PATH).parent
        )
    latest_name = (handoff_latest_name or "").strip() or DEFAULT_BRIDGE_HANDOFF_NAME
    return output_dir / latest_name


def run_bridge_signal_handoff(
    *,
    bridge_root: str | Path = DEFAULT_BRIDGE_REPO_ROOT,
    signal_path: str | Path = "",
    command_name: str = "order_submit",
    test: bool = False,
    handoff_output_dir: str | Path | None = None,
    handoff_latest_name: str = DEFAULT_BRIDGE_HANDOFF_NAME,
    timeout_seconds: int = DEFAULT_BRIDGE_TIMEOUT_SECONDS,
) -> Path:
    """Invoke SharpEdge-Robinhood-Bridge to produce a fresh handoff artifact."""
    resolved_bridge_root = _resolve_bridge_root(bridge_root)
    target_path = _bridge_handoff_target(handoff_output_dir, handoff_latest_name)

    command = [
        sys.executable,
        "-m",
        "sharpedge_robinhood_bridge",
        "signal-handoff",
        "--command-name",
        (command_name or "").strip() or "order_submit",
        "--latest-name",
        target_path.name,
        "--out-dir",
        str(target_path.parent),
    ]
    if signal_path:
        resolved_signal_path = (
            signal_path.expanduser()
            if isinstance(signal_path, Path)
            else Path(signal_path).expanduser()
        )
        command.extend(["--signal", str(resolved_signal_path)])
    if test:
        command.append("--test")

    env = os.environ.copy()
    bridge_src = str(resolved_bridge_root / "src")
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        bridge_src
        if not existing_pythonpath
        else bridge_src + os.pathsep + existing_pythonpath
    )

    try:
        result = subprocess.run(
            command,
            cwd=resolved_bridge_root,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(
            "Timed out waiting for SharpEdge-Robinhood-Bridge signal-handoff to complete."
        ) from exc

    if result.returncode != 0:
        details = _join_sections(result.stdout, result.stderr)
        raise RuntimeError(
            "SharpEdge-Robinhood-Bridge signal-handoff failed."
            + (f"\n{details}" if details else "")
        )
    if not target_path.exists():
        raise FileNotFoundError(
            "Bridge signal-handoff finished but did not produce the expected handoff at "
            f"{target_path}."
        )
    return target_path


def prepare_delegation_from_signal(
    *,
    bridge_root: str | Path = DEFAULT_BRIDGE_REPO_ROOT,
    signal_path: str | Path = "",
    bridge_command_name: str = "order_submit",
    test: bool = False,
    handoff_output_dir: str | Path | None = None,
    handoff_latest_name: str = DEFAULT_BRIDGE_HANDOFF_NAME,
    bridge_timeout_seconds: int = DEFAULT_BRIDGE_TIMEOUT_SECONDS,
    artifact_name: str = DEFAULT_BRIDGE_ARTIFACT_NAME,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    base_dir: Path | None = None,
    objective: str = "",
    required_result: str = "",
    supporting_context: str = "",
    constraints: str = "",
    risk_notes: str = "",
) -> ChatGPTRobinhoodDelegationOutput:
    """Run the bridge signal-handoff, then package the resulting handoff for ChatGPT."""
    handoff_path = run_bridge_signal_handoff(
        bridge_root=bridge_root,
        signal_path=signal_path,
        command_name=bridge_command_name,
        test=test,
        handoff_output_dir=handoff_output_dir,
        handoff_latest_name=handoff_latest_name,
        timeout_seconds=bridge_timeout_seconds,
    )
    try:
        return prepare_delegation_from_bridge_handoff(
            handoff_path=handoff_path,
            artifact_name=artifact_name,
            output_dir=output_dir,
            base_dir=base_dir,
            objective=objective,
            required_result=required_result,
            supporting_context=supporting_context,
            constraints=constraints,
            risk_notes=risk_notes,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise ValueError(
            f"Bridge handoff at {handoff_path} was not connector-ready: {exc}"
        ) from exc


def write_delegation_artifacts(
    packet: dict[str, Any],
    prompt_text: str,
    *,
    artifact_name: str = DEFAULT_ARTIFACT_NAME,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    base_dir: Path | None = None,
) -> tuple[Path, Path]:
    """Persist JSON + text artifacts for downstream handoff."""
    root = Path(base_dir) if base_dir is not None else Path.cwd()
    output_path = root / output_dir
    output_path.mkdir(parents=True, exist_ok=True)

    safe_name = _sanitize_artifact_name(artifact_name)
    json_path = output_path / f"{safe_name}.json"
    text_path = output_path / f"{safe_name}.txt"

    json_path.write_text(json.dumps(packet, indent=2, sort_keys=True), encoding="utf-8")
    text_path.write_text(prompt_text + "\n", encoding="utf-8")
    return json_path, text_path
