"""Recorder — captures agent runs into the kennel.

Fires on ``agent_run_end``. The recorder writes the agent's raw response to
**one** wing: the current repo wing, but only as transcript quarantine. The
autosave path treats every response as "conversation material that happened in
this project," not durable project memory.

Cross-project agent reflections belong in ``agent:<name>`` and are an
opt-in concern handled by the ``kennel_remember`` tool, not autosave.
User preferences likewise live in ``user:default`` and only land there
via explicit ``kennel_remember`` calls.

Capturing user input is a phase-2 concern that will hook ``stream_event``
instead.
"""

from __future__ import annotations

from typing import Any

from code_puppy.messaging.bus import emit_debug

from . import kennel
from .hygiene import autosave_decision
from .state import is_enabled
from .wings import detect_cwd, repo_wing


QUARANTINE_ROLE = "quarantine"
QUARANTINE_MEMORY_TYPE = "transcript_quarantine"


def _room_name(session_id: str | None) -> str:
    """Rooms partition quarantine by session. Keep the name human-scannable."""
    if not session_id:
        return "quarantine-session-unknown"
    short = session_id.split("-")[0][:12] if "-" in session_id else session_id[:12]
    return f"quarantine-session-{short}"


def record_run_end(
    agent_name: str,
    model_name: str,
    session_id: str | None = None,
    success: bool = True,
    error: Exception | None = None,
    response_text: str | None = None,
    metadata: dict | None = None,
) -> None:
    """Persist the agent's final response into transcript quarantine.

    Raw transcript can enter the kennel only as temporary quarantine. Durable
    project memory should be explicit typed notes: facts, decisions, artifacts,
    relationships, and history.

    Failures here must never crash the host app — the kennel is best-effort
    context capture, not a transactional system of record.
    """
    decision = autosave_decision(response_text or "")
    if not decision.should_store:
        emit_debug(f"[puppy_kennel] recorder skipped {decision.reason} response")
        return
    if not success:
        # Don't memorialize broken runs. The error log is the right place.
        return
    if not is_enabled():
        # Kennel context is toggled off — silently skip. Slash commands surface state.
        return

    try:
        cwd = detect_cwd()
        room = _room_name(session_id)
        drawer_meta: dict[str, Any] = {
            "agent": agent_name,
            "model": model_name,
            "cwd": str(cwd),
            "memory_type": QUARANTINE_MEMORY_TYPE,
            "durable": False,
        }
        if metadata:
            drawer_meta["run_metadata"] = metadata

        # Transcript quarantine — the only passive autosave destination.
        repo_w = repo_wing(cwd)
        if kennel.find_duplicate_drawer_id(
            response_text, wing_name=repo_w, role=QUARANTINE_ROLE
        ):
            emit_debug("[puppy_kennel] recorder skipped duplicate quarantine response")
            return
        repo_wing_id = kennel.ensure_wing(repo_w)
        repo_room_id = kennel.ensure_room(repo_wing_id, room)
        kennel.add_drawer(
            repo_room_id,
            content=response_text,
            role=QUARANTINE_ROLE,
            session_id=session_id,
            metadata=drawer_meta,
        )
    except Exception as exc:  # noqa: BLE001 — best-effort context capture.
        emit_debug(f"[puppy_kennel] recorder skipped: {exc!r}")
