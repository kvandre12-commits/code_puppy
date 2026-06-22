"""Slash commands for governed workflow capture and commit."""

from __future__ import annotations

import logging
from typing import Any, List, Optional, Tuple

from code_puppy.messaging import emit_info

logger = logging.getLogger(__name__)

_COMMAND_NAME = "workflow-commit"
_COMMAND_ALIAS = "wcommit"
_COMMAND_NAMES = {_COMMAND_NAME, _COMMAND_ALIAS}


def context_command_help() -> List[Tuple[str, str]]:
    description = (
        "Capture a governed handshake, run the commit workflow, and summarize "
        "approval/commit status. Alias: /wcommit"
    )
    return [(_COMMAND_NAME, description), (_COMMAND_ALIAS, description)]


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

    if args:
        request_block = f"User request to govern and commit:\n{args}"
    else:
        request_block = (
            "No extra request text was provided. Inspect the current canonical "
            "context packet and attempt to commit the active workflow if it is coherent."
        )

    prompt = "\n".join(
        [
            "Run the governed workflow commit flow for this repo.",
            "",
            "Requirements:",
            "1. Read the canonical context packet first.",
            "2. Prefer invoke_agent with governance-orchestrator so the governed chain stays explicit; if only the receipt needs refreshing, use workflow-commit.",
            "3. If the intent handshake is missing or stale, record it with droidpuppy_context_handshake.",
            "4. Establish or refresh workflow_state, execution_plan, and approval_decision honestly.",
            "5. If the chain shapes or mints a lease, default it to the stable authority principal instead of ephemeral agent/run ids; keep requested/delegated actor metadata separate.",
            "6. Create or refresh the durable workflow commit receipt with droidpuppy_context_commit_workflow when appropriate.",
            "7. Never treat workflow_commit as authority; approval_decision remains the only authoritative permission object.",
            "8. Summarize the resulting workflow_id, handshake_status, approval_status, commit_status, blockers, and next steps.",
            "",
            request_block,
        ]
    )

    emit_info("Running governed workflow commit flow")
    return MarkdownCommandResult(prompt)
