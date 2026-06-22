"""Register DroidPuppy canonical-context tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .commands import context_command_help, handle_context_command
from .tooling import (
    droidpuppy_context_append_journal as context_append_journal_impl,
    droidpuppy_context_apply_packet as context_apply_packet_impl,
    droidpuppy_context_commit_workflow as context_commit_workflow_impl,
    droidpuppy_context_doctor as context_doctor_impl,
    droidpuppy_context_handshake as context_handshake_impl,
    droidpuppy_context_init as context_init_impl,
    droidpuppy_context_install_repo_governance as context_install_repo_governance_impl,
    droidpuppy_context_packet as context_packet_impl,
    droidpuppy_context_record as context_record_impl,
)

_DOCTOR = "droidpuppy_context_doctor"
_INIT = "droidpuppy_context_init"
_RECORD = "droidpuppy_context_record"
_PACKET = "droidpuppy_context_packet"
_APPEND_JOURNAL = "droidpuppy_context_append_journal"
_APPLY_PACKET = "droidpuppy_context_apply_packet"
_HANDSHAKE = "droidpuppy_context_handshake"
_COMMIT = "droidpuppy_context_commit_workflow"
_INSTALL_REPO_GOVERNANCE = "droidpuppy_context_install_repo_governance"


def register_droidpuppy_context_doctor(agent: Any) -> None:
    @agent.tool
    async def droidpuppy_context_doctor(
        context: RunContext, root: str = ""
    ) -> dict[str, Any]:
        del context
        return context_doctor_impl(root=root)


def register_droidpuppy_context_init(agent: Any) -> None:
    @agent.tool
    async def droidpuppy_context_init(
        context: RunContext,
        root: str = "",
        workflow_id: str = "default-workflow",
        operator: str = "operator",
        authority: str = "operator",
        title: str = "",
        overwrite: bool = False,
    ) -> dict[str, Any]:
        del context
        return context_init_impl(
            root=root,
            workflow_id=workflow_id,
            operator=operator,
            authority=authority,
            title=title,
            overwrite=overwrite,
        )


def register_droidpuppy_context_record(agent: Any) -> None:
    @agent.tool
    async def droidpuppy_context_record(
        context: RunContext,
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
        del context
        return context_record_impl(
            what=what,
            why=why,
            result=result,
            root=root,
            actor=actor,
            workflow_id=workflow_id,
            workflow_status=workflow_status,
            current_goal=current_goal,
            current_step=current_step,
            next_steps=next_steps,
            blockers=blockers,
            evidence_refs=evidence_refs,
            approved_actions=approved_actions,
            blocked_actions=blocked_actions,
            approval_status=approval_status,
            authority=authority,
        )


def register_droidpuppy_context_packet(agent: Any) -> None:
    @agent.tool
    async def droidpuppy_context_packet(
        context: RunContext,
        root: str = "",
        history_limit: int = 10,
    ) -> dict[str, Any]:
        del context
        return context_packet_impl(root=root, history_limit=history_limit)


def register_droidpuppy_context_append_journal(agent: Any) -> None:
    @agent.tool
    async def droidpuppy_context_append_journal(
        context: RunContext,
        what: str,
        why: str,
        result: str,
        root: str = "",
        actor: str = "operator",
        workflow_id: str = "",
        evidence_refs: list[str] | None = None,
        next_steps: list[str] | None = None,
    ) -> dict[str, Any]:
        del context
        return context_append_journal_impl(
            what=what,
            why=why,
            result=result,
            root=root,
            actor=actor,
            workflow_id=workflow_id,
            evidence_refs=evidence_refs,
            next_steps=next_steps,
        )


def register_droidpuppy_context_apply_packet(agent: Any) -> None:
    @agent.tool
    async def droidpuppy_context_apply_packet(
        context: RunContext,
        root: str = "",
        workflow_state_json: str = "",
        execution_plan_json: str = "",
        approval_decision_json: str = "",
        journal_json: str = "",
    ) -> dict[str, Any]:
        del context
        return context_apply_packet_impl(
            root=root,
            workflow_state_json=workflow_state_json,
            execution_plan_json=execution_plan_json,
            approval_decision_json=approval_decision_json,
            journal_json=journal_json,
        )


def register_droidpuppy_context_handshake(agent: Any) -> None:
    @agent.tool
    async def droidpuppy_context_handshake(
        context: RunContext,
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
        del context
        return context_handshake_impl(
            raw_request=raw_request,
            root=root,
            workflow_id=workflow_id,
            requester=requester,
            intent_summary=intent_summary,
            requested_capabilities=requested_capabilities,
            constraints=constraints,
            target_surface=target_surface,
            risk_tier=risk_tier,
        )


def register_droidpuppy_context_commit_workflow(agent: Any) -> None:
    @agent.tool
    async def droidpuppy_context_commit_workflow(
        context: RunContext,
        root: str = "",
        workflow_id: str = "",
        committed_by: str = "operator",
        commit_message: str = "",
    ) -> dict[str, Any]:
        del context
        return context_commit_workflow_impl(
            root=root,
            workflow_id=workflow_id,
            committed_by=committed_by,
            commit_message=commit_message,
        )


def register_droidpuppy_context_install_repo_governance(agent: Any) -> None:
    @agent.tool
    async def droidpuppy_context_install_repo_governance(
        context: RunContext,
        target_root: str = "",
        overwrite: bool = False,
        include_readme: bool = True,
    ) -> dict[str, Any]:
        del context
        return context_install_repo_governance_impl(
            target_root=target_root,
            overwrite=overwrite,
            include_readme=include_readme,
        )


def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _DOCTOR, "register_func": register_droidpuppy_context_doctor},
        {"name": _INIT, "register_func": register_droidpuppy_context_init},
        {"name": _RECORD, "register_func": register_droidpuppy_context_record},
        {"name": _PACKET, "register_func": register_droidpuppy_context_packet},
        {
            "name": _APPEND_JOURNAL,
            "register_func": register_droidpuppy_context_append_journal,
        },
        {
            "name": _APPLY_PACKET,
            "register_func": register_droidpuppy_context_apply_packet,
        },
        {
            "name": _HANDSHAKE,
            "register_func": register_droidpuppy_context_handshake,
        },
        {
            "name": _COMMIT,
            "register_func": register_droidpuppy_context_commit_workflow,
        },
        {
            "name": _INSTALL_REPO_GOVERNANCE,
            "register_func": register_droidpuppy_context_install_repo_governance,
        },
    ]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    allowed_agents = {
        "code-puppy",
        "workflow-state",
        "execution-plan",
        "lease-request",
        "approval-decision",
        "workflow-commit",
        "lease-audit",
        "journal-audit",
        "governance-orchestrator",
    }
    if agent_name not in allowed_agents:
        return []
    return [
        _DOCTOR,
        _INIT,
        _RECORD,
        _PACKET,
        _APPEND_JOURNAL,
        _APPLY_PACKET,
        _HANDSHAKE,
        _COMMIT,
        _INSTALL_REPO_GOVERNANCE,
    ]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
register_callback("custom_command_help", context_command_help)
register_callback("custom_command", handle_context_command)
