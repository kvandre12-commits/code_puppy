"""Render bridge payload_contracts into readable ChatGPT handoff sections."""

from __future__ import annotations

from typing import Any


def _stringify(value: Any) -> str:
    if value in (None, "", [], {}):
        return ""
    return str(value)


def _bullet_list(values: list[str], *, indent: str = "- ") -> list[str]:
    return [f"{indent}{value}" for value in values if str(value).strip()]


def _render_read_contracts(payload_contracts: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    read_contracts = payload_contracts.get("read_contracts") or {}
    if not isinstance(read_contracts, dict) or not read_contracts:
        return lines

    lines.extend(["Connector contract plan:", "", "Read-side contracts:"])
    for name, contract in read_contracts.items():
        if not isinstance(contract, dict):
            continue
        requested_checks = contract.get("requested_checks") or []
        lines.append(f"- {name}: {contract.get('contract_type') or 'read_contract'}")
        if requested_checks:
            lines.append(
                f"  checks: {', '.join(str(item) for item in requested_checks)}"
            )
        if contract.get("artifact_target"):
            lines.append(f"  artifact_target: {contract['artifact_target']}")
        if contract.get("safe_output"):
            lines.append(f"  safe_output: {contract['safe_output']}")
    return lines


def _render_lookup_contract(contract: dict[str, Any]) -> list[str]:
    lines = ["  lookup phase:"]
    tool_sequence = contract.get("tool_sequence") or []
    for step in tool_sequence:
        if not isinstance(step, dict):
            continue
        tool_name = _stringify(step.get("tool_name")) or "unknown_tool"
        payload = step.get("payload") or {}
        payload_bits = []
        if isinstance(payload, dict):
            for key in (
                "underlying_symbol",
                "chain_symbol",
                "expiration_dates",
                "type",
            ):
                if payload.get(key) not in (None, ""):
                    payload_bits.append(f"{key}={payload[key]}")
        suffix = f" ({', '.join(payload_bits)})" if payload_bits else ""
        lines.append(f"    - {tool_name}{suffix}")

    selection_policy = contract.get("selection_policy") or {}
    candidate_strikes = selection_policy.get("candidate_strikes") or []
    if candidate_strikes:
        lines.append(
            "    - selection policy: "
            + f"{selection_policy.get('policy_name') or 'unknown'}"
            + " | candidate ladder "
            + ", ".join(str(item) for item in candidate_strikes)
        )
    elif selection_policy.get("selected_strike") not in (None, ""):
        lines.append(
            "    - selection policy: "
            + f"{selection_policy.get('policy_name') or 'unknown'}"
            + f" | selected strike {selection_policy.get('selected_strike')}"
        )
    return lines


def _render_action_contract(label: str, contract: dict[str, Any]) -> list[str]:
    tool_name = _stringify(contract.get("tool_name")) or "unknown_tool"
    lines = [f"  {label}: {tool_name}"]
    payload = contract.get("payload_template") or {}
    if isinstance(payload, dict):
        if payload.get("account_number"):
            lines.append(f"    - account_number: {payload['account_number']}")
        if payload.get("quantity"):
            lines.append(f"    - quantity: {payload['quantity']}")
        if payload.get("price"):
            lines.append(f"    - price: {payload['price']}")
        legs = payload.get("legs") or []
        if isinstance(legs, list) and legs and isinstance(legs[0], dict):
            leg = legs[0]
            leg_bits = []
            for key in ("option_id", "side", "position_effect"):
                if leg.get(key) not in (None, ""):
                    leg_bits.append(f"{key}={leg[key]}")
            if leg_bits:
                lines.append("    - leg: " + ", ".join(leg_bits))
    return lines


def _render_execution_contracts(payload_contracts: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    execution_contracts = payload_contracts.get("execution_contracts") or []
    if not isinstance(execution_contracts, list) or not execution_contracts:
        return lines

    if not lines:
        lines.extend(["Connector contract plan:", ""])
    lines.append("Execution-side contracts:")
    for contract in execution_contracts:
        if not isinstance(contract, dict):
            continue
        step_id = _stringify(contract.get("step_id")) or "step"
        intent_stage = _stringify(contract.get("intent_stage")) or "unknown"
        position_effect = _stringify(contract.get("position_effect")) or "unknown"
        lines.append(
            f"- {step_id}: stage={intent_stage}, position_effect={position_effect}"
        )
        lookup_contract = contract.get("lookup_contract") or {}
        review_contract = contract.get("review_contract") or {}
        submit_contract = contract.get("submit_contract") or {}
        if isinstance(lookup_contract, dict):
            lines.extend(_render_lookup_contract(lookup_contract))
        if isinstance(review_contract, dict):
            lines.extend(_render_action_contract("review phase", review_contract))
        if isinstance(submit_contract, dict):
            lines.extend(_render_action_contract("submit phase", submit_contract))
    return lines


def render_payload_contracts_section(broker_payload: dict[str, Any]) -> str:
    """Render broker payload contracts into readable prompt prose."""
    if not isinstance(broker_payload, dict):
        return ""
    payload_contracts = broker_payload.get("payload_contracts") or {}
    if not isinstance(payload_contracts, dict) or not payload_contracts:
        return ""

    lines: list[str] = []
    read_lines = _render_read_contracts(payload_contracts)
    execution_lines = _render_execution_contracts(payload_contracts)

    if (
        read_lines
        and execution_lines
        and execution_lines[:2] == ["Connector contract plan:", ""]
    ):
        execution_lines = execution_lines[2:]
    lines.extend(read_lines or ["Connector contract plan:"])
    if lines and lines[-1] != "":
        lines.append("")
    lines.extend(execution_lines)
    return "\n".join(line for line in lines if line is not None).strip()


__all__ = ["render_payload_contracts_section"]
