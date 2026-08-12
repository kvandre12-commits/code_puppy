"""Register ChatGPT Robinhood delegation tools.

This plugin gives agents a truthful handoff path for Robinhood work:
prepare a structured request for ChatGPT's existing Robinhood connector,
instead of pretending Code Puppy can directly drive that connector today.
"""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .audit import (
    DEFAULT_AUDIT_ARTIFACT_NAME,
    ChatGPTRobinhoodAuditOutput,
    ingest_connector_audit,
)
from .loop import (
    DEFAULT_LOOP_ARTIFACT_NAME,
    ChatGPTRobinhoodLoopOutput,
    finish_delegation_loop,
    get_delegation_loop_status,
    start_delegation_loop,
)
from .tooling import (
    DEFAULT_ARTIFACT_NAME,
    DEFAULT_BRIDGE_ARTIFACT_NAME,
    DEFAULT_BRIDGE_HANDOFF_NAME,
    DEFAULT_BRIDGE_HANDOFF_PATH,
    DEFAULT_BRIDGE_REPO_ROOT,
    ChatGPTRobinhoodDelegationOutput,
    build_delegation_packet,
    build_delegation_prompt,
    detect_chatgpt_oauth,
    prepare_delegation_from_bridge_handoff,
    prepare_delegation_from_signal,
    write_delegation_artifacts,
)

_TOOL_NAME = "chatgpt_robinhood_delegate"
_BRIDGE_TOOL_NAME = "chatgpt_robinhood_delegate_from_handoff"
_SIGNAL_TOOL_NAME = "chatgpt_robinhood_delegate_from_signal"
_AUDIT_TOOL_NAME = "chatgpt_robinhood_audit_ingest"
_LOOP_TOOL_NAME = "chatgpt_robinhood_loop"


def register_chatgpt_robinhood_delegate(agent: Any) -> None:
    """Register the base ChatGPT Robinhood delegation tool."""

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


def register_chatgpt_robinhood_delegate_from_handoff(agent: Any) -> None:
    """Register the bridge-handoff packaging tool."""

    @agent.tool
    async def chatgpt_robinhood_delegate_from_handoff(
        context: RunContext,
        handoff_path: str = DEFAULT_BRIDGE_HANDOFF_PATH,
        artifact_name: str = DEFAULT_BRIDGE_ARTIFACT_NAME,
        required_result: str = "",
        objective: str = "",
        supporting_context: str = "",
        constraints: str = "",
        risk_notes: str = "",
    ) -> ChatGPTRobinhoodDelegationOutput:
        """Package a SharpEdge bridge handoff into ChatGPT Robinhood artifacts.

        Use this when SharpEdge-Robinhood-Bridge has already produced a
        ``sharpedge.robinhood_execution_handoff.v1`` file and you want Code
        Puppy to convert that approval-gated handoff directly into the normal
        ChatGPT delegation JSON + prompt artifacts.

        Important:
        - This tool does NOT execute Robinhood actions directly.
        - It refuses stand-down or non-approval-ready bridge handoffs.
        - Live-order style tasks remain approval-gated.

        Args:
            handoff_path: Path to the bridge handoff JSON. Defaults to the
                current SharpEdge bridge output path.
            artifact_name: Basename for outputs/<name>.json and .txt.
            required_result: Optional override for what ChatGPT should return.
            objective: Optional override for the generated objective.
            supporting_context: Optional extra context appended to the bridge
                summary.
            constraints: Optional extra constraints appended to the bridge
                constraints.
            risk_notes: Optional extra risk notes appended to the bridge risk
                summary.
        """
        del context
        return prepare_delegation_from_bridge_handoff(
            handoff_path=handoff_path,
            artifact_name=artifact_name,
            required_result=required_result,
            objective=objective,
            supporting_context=supporting_context,
            constraints=constraints,
            risk_notes=risk_notes,
        )


def register_chatgpt_robinhood_delegate_from_signal(agent: Any) -> None:
    """Register the signal-to-bridge-to-ChatGPT packaging tool."""

    @agent.tool
    async def chatgpt_robinhood_delegate_from_signal(
        context: RunContext,
        bridge_root: str = DEFAULT_BRIDGE_REPO_ROOT,
        signal_path: str = "",
        bridge_command_name: str = "order_submit",
        test: bool = False,
        handoff_output_dir: str = "",
        handoff_latest_name: str = DEFAULT_BRIDGE_HANDOFF_NAME,
        artifact_name: str = DEFAULT_BRIDGE_ARTIFACT_NAME,
        required_result: str = "",
        objective: str = "",
        supporting_context: str = "",
        constraints: str = "",
        risk_notes: str = "",
    ) -> ChatGPTRobinhoodDelegationOutput:
        """Run SharpEdge-Robinhood-Bridge signal-handoff, then package it for ChatGPT.

        Use this when you want a one-shot cockpit-to-connector prep flow:
        generate a fresh bridge handoff from the current cockpit signal, then
        convert that approval-gated handoff into the normal ChatGPT delegation
        JSON + prompt artifacts.

        Important:
        - This tool does NOT execute Robinhood actions directly.
        - It invokes the bridge CLI instead of re-implementing bridge logic.
        - It refuses bridge outputs that are stand-down or not approval-ready.

        Args:
            bridge_root: Path to the SharpEdge-Robinhood-Bridge repo root.
            signal_path: Optional path to a specific cockpit signal.json.
            bridge_command_name: Bridge command to plan, defaults to order_submit.
            test: If true, ask the bridge to force its test-mode handoff path.
            handoff_output_dir: Optional output directory for the bridge handoff.
            handoff_latest_name: Latest-name file for the bridge handoff artifact.
            artifact_name: Basename for outputs/<name>.json and .txt.
            required_result: Optional override for what ChatGPT should return.
            objective: Optional override for the generated objective.
            supporting_context: Optional extra context appended to the bridge
                summary.
            constraints: Optional extra constraints appended to the bridge
                constraints.
            risk_notes: Optional extra risk notes appended to the bridge risk
                summary.
        """
        del context
        return prepare_delegation_from_signal(
            bridge_root=bridge_root,
            signal_path=signal_path,
            bridge_command_name=bridge_command_name,
            test=test,
            handoff_output_dir=handoff_output_dir,
            handoff_latest_name=handoff_latest_name,
            artifact_name=artifact_name,
            required_result=required_result,
            objective=objective,
            supporting_context=supporting_context,
            constraints=constraints,
            risk_notes=risk_notes,
        )


def register_chatgpt_robinhood_audit_ingest(agent: Any) -> None:
    """Register the connector audit ingestion tool."""

    @agent.tool
    async def chatgpt_robinhood_audit_ingest(
        context: RunContext,
        response_text: str = "",
        response_json: str = "",
        response_file_path: str = "",
        handoff_path: str = "",
        artifact_name: str = DEFAULT_AUDIT_ARTIFACT_NAME,
        append_log: bool = True,
    ) -> ChatGPTRobinhoodAuditOutput:
        """Normalize a ChatGPT connector outcome into audit + journal artifacts.

        Use this after a downstream ChatGPT + Robinhood connector session has
        replied with what it observed, drafted, submitted, canceled, or blocked.
        The ingestor preserves what actually happened so SharpEdge can compare
        intent versus execution instead of relying on chat scroll archaeology.

        Important:
        - This tool does NOT execute Robinhood actions directly.
        - It accepts raw connector text, structured JSON, or a saved response file.
        - If you also provide a bridge handoff path, the audit is enriched with
          the original requested action and approval context.

        Args:
            response_text: Freeform connector response text.
            response_json: Structured connector response JSON object.
            response_file_path: Optional path to saved connector response text/JSON.
            handoff_path: Optional path to the originating bridge handoff JSON.
            artifact_name: Basename for outputs/<name>.json plus journal companions.
            append_log: Whether to append a summary line into the connector audit log.
        """
        del context
        return ingest_connector_audit(
            response_text=response_text,
            response_json=response_json,
            response_file_path=response_file_path,
            handoff_path=handoff_path,
            artifact_name=artifact_name,
            append_log=append_log,
        )


def register_chatgpt_robinhood_loop(agent: Any) -> None:
    """Register the two-phase delegation loop tool."""

    @agent.tool
    async def chatgpt_robinhood_loop(
        context: RunContext,
        action: str = "start",
        loop_json_path: str = "",
        artifact_name: str = DEFAULT_LOOP_ARTIFACT_NAME,
        handoff_path: str = "",
        bridge_root: str = DEFAULT_BRIDGE_REPO_ROOT,
        signal_path: str = "",
        bridge_command_name: str = "order_submit",
        test: bool = False,
        handoff_output_dir: str = "",
        handoff_latest_name: str = DEFAULT_BRIDGE_HANDOFF_NAME,
        required_result: str = "",
        objective: str = "",
        supporting_context: str = "",
        constraints: str = "",
        risk_notes: str = "",
        response_text: str = "",
        response_json: str = "",
        response_file_path: str = "",
        append_log: bool = True,
    ) -> ChatGPTRobinhoodLoopOutput:
        """Run a two-phase Robinhood delegation loop around the ChatGPT connector.

        Use ``action='start'`` to build bridge + delegation artifacts and persist
        a loop manifest. After the downstream ChatGPT connector session replies,
        use ``action='finish'`` with the connector response to ingest the result
        back into audit + journal artifacts tied to that same loop. You can also
        use ``action='status'`` to inspect the current loop manifest.

        Important:
        - This tool still does NOT execute Robinhood actions directly.
        - The loop is honest about the async boundary: start now, finish later.
        - Finish mode enriches the audit from the stored bridge handoff context.

        Args:
            action: ``start`` / ``finish`` / ``status``.
            loop_json_path: Path to a previously created loop manifest. Required
                for finish/status unless you rely on the derived artifact_name path.
            artifact_name: Base name for loop-related outputs.
            handoff_path: Optional existing bridge handoff for start mode.
            bridge_root: SharpEdge-Robinhood-Bridge repo root for start mode.
            signal_path: Optional specific signal.json for start mode.
            bridge_command_name: Bridge command to plan during start mode.
            test: Whether start mode should ask the bridge for a test handoff.
            handoff_output_dir: Optional bridge output dir for start mode.
            handoff_latest_name: Bridge latest-name handoff artifact.
            required_result: Optional override for connector return expectations.
            objective: Optional override for the generated objective.
            supporting_context: Optional extra context for delegation prep.
            constraints: Optional extra constraints for delegation prep.
            risk_notes: Optional extra risk notes for delegation prep.
            response_text: Connector response text for finish mode.
            response_json: Connector response JSON for finish mode.
            response_file_path: Saved connector response path for finish mode.
            append_log: Whether finish mode should append the audit log line.
        """
        del context
        normalized_action = (action or "start").strip().lower()
        if normalized_action == "start":
            return start_delegation_loop(
                artifact_name=artifact_name,
                handoff_path=handoff_path,
                bridge_root=bridge_root,
                signal_path=signal_path,
                bridge_command_name=bridge_command_name,
                test=test,
                handoff_output_dir=handoff_output_dir,
                handoff_latest_name=handoff_latest_name,
                required_result=required_result,
                objective=objective,
                supporting_context=supporting_context,
                constraints=constraints,
                risk_notes=risk_notes,
            )
        if normalized_action == "finish":
            resolved_loop_path = loop_json_path or f"outputs/{artifact_name}_loop.json"
            return finish_delegation_loop(
                loop_json_path=resolved_loop_path,
                response_text=response_text,
                response_json=response_json,
                response_file_path=response_file_path,
                append_log=append_log,
            )
        if normalized_action == "status":
            resolved_loop_path = loop_json_path or f"outputs/{artifact_name}_loop.json"
            return get_delegation_loop_status(loop_json_path=resolved_loop_path)
        raise ValueError("action must be one of: start, finish, status")


def register_tools_callback() -> list[dict[str, Any]]:
    """Expose the plugin tools through the callback registry."""
    return [
        {
            "name": _TOOL_NAME,
            "register_func": register_chatgpt_robinhood_delegate,
        },
        {
            "name": _BRIDGE_TOOL_NAME,
            "register_func": register_chatgpt_robinhood_delegate_from_handoff,
        },
        {
            "name": _SIGNAL_TOOL_NAME,
            "register_func": register_chatgpt_robinhood_delegate_from_signal,
        },
        {
            "name": _AUDIT_TOOL_NAME,
            "register_func": register_chatgpt_robinhood_audit_ingest,
        },
        {
            "name": _LOOP_TOOL_NAME,
            "register_func": register_chatgpt_robinhood_loop,
        },
    ]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [
        _TOOL_NAME,
        _BRIDGE_TOOL_NAME,
        _SIGNAL_TOOL_NAME,
        _AUDIT_TOOL_NAME,
        _LOOP_TOOL_NAME,
    ]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
