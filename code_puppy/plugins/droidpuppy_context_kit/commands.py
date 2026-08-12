"""Slash commands for governed workflow capture, orchestration, and commit."""

from __future__ import annotations

import logging
from typing import Any, List, Optional, Tuple

from code_puppy.messaging import emit_info

logger = logging.getLogger(__name__)

_COMMIT_COMMAND_NAME = "workflow-commit"
_COMMIT_COMMAND_ALIAS = "wcommit"
_GOVERN_COMMAND_NAME = "govern"
_GOVERN_COMMAND_ALIAS = "workflow"
_COMMIT_COMMAND_NAMES = {_COMMIT_COMMAND_NAME, _COMMIT_COMMAND_ALIAS}
_GOVERN_COMMAND_NAMES = {_GOVERN_COMMAND_NAME, _GOVERN_COMMAND_ALIAS}
_COMMAND_NAMES = _COMMIT_COMMAND_NAMES | _GOVERN_COMMAND_NAMES


def context_command_help() -> List[Tuple[str, str]]:
    commit_description = (
        "Capture a governed handshake, run the commit workflow, and summarize "
        "approval/commit status. Alias: /wcommit"
    )
    govern_description = (
        "Capture a workflow prompt, prefer the committed fast path, and mint any "
        "approved workflow lease. Alias: /workflow"
    )
    return [
        (_COMMIT_COMMAND_NAME, commit_description),
        (_COMMIT_COMMAND_ALIAS, commit_description),
        (_GOVERN_COMMAND_NAME, govern_description),
        (_GOVERN_COMMAND_ALIAS, govern_description),
    ]


def _request_block(args: str, *, mode: str) -> str:
    if args:
        if mode == "govern":
            return f"User request to govern this workflow:\n{args}"
        return f"User request to govern and commit:\n{args}"
    if mode == "govern":
        return (
            "No extra request text was provided. Inspect the current canonical "
            "context packet, prefer the committed fast path if eligible, and mint "
            "a workflow lease only if approval_decision already supports it."
        )
    return (
        "No extra request text was provided. Inspect the current canonical "
        "context packet and attempt to commit the active workflow if it is coherent."
    )


def _build_prompt(args: str, *, mode: str) -> str:
    requirements = [
        "1. Read the canonical context packet first.",
        "2. Prefer invoke_agent with governance-orchestrator so the governed chain stays explicit; if only the receipt needs refreshing, use workflow-commit.",
        "3. For /govern, call droidpuppy_context_fast_path_status first. If it says eligible, skip workflow-state/execution-plan/approval fanout and go straight to authority_gateway_grant_workflow_lease, then execute and audit.",
        "4. If the fast path is not eligible, and the intent handshake is missing or stale, record it with droidpuppy_context_handshake.",
        "5. If the fast path is not eligible, establish or refresh workflow_state, execution_plan, and approval_decision honestly.",
        "6. If the chain shapes or mints a lease, default it to the stable authority principal instead of ephemeral agent/run ids; keep requested/delegated actor metadata separate.",
        "7. If approval_decision is ready and includes a lease_request, mint the lease with authority_gateway_grant_workflow_lease instead of retyping lease fields from the transcript.",
        "8. Create or refresh the durable workflow commit receipt with droidpuppy_context_commit_workflow when appropriate.",
        "9. Never treat workflow_commit as authority; approval_decision remains the only authoritative permission object.",
        "10. Summarize the resulting workflow_id, handshake_status, approval_status, commit_status, lease_status, blockers, and next steps.",
    ]
    intro = (
        "Run the governed workflow orchestration flow for this repo, preferring the committed fast path before any full governance fanout."
        if mode == "govern"
        else "Run the governed workflow commit flow for this repo."
    )
    return "\n".join(
        [intro, "", "Requirements:", *requirements, "", _request_block(args, mode=mode)]
    )


def handle_context_command(command: str, name: str) -> Optional[Any]:
    if name not in _COMMAND_NAMES:
        return None

    try:
        from code_puppy.plugins.customizable_commands.register_callbacks import (
            MarkdownCommandResult,
        )
    except ImportError:
        logger.debug(
            "MarkdownCommandResult unavailable; cannot run governed workflow slash"
        )
        return None

    parts = command.split(maxsplit=1)
    args = parts[1].strip() if len(parts) > 1 else ""
    mode = "govern" if name in _GOVERN_COMMAND_NAMES else "commit"
    emit_info(
        "Running governed workflow orchestration flow"
        if mode == "govern"
        else "Running governed workflow commit flow"
    )
    return MarkdownCommandResult(_build_prompt(args, mode=mode))
