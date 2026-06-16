"""Register ChatGPT Robinhood delegation tools.

This plugin gives agents a truthful handoff path for Robinhood work:
prepare a structured request for ChatGPT's existing Robinhood connector,
instead of pretending Code Puppy can directly drive that connector today.
"""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    DEFAULT_ARTIFACT_NAME,
    ChatGPTRobinhoodDelegationOutput,
    build_delegation_packet,
    build_delegation_prompt,
    detect_chatgpt_oauth,
    write_delegation_artifacts,
)

_TOOL_NAME = "chatgpt_robinhood_delegate"


def register_chatgpt_robinhood_delegate(agent: Any) -> None:
    """Register the ChatGPT Robinhood handoff tool on an agent."""

    @agent.tool
    async def chatgpt_robinhood_delegate(
        context: RunContext,
        task_type: str,
        objective: str,
        required_result: str = "",
        broker_payload_json: str = "",
        supporting_context: str = "",
        constraints: str = "",
        risk_notes: str = "",
        approval_policy: str = "operator_confirm_required",
        artifact_name: str = DEFAULT_ARTIFACT_NAME,
    ) -> ChatGPTRobinhoodDelegationOutput:
        """Prepare a Robinhood delegation handoff for ChatGPT's connector.

        Use this when you want ChatGPT's already-configured Robinhood connector
        to do the broker-side work instead of building local Robinhood OAuth
        into Code Puppy.

        Important:
        - This tool does NOT execute Robinhood actions directly.
        - It writes JSON and text artifacts for a downstream ChatGPT session.
        - Live-order style tasks remain approval-gated.

        Args:
            task_type: One of account_read / market_data / order_draft /
                order_submit / order_cancel / order_replace / other.
            objective: Plain-English goal for the Robinhood action.
            required_result: What the downstream ChatGPT session should return.
            broker_payload_json: Optional JSON object with symbols, side,
                quantity, option legs, limit prices, etc.
            supporting_context: Optional narrative context from the agent.
            constraints: Optional execution constraints or guardrails.
            risk_notes: Optional risk disclosures or cautions.
            approval_policy: Safety posture. Write-style tasks are forced to
                operator_confirm_required.
            artifact_name: Basename for outputs/<name>.json and .txt.
        """
        del context  # Reserved for future context-aware routing.
        packet, warnings = build_delegation_packet(
            task_type=task_type,
            objective=objective,
            required_result=required_result,
            broker_payload_json=broker_payload_json,
            supporting_context=supporting_context,
            constraints=constraints,
            risk_notes=risk_notes,
            approval_policy=approval_policy,
        )
        prompt_text = build_delegation_prompt(packet)
        json_path, text_path = write_delegation_artifacts(
            packet,
            prompt_text,
            artifact_name=artifact_name,
        )
        return ChatGPTRobinhoodDelegationOutput(
            status="prepared",
            delegation_mode=packet["delegation_mode"],
            connector_target=packet["connector_target"],
            direct_connector_access_supported=packet[
                "direct_connector_access_supported"
            ],
            task_type=packet["task_type"],
            objective=packet["objective"],
            approval_policy=packet["approval_policy"],
            handoff_json_path=str(json_path),
            handoff_text_path=str(text_path),
            chatgpt_oauth_detected=detect_chatgpt_oauth(),
            delegation_prompt=prompt_text,
            warnings=warnings,
        )


def register_tools_callback() -> list[dict[str, Any]]:
    """Expose the plugin tool through the callback registry."""
    return [{"name": _TOOL_NAME, "register_func": register_chatgpt_robinhood_delegate}]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_TOOL_NAME]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
