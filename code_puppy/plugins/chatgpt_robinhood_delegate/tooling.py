"""Helpers for delegating Robinhood requests through ChatGPT.

This plugin is intentionally honest: Code Puppy's current ChatGPT OAuth path
speaks to the Codex backend as a model provider, not to ChatGPT's connector
surface. So the safe v1 is a structured handoff artifact that another system
(or a human in the ChatGPT UI) can execute using an already-authenticated
Robinhood connector.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

DEFAULT_ARTIFACT_NAME = "chatgpt_robinhood_delegation"
DEFAULT_OUTPUT_DIR = "outputs"
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
        normalized_policy = (approval_policy or "").strip() or "operator_confirm_required"
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
    write_guard = (
        "If this is a live trading action, do not execute it silently. Draft the action, "
        "show the exact order details, and wait for explicit confirmation before any submit, "
        "replace, or cancel step."
    )
    return "\n".join(
        [
            "Use your existing Robinhood connector for this request.",
            "Do not assume local API access from Code Puppy — this is a delegation handoff.",
            f"Task type: {packet.get('task_type', 'other')}",
            f"Objective: {packet.get('objective', '')}",
            f"Required result: {packet.get('required_result', '') or 'Return the connector result and any follow-up questions.'}",
            f"Approval policy: {approval_policy}",
            f"Constraints: {packet.get('constraints', '') or '(none provided)'}",
            f"Supporting context: {packet.get('supporting_context', '') or '(none provided)'}",
            f"Risk notes: {packet.get('risk_notes', '') or '(none provided)'}",
            "Broker payload:",
            json.dumps(packet.get("broker_payload", {}), indent=2, sort_keys=True),
            write_guard,
            "Reply with:",
            "1. what you observed or prepared through Robinhood",
            "2. any blockers or missing fields",
            "3. the exact order draft if an order action was requested",
        ]
    )


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
