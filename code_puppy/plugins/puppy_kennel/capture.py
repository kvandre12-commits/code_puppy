"""Structured checkpoint capture for puppy_kennel.

Turns the usual "we should remember this" moment into a consistent note shape
without making the agent hand-format every decision write.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic_ai import RunContext

from . import kennel
from .state import DISABLED_TOOL_ERROR, is_enabled
from .time_utils import now_iso
from .tool_helpers import agent_name_from_context, resolve_wing
from .wings import detect_cwd


class KennelCheckpointOutput(BaseModel):
    """Output for ``kennel_capture_decision``."""

    drawer_id: int
    wing: str
    room: str
    capture_kind: str
    bytes_stored: int
    timestamp: str
    error: str | None = None


def _render_checkpoint(
    *,
    timestamp: str,
    who: str,
    what: str,
    why: str,
    evidence: str,
    outcome: str,
    follow_up: str,
) -> str:
    lines = [
        f"When: {timestamp}",
        f"Who: {who or 'unknown'}",
        f"What: {what.strip()}",
        f"Why: {why.strip()}",
    ]
    if evidence.strip():
        lines.append(f"Evidence: {evidence.strip()}")
    if outcome.strip():
        lines.append(f"Outcome: {outcome.strip()}")
    if follow_up.strip():
        lines.append(f"Follow-up: {follow_up.strip()}")
    return "\n".join(lines)


def write_decision_checkpoint(
    *,
    agent_name: str,
    what: str,
    why: str,
    evidence: str = "",
    outcome: str = "",
    follow_up: str = "",
    who: str = "",
    when: str = "",
    wing: str = "repo",
    room: str = "decisions",
    cwd: Any | None = None,
) -> KennelCheckpointOutput:
    """Write a structured checkpoint for both tools and slash commands."""
    if not what or not what.strip():
        return KennelCheckpointOutput(
            drawer_id=0,
            wing="",
            room=room,
            capture_kind="decision_checkpoint",
            bytes_stored=0,
            timestamp=when or "",
            error="Empty 'what' — describe what changed or was decided.",
        )
    if not why or not why.strip():
        return KennelCheckpointOutput(
            drawer_id=0,
            wing="",
            room=room,
            capture_kind="decision_checkpoint",
            bytes_stored=0,
            timestamp=when or "",
            error="Empty 'why' — capture the rationale, not just the action.",
        )

    try:
        cwd = cwd or detect_cwd()
        timestamp = (when or "").strip() or now_iso()
        actor = (who or "").strip() or agent_name
        resolved_wing = resolve_wing(wing, agent_name, cwd)
        resolved_room = (room or "decisions").strip() or "decisions"
        content = _render_checkpoint(
            timestamp=timestamp,
            who=actor,
            what=what,
            why=why,
            evidence=evidence,
            outcome=outcome,
            follow_up=follow_up,
        )
        drawer_id = kennel.write_note(
            wing_name=resolved_wing,
            room_name=resolved_room,
            content=content,
            role="note",
            metadata={
                "agent": agent_name,
                "cwd": str(cwd),
                "explicit": True,
                "capture_kind": "decision_checkpoint",
                "actor": actor,
            },
        )
        return KennelCheckpointOutput(
            drawer_id=drawer_id,
            wing=resolved_wing,
            room=resolved_room,
            capture_kind="decision_checkpoint",
            bytes_stored=len(content.encode("utf-8")),
            timestamp=timestamp,
        )
    except Exception as exc:  # noqa: BLE001
        return KennelCheckpointOutput(
            drawer_id=0,
            wing=wing,
            room=room,
            capture_kind="decision_checkpoint",
            bytes_stored=0,
            timestamp=when or "",
            error=f"kennel_capture_decision failed: {exc!r}",
        )


def register_kennel_capture_decision(agent: Any) -> None:
    """Register a structured decision-checkpoint tool."""

    @agent.tool
    async def kennel_capture_decision(
        context: RunContext,
        what: str,
        why: str,
        evidence: str = "",
        outcome: str = "",
        follow_up: str = "",
        who: str = "",
        when: str = "",
        wing: str = "repo",
        room: str = "decisions",
    ) -> KennelCheckpointOutput:
        """Save a structured mid-stream checkpoint to the Puppy Kennel.

        Use this when you just learned something worth preserving and don't want
        it to vanish in the middle of the session. The tool writes a durable,
        searchable note with the practical fields future-you actually needs:
        who / what / when / why / evidence / outcome / follow-up.

        Defaults:
        - ``wing='repo'`` because most solved-problem memory is project-scoped
        - ``room='decisions'`` because the usual use case is a durable choice
        - ``when`` defaults to the current UTC timestamp
        - ``who`` defaults to the current agent name
        """
        if not is_enabled():
            return KennelCheckpointOutput(
                drawer_id=0,
                wing="",
                room=room,
                capture_kind="decision_checkpoint",
                bytes_stored=0,
                timestamp=when or "",
                error=DISABLED_TOOL_ERROR,
            )

        agent_name = agent_name_from_context(context)
        return write_decision_checkpoint(
            agent_name=agent_name,
            what=what,
            why=why,
            evidence=evidence,
            outcome=outcome,
            follow_up=follow_up,
            who=who,
            when=when,
            wing=wing,
            room=room,
        )
