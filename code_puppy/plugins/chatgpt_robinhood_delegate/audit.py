"""Post-connector audit helpers for ChatGPT Robinhood delegation flows."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .live_positions import build_live_positions_snapshot, write_live_positions_snapshot
from .tooling import (
    DEFAULT_OUTPUT_DIR,
    _join_sections,
    _load_bridge_handoff,
    _resolve_handoff_path,
    _sanitize_artifact_name,
    _utc_now,
)

DEFAULT_AUDIT_ARTIFACT_NAME = "chatgpt_robinhood_connector_audit"
DEFAULT_AUDIT_LOG_NAME = "robinhood_connector_audit_log"
CONNECTOR_AUDIT_SCHEMA = "sharpedge.robinhood_connector_audit.v1"
JOURNAL_STUB_SCHEMA = "sharpedge.trade_journal_stub.v1"
AUDIT_LOG_ENTRY_SCHEMA = "sharpedge.robinhood_connector_audit_log_entry.v1"

_STATUS_HINTS = {
    "filled": ("filled", ["filled", "fully filled", "fill complete"]),
    "submitted": ("submitted", ["submitted", "placed", "sent", "accepted"]),
    "drafted": (
        "drafted",
        ["draft", "drafted", "prepared", "awaiting confirmation", "review draft"],
    ),
    "replaced": ("replaced", ["replaced", "replace submitted"]),
    "canceled": ("canceled", ["canceled", "cancelled"]),
    "blocked": (
        "blocked",
        ["blocked", "rejected", "failed", "error", "unable", "missing field"],
    ),
}


class ChatGPTRobinhoodAuditOutput(BaseModel):
    """Tool output for post-connector audit ingestion."""

    status: str
    connector_status: str
    fill_status: str
    symbol: str
    task_type: str
    broker_order_id: str = ""
    source_handoff_path: str = ""
    source_response_path: str = ""
    audit_json_path: str
    journal_json_path: str
    journal_markdown_path: str
    audit_log_jsonl_path: str = ""
    live_positions_json_path: str = ""
    warnings: list[str] = Field(default_factory=list)


def _coerce_string_list(value: Any) -> list[str]:
    if value in (None, "", [], {}):
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, dict):
        parts = [f"{key}: {item}" for key, item in value.items() if str(item).strip()]
        return [part for part in parts if part.strip()]
    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            items.extend(_coerce_string_list(item))
        return items
    text = str(value).strip()
    return [text] if text else []


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _extract_json_block(text: str) -> str:
    stripped = (text or "").strip()
    if not stripped:
        return ""
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, flags=re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def _read_response_inputs(
    *,
    response_text: str = "",
    response_json: str = "",
    response_file_path: str = "",
) -> tuple[str, dict[str, Any], str, list[str]]:
    warnings: list[str] = []
    source_response_path = ""
    file_text = ""

    if response_file_path:
        path = Path(response_file_path).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"Connector response file not found: {path}")
        source_response_path = str(path)
        file_text = path.read_text(encoding="utf-8")

    effective_json = (response_json or "").strip()
    effective_text = (response_text or file_text or "").strip()
    if not effective_json and not effective_text:
        raise ValueError(
            "Provide connector response material via response_text, response_json, or response_file_path."
        )

    if effective_json:
        try:
            parsed = json.loads(effective_json)
        except json.JSONDecodeError as exc:
            raise ValueError(f"response_json was not valid JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ValueError("response_json must decode to a JSON object.")
        return effective_text, parsed, source_response_path, warnings

    maybe_json = _extract_json_block(effective_text)
    if maybe_json:
        try:
            parsed = json.loads(maybe_json)
        except json.JSONDecodeError:
            parsed = {}
            warnings.append(
                "Connector response looked JSON-ish but did not parse cleanly; kept raw text only."
            )
        else:
            if isinstance(parsed, dict):
                return effective_text, parsed, source_response_path, warnings
            warnings.append(
                "Connector response JSON block was not an object; kept raw text only."
            )

    return effective_text, {}, source_response_path, warnings


def _dict_candidates(payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = [payload]
    for value in payload.values():
        if isinstance(value, dict):
            candidates.append(value)
            for nested in value.values():
                if isinstance(nested, dict):
                    candidates.append(nested)
    return candidates


def _first_value(payload: dict[str, Any], keys: list[str]) -> Any:
    for candidate in _dict_candidates(payload):
        for key in keys:
            value = candidate.get(key)
            if value not in (None, "", [], {}):
                return value
    return None


def _first_text(payload: dict[str, Any], keys: list[str]) -> str:
    value = _first_value(payload, keys)
    if value is None:
        return ""
    text = str(value).strip()
    return text


def _infer_status_from_text(text: str) -> str:
    lowered = (text or "").lower()
    for status, (_, hints) in _STATUS_HINTS.items():
        if any(hint in lowered for hint in hints):
            return status
    return "unknown"


def _normalize_connector_status(payload: dict[str, Any], raw_text: str) -> str:
    direct = _first_text(
        payload,
        [
            "connector_status",
            "status",
            "execution_status",
            "order_status",
            "submission_status",
            "state",
            "result",
        ],
    )
    direct_status = _infer_status_from_text(direct)
    if direct_status != "unknown":
        return direct_status
    inferred = _infer_status_from_text(raw_text)
    if inferred != "unknown":
        return inferred
    return "unknown"


def _normalize_fill_status(
    payload: dict[str, Any],
    raw_text: str,
    connector_status: str,
) -> str:
    direct = _first_text(
        payload,
        [
            "fill_status",
            "filled_status",
            "execution_fill_status",
            "order_fill_status",
        ],
    )
    lowered = _join_sections(direct, raw_text).lower()
    if "partial" in lowered and "fill" in lowered:
        return "partial_fill"
    if "filled" in lowered:
        return "filled"
    if connector_status == "drafted":
        return "not_submitted"
    if connector_status in {"submitted", "replaced"}:
        return "submitted_unfilled"
    if connector_status == "canceled":
        return "canceled"
    if connector_status == "blocked":
        return "blocked"
    return "unknown"


def _default_summary(payload: dict[str, Any], raw_text: str) -> str:
    summary = _first_text(
        payload,
        [
            "connector_summary",
            "summary",
            "message",
            "result_summary",
            "details",
            "notes",
        ],
    )
    if summary:
        return summary
    stripped = (raw_text or "").strip()
    if stripped:
        return stripped[:400]
    return "No connector summary was provided."


def _build_follow_up_prompts(
    *,
    connector_status: str,
    fill_status: str,
    blockers: list[str],
    questions: list[str],
) -> list[str]:
    prompts: list[str] = []
    if connector_status == "drafted":
        prompts.append(
            "Did the operator approve the exact draft details before any submit step?"
        )
        prompts.append("What were the final limit price, contracts, and sizing shown?")
    elif connector_status in {"submitted", "replaced"}:
        prompts.append("Was the order actually submitted to Robinhood, or only staged?")
        prompts.append(
            "What were the final submitted price, timestamp, and any slippage versus plan?"
        )
    elif connector_status == "filled":
        prompts.append(
            "What was the actual fill price, timestamp, and slippage versus plan?"
        )
        prompts.append("Did the fill still match the original thesis and risk budget?")
    elif connector_status == "blocked":
        prompts.append(
            "Which blocker needs to be fixed upstream before retrying this flow?"
        )
    elif connector_status == "canceled":
        prompts.append(
            "Why was the order canceled, and was a replacement plan discussed?"
        )
    else:
        prompts.append(
            "What exactly happened in the connector session, in plain language?"
        )

    if fill_status == "partial_fill":
        prompts.append("How much of the order filled, and what remains open?")
    if blockers:
        prompts.append(
            "Are the listed blockers connector-side, broker-side, or missing-input issues?"
        )
    prompts.extend(question for question in questions if question.endswith("?"))
    return _dedupe_preserve_order(prompts)


def build_connector_audit_packet(
    *,
    response_text: str = "",
    response_json: str = "",
    response_file_path: str = "",
    handoff_path: str = "",
) -> tuple[dict[str, Any], list[str]]:
    """Normalize a connector result into a structured audit artifact."""
    raw_text, connector_payload, source_response_path, warnings = _read_response_inputs(
        response_text=response_text,
        response_json=response_json,
        response_file_path=response_file_path,
    )

    handoff: dict[str, Any] = {}
    source_handoff_path = ""
    if (handoff_path or "").strip():
        resolved_handoff = _resolve_handoff_path(handoff_path)
        handoff = _load_bridge_handoff(resolved_handoff)
        source_handoff_path = str(resolved_handoff)

    connector_status = _normalize_connector_status(connector_payload, raw_text)
    fill_status = _normalize_fill_status(connector_payload, raw_text, connector_status)
    summary = _default_summary(connector_payload, raw_text)
    blockers = _dedupe_preserve_order(
        _coerce_string_list(
            _first_value(
                connector_payload,
                ["blockers", "errors", "missing_fields", "missing_information"],
            )
        )
    )
    questions = _dedupe_preserve_order(
        _coerce_string_list(
            _first_value(
                connector_payload,
                ["questions", "follow_up_questions", "open_questions"],
            )
        )
    )
    if connector_status == "blocked" and not blockers:
        blockers = [summary]

    command_plan = handoff.get("command_plan") or {}
    delegation = handoff.get("delegation") or {}
    decision = handoff.get("decision") or {}
    signal_summary = handoff.get("signal_summary") or {}
    broker_payload = delegation.get("broker_payload") or {}
    task_type = (
        str(
            delegation.get("task_type") or command_plan.get("command") or "other"
        ).strip()
        or "other"
    )
    symbol = str(
        broker_payload.get("symbol")
        or signal_summary.get("symbol")
        or _first_value(connector_payload, ["symbol", "ticker", "underlying_symbol"])
        or ""
    ).strip()

    broker_order_id = _first_text(
        connector_payload,
        ["broker_order_id", "order_id", "robinhood_order_id", "id"],
    )
    if not broker_order_id and connector_status in {"submitted", "filled", "replaced"}:
        warnings.append(
            "Connector outcome looked live, but no broker_order_id was present in the response."
        )

    audit_packet = {
        "schema": CONNECTOR_AUDIT_SCHEMA,
        "created_at": _utc_now(),
        "source_handoff_path": source_handoff_path,
        "source_response_path": source_response_path,
        "requested_action": {
            "task_type": task_type,
            "symbol": symbol,
            "approval_policy": command_plan.get("approval_policy") or "",
            "objective": delegation.get("objective") or "",
            "required_result": delegation.get("required_result") or "",
            "broker_payload": broker_payload,
        },
        "bridge_context": {
            "decision_action": decision.get("action"),
            "decision_reason": decision.get("reason"),
            "route": command_plan.get("route"),
            "command_status": command_plan.get("status"),
            "trade_gate": signal_summary.get("trade_gate"),
            "operator_confirmation_required": (handoff.get("operator_gate") or {}).get(
                "required"
            ),
            "risk_notes": _coerce_string_list((handoff.get("risk") or {}).get("notes")),
            "handoff_notes": _coerce_string_list(handoff.get("notes")),
        },
        "connector_observation": {
            "connector_status": connector_status,
            "fill_status": fill_status,
            "broker_order_id": broker_order_id,
            "summary": summary,
            "blockers": blockers,
            "questions": questions,
            "raw_text": raw_text,
            "parsed_payload": connector_payload,
        },
        "operator_follow_up": {
            "required": connector_status
            in {"drafted", "submitted", "replaced", "filled", "unknown"}
            or bool(questions),
            "prompts": _build_follow_up_prompts(
                connector_status=connector_status,
                fill_status=fill_status,
                blockers=blockers,
                questions=questions,
            ),
        },
        "warnings": _dedupe_preserve_order(warnings),
    }
    return audit_packet, audit_packet["warnings"]


def build_trade_journal_stub(audit_packet: dict[str, Any]) -> dict[str, Any]:
    """Build a journal-oriented companion artifact from a connector audit packet."""
    requested = audit_packet.get("requested_action") or {}
    bridge_context = audit_packet.get("bridge_context") or {}
    observed = audit_packet.get("connector_observation") or {}
    connector_status = str(observed.get("connector_status") or "unknown")
    fill_status = str(observed.get("fill_status") or "unknown")
    symbol = str(requested.get("symbol") or "").strip()
    headline_symbol = symbol or "the symbol"
    headline = f"Connector reported {connector_status} for {headline_symbol}."
    if fill_status not in {"unknown", "not_submitted"}:
        headline = f"Connector reported {connector_status} for {headline_symbol} ({fill_status})."

    return {
        "schema": JOURNAL_STUB_SCHEMA,
        "created_at": _utc_now(),
        "source_handoff_path": audit_packet.get("source_handoff_path") or "",
        "source_response_path": audit_packet.get("source_response_path") or "",
        "source_audit_schema": audit_packet.get("schema"),
        "symbol": symbol,
        "task_type": requested.get("task_type") or "other",
        "headline": headline,
        "connector_status": connector_status,
        "fill_status": fill_status,
        "broker_order_id": observed.get("broker_order_id") or "",
        "setup_context": {
            "trade_gate": bridge_context.get("trade_gate"),
            "decision_action": bridge_context.get("decision_action"),
            "decision_reason": bridge_context.get("decision_reason"),
            "route": bridge_context.get("route"),
            "command_status": bridge_context.get("command_status"),
        },
        "journal_entry": {
            "intended_action": requested,
            "actual_outcome": {
                "summary": observed.get("summary"),
                "connector_status": connector_status,
                "fill_status": fill_status,
                "broker_order_id": observed.get("broker_order_id") or "",
            },
            "blockers": observed.get("blockers") or [],
            "questions": observed.get("questions") or [],
            "warnings": audit_packet.get("warnings") or [],
        },
        "operator_fields_to_confirm": _build_follow_up_prompts(
            connector_status=connector_status,
            fill_status=fill_status,
            blockers=observed.get("blockers") or [],
            questions=observed.get("questions") or [],
        ),
    }


def render_trade_journal_stub_markdown(journal_stub: dict[str, Any]) -> str:
    """Render a human-usable markdown stub for trade journaling."""
    lines = [
        f"# Trade Journal Stub — {journal_stub.get('symbol') or 'unknown-symbol'}",
        "",
        f"- created_at: {journal_stub.get('created_at', '')}",
        f"- task_type: {journal_stub.get('task_type', '')}",
        f"- connector_status: {journal_stub.get('connector_status', '')}",
        f"- fill_status: {journal_stub.get('fill_status', '')}",
        f"- broker_order_id: {journal_stub.get('broker_order_id', '') or '(none reported)'}",
        "",
        f"> {journal_stub.get('headline', '')}",
        "",
        "## Setup context",
    ]
    setup_context = journal_stub.get("setup_context") or {}
    for key in [
        "trade_gate",
        "decision_action",
        "decision_reason",
        "route",
        "command_status",
    ]:
        lines.append(f"- {key}: {setup_context.get(key) or '(unknown)'}")

    outcome = (journal_stub.get("journal_entry") or {}).get("actual_outcome") or {}
    lines.extend(
        [
            "",
            "## Connector outcome",
            f"- summary: {outcome.get('summary') or '(none provided)'}",
        ]
    )

    blockers = (journal_stub.get("journal_entry") or {}).get("blockers") or []
    questions = (journal_stub.get("journal_entry") or {}).get("questions") or []
    warnings = (journal_stub.get("journal_entry") or {}).get("warnings") or []

    for header, values in [
        ("## Blockers", blockers),
        ("## Follow-up questions", questions),
        ("## Warnings", warnings),
        (
            "## Operator fields to confirm",
            journal_stub.get("operator_fields_to_confirm") or [],
        ),
    ]:
        lines.extend(["", header])
        if values:
            lines.extend(f"- {value}" for value in values)
        else:
            lines.append("- (none)")

    return "\n".join(lines).rstrip() + "\n"


def _append_audit_log(
    *,
    output_path: Path,
    safe_name: str,
    audit_packet: dict[str, Any],
    journal_stub: dict[str, Any],
) -> Path:
    log_path = output_path / f"{DEFAULT_AUDIT_LOG_NAME}.jsonl"
    observed = audit_packet.get("connector_observation") or {}
    requested = audit_packet.get("requested_action") or {}
    entry = {
        "schema": AUDIT_LOG_ENTRY_SCHEMA,
        "created_at": _utc_now(),
        "artifact_name": safe_name,
        "symbol": requested.get("symbol") or "",
        "task_type": requested.get("task_type") or "other",
        "connector_status": observed.get("connector_status") or "unknown",
        "fill_status": observed.get("fill_status") or "unknown",
        "broker_order_id": observed.get("broker_order_id") or "",
        "headline": journal_stub.get("headline") or "",
        "blockers": observed.get("blockers") or [],
        "questions": observed.get("questions") or [],
        "source_handoff_path": audit_packet.get("source_handoff_path") or "",
        "source_response_path": audit_packet.get("source_response_path") or "",
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
    return log_path


def write_audit_artifacts(
    audit_packet: dict[str, Any],
    journal_stub: dict[str, Any],
    *,
    artifact_name: str = DEFAULT_AUDIT_ARTIFACT_NAME,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    base_dir: Path | None = None,
    append_log: bool = True,
) -> tuple[Path, Path, Path, Path | None]:
    """Persist audit + journal companion artifacts."""
    root = Path(base_dir) if base_dir is not None else Path.cwd()
    output_path = root / output_dir
    output_path.mkdir(parents=True, exist_ok=True)

    safe_name = _sanitize_artifact_name(artifact_name)
    audit_path = output_path / f"{safe_name}.json"
    journal_json_path = output_path / f"{safe_name}_journal_stub.json"
    journal_markdown_path = output_path / f"{safe_name}_journal_stub.md"

    audit_path.write_text(
        json.dumps(audit_packet, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    journal_json_path.write_text(
        json.dumps(journal_stub, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    journal_markdown_path.write_text(
        render_trade_journal_stub_markdown(journal_stub),
        encoding="utf-8",
    )

    log_path = None
    if append_log:
        log_path = _append_audit_log(
            output_path=output_path,
            safe_name=safe_name,
            audit_packet=audit_packet,
            journal_stub=journal_stub,
        )
    return audit_path, journal_json_path, journal_markdown_path, log_path


def ingest_connector_audit(
    *,
    response_text: str = "",
    response_json: str = "",
    response_file_path: str = "",
    handoff_path: str = "",
    artifact_name: str = DEFAULT_AUDIT_ARTIFACT_NAME,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    base_dir: Path | None = None,
    append_log: bool = True,
) -> ChatGPTRobinhoodAuditOutput:
    """Build and persist connector audit artifacts."""
    audit_packet, warnings = build_connector_audit_packet(
        response_text=response_text,
        response_json=response_json,
        response_file_path=response_file_path,
        handoff_path=handoff_path,
    )
    journal_stub = build_trade_journal_stub(audit_packet)
    audit_path, journal_json_path, journal_markdown_path, log_path = (
        write_audit_artifacts(
            audit_packet,
            journal_stub,
            artifact_name=artifact_name,
            output_dir=output_dir,
            base_dir=base_dir,
            append_log=append_log,
        )
    )
    observed = audit_packet.get("connector_observation") or {}
    requested = audit_packet.get("requested_action") or {}
    live_positions_json_path = ""
    snapshot, snapshot_warnings = build_live_positions_snapshot(
        observed.get("parsed_payload") or {},
        task_type=str(requested.get("task_type") or "other"),
        symbol=str(requested.get("symbol") or ""),
        source_response_path=str(audit_packet.get("source_response_path") or ""),
        source_handoff_path=str(audit_packet.get("source_handoff_path") or ""),
    )
    warnings = list(warnings)
    warnings.extend(snapshot_warnings)
    if snapshot is not None:
        live_positions_json_path = str(
            write_live_positions_snapshot(
                snapshot,
                output_dir=output_dir,
                base_dir=base_dir,
            )
        )

    return ChatGPTRobinhoodAuditOutput(
        status="recorded",
        connector_status=str(observed.get("connector_status") or "unknown"),
        fill_status=str(observed.get("fill_status") or "unknown"),
        symbol=str(requested.get("symbol") or ""),
        task_type=str(requested.get("task_type") or "other"),
        broker_order_id=str(observed.get("broker_order_id") or ""),
        source_handoff_path=str(audit_packet.get("source_handoff_path") or ""),
        source_response_path=str(audit_packet.get("source_response_path") or ""),
        audit_json_path=str(audit_path),
        journal_json_path=str(journal_json_path),
        journal_markdown_path=str(journal_markdown_path),
        audit_log_jsonl_path=str(log_path) if log_path is not None else "",
        live_positions_json_path=live_positions_json_path,
        warnings=warnings,
    )
