"""Audit-style agent tools for the puppy_kennel.

These tools help inspect whether durable memory structure is actually forming,
instead of forcing the operator to eyeball session crumbs and guess.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import RunContext

from . import kennel
from .state import DISABLED_TOOL_ERROR, is_enabled
from .tool_helpers import agent_name_from_context, coerce_bounded_int, resolve_scope
from .wings import detect_cwd

_DECISION_ROOM = "decisions"
_SESSION_PREFIX = "session-"
_DOCTRINE_ROOMS = {"decisions", "notes"}
_LEGACY_FOLLOW_UP_MARKERS = ("follow-up:", "next:", "todo:", "action:")


class KennelHingePoint(BaseModel):
    drawer_id: int
    wing_name: str
    room_name: str
    ts: str
    capture_kind: str
    summary: str
    what: str = ""
    why: str = ""
    outcome: str = ""
    follow_up: str = ""


class KennelRecentHingesOutput(BaseModel):
    wings_searched: list[str]
    total: int
    hinges: list[KennelHingePoint] = Field(default_factory=list)
    error: str | None = None


class KennelMissingFollowUpItem(BaseModel):
    drawer_id: int
    wing_name: str
    room_name: str
    ts: str
    summary: str
    reason: str
    what: str = ""
    why: str = ""


class KennelMissingFollowUpOutput(BaseModel):
    wings_searched: list[str]
    total: int
    items: list[KennelMissingFollowUpItem] = Field(default_factory=list)
    error: str | None = None


class KennelDoctrineGap(BaseModel):
    wing_name: str
    latest_ts: str | None = None
    session_drawers: int
    session_rooms: int
    doctrine_drawers: int
    doctrine_rooms: int
    largest_session_room: str
    largest_session_room_drawers: int
    coverage_ratio: float
    gap_score: int
    assessment: str


class KennelDoctrineGapsOutput(BaseModel):
    wings_searched: list[str]
    total_wings_analyzed: int
    total_gaps: int
    gaps: list[KennelDoctrineGap] = Field(default_factory=list)
    error: str | None = None


def _structured_value(content: str, label: str) -> str:
    prefix = f"{label}:"
    for line in content.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return ""


def _summary_for_content(content: str) -> str:
    what = _structured_value(content, "What")
    if what:
        return what
    for line in content.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:160]
    return ""


def _capture_kind(drawer: kennel.DrawerContext) -> str:
    metadata = drawer.metadata or {}
    kind = metadata.get("capture_kind")
    if kind:
        return str(kind)
    if drawer.room_name == _DECISION_ROOM:
        return "decision_note"
    return drawer.role or "unknown"


def _is_hinge_drawer(drawer: kennel.DrawerContext) -> bool:
    metadata = drawer.metadata or {}
    if metadata.get("capture_kind") == "decision_checkpoint":
        return True
    return drawer.room_name == _DECISION_ROOM and drawer.role == "note"


def _has_explicit_follow_up(content: str) -> bool:
    if _structured_value(content, "Follow-up"):
        return True
    lowered = content.lower()
    return any(marker in lowered for marker in _LEGACY_FOLLOW_UP_MARKERS)


def _hinge_to_model(drawer: kennel.DrawerContext) -> KennelHingePoint:
    return KennelHingePoint(
        drawer_id=drawer.id,
        wing_name=drawer.wing_name,
        room_name=drawer.room_name,
        ts=drawer.ts,
        capture_kind=_capture_kind(drawer),
        summary=_summary_for_content(drawer.content),
        what=_structured_value(drawer.content, "What"),
        why=_structured_value(drawer.content, "Why"),
        outcome=_structured_value(drawer.content, "Outcome"),
        follow_up=_structured_value(drawer.content, "Follow-up"),
    )


def _resolve_wings_for_audit(
    context: RunContext,
    wing: str,
    scope: str,
) -> list[str]:
    agent_name = agent_name_from_context(context)
    cwd = detect_cwd()
    return resolve_scope(wing, scope, agent_name, cwd)


def collect_recent_hinges(
    wing_names: list[str] | None = None,
    limit: int = 10,
) -> list[KennelHingePoint]:
    """Collect the newest durable hinge captures for commands or tools."""
    drawers = kennel.drawers_with_context(
        wing_names=wing_names or None,
        role="note",
    )
    return [_hinge_to_model(d) for d in drawers if _is_hinge_drawer(d)][:limit]


def register_kennel_recent_hinges(agent: Any) -> None:
    """Register ``kennel_recent_hinges`` — newest durable hinge captures."""

    @agent.tool
    async def kennel_recent_hinges(
        context: RunContext,
        wing: str = "",
        top_k: int = 10,
        scope: str = "default",
    ) -> KennelRecentHingesOutput:
        """List the newest hinge-point captures across the selected wings.

        Good for asking: what durable decisions actually got written down,
        instead of trying to reverse-engineer a whole session transcript.
        """
        if not is_enabled():
            return KennelRecentHingesOutput(
                wings_searched=[],
                total=0,
                error=DISABLED_TOOL_ERROR,
            )
        top_k = coerce_bounded_int(top_k, default=10, minimum=1, maximum=50)
        try:
            wings_to_search = _resolve_wings_for_audit(context, wing, scope)
            hinges = collect_recent_hinges(wings_to_search or None, limit=top_k)
            return KennelRecentHingesOutput(
                wings_searched=wings_to_search,
                total=len(hinges),
                hinges=hinges,
            )
        except Exception as exc:  # noqa: BLE001
            return KennelRecentHingesOutput(
                wings_searched=[],
                total=0,
                error=f"kennel_recent_hinges failed: {exc!r}",
            )


def collect_decisions_missing_follow_up(
    wing_names: list[str] | None = None,
    limit: int = 10,
) -> list[KennelMissingFollowUpItem]:
    """Collect decision captures that lack explicit next-step markers."""
    drawers = kennel.drawers_with_context(
        wing_names=wing_names or None,
        room_names=[_DECISION_ROOM],
        role="note",
    )
    items: list[KennelMissingFollowUpItem] = []
    for drawer in drawers:
        if not _is_hinge_drawer(drawer):
            continue
        if _has_explicit_follow_up(drawer.content):
            continue
        items.append(
            KennelMissingFollowUpItem(
                drawer_id=drawer.id,
                wing_name=drawer.wing_name,
                room_name=drawer.room_name,
                ts=drawer.ts,
                summary=_summary_for_content(drawer.content),
                reason="Decision note has no explicit follow-up trail.",
                what=_structured_value(drawer.content, "What"),
                why=_structured_value(drawer.content, "Why"),
            )
        )
        if len(items) >= limit:
            break
    return items


def register_kennel_decisions_missing_follow_up(agent: Any) -> None:
    """Register ``kennel_decisions_missing_follow_up`` audit tool."""

    @agent.tool
    async def kennel_decisions_missing_follow_up(
        context: RunContext,
        wing: str = "",
        top_k: int = 10,
        scope: str = "default",
    ) -> KennelMissingFollowUpOutput:
        """Find decision captures that lack an explicit follow-up trail.

        This is intentionally a little annoying: a decision without a next move
        is how good ideas get buried under new sessions.
        """
        if not is_enabled():
            return KennelMissingFollowUpOutput(
                wings_searched=[],
                total=0,
                error=DISABLED_TOOL_ERROR,
            )
        top_k = coerce_bounded_int(top_k, default=10, minimum=1, maximum=50)
        try:
            wings_to_search = _resolve_wings_for_audit(context, wing, scope)
            items = collect_decisions_missing_follow_up(
                wings_to_search or None, limit=top_k
            )
            return KennelMissingFollowUpOutput(
                wings_searched=wings_to_search,
                total=len(items),
                items=items,
            )
        except Exception as exc:  # noqa: BLE001
            return KennelMissingFollowUpOutput(
                wings_searched=[],
                total=0,
                error=f"kennel_decisions_missing_follow_up failed: {exc!r}",
            )


def _build_doctrine_gap(
    wing_name: str,
    drawers: list[kennel.DrawerContext],
) -> KennelDoctrineGap | None:
    session_drawers = [d for d in drawers if d.room_name.startswith(_SESSION_PREFIX)]
    if not session_drawers:
        return None

    doctrine_drawers = [
        d for d in drawers if d.role == "note" and d.room_name in _DOCTRINE_ROOMS
    ]
    session_counter = Counter(d.room_name for d in session_drawers)
    largest_room, largest_count = session_counter.most_common(1)[0]
    coverage_ratio = round(len(doctrine_drawers) / max(len(session_drawers), 1), 3)
    gap_score = len(session_drawers) - len(doctrine_drawers)

    if len(doctrine_drawers) == 0:
        assessment = "Pure session sprawl: no doctrine notes captured in this wing."
    elif coverage_ratio < 0.25:
        assessment = "Session-heavy wing with very thin doctrine capture."
    elif coverage_ratio < 0.5:
        assessment = "Session activity is outrunning durable doctrine capture."
    else:
        assessment = "Moderate doctrine coverage, but sessions still dominate volume."

    latest_ts = max((d.ts for d in drawers), default=None)
    return KennelDoctrineGap(
        wing_name=wing_name,
        latest_ts=latest_ts,
        session_drawers=len(session_drawers),
        session_rooms=len(session_counter),
        doctrine_drawers=len(doctrine_drawers),
        doctrine_rooms=len({d.room_name for d in doctrine_drawers}),
        largest_session_room=largest_room,
        largest_session_room_drawers=largest_count,
        coverage_ratio=coverage_ratio,
        gap_score=gap_score,
        assessment=assessment,
    )


def collect_doctrine_gaps(
    wing_names: list[str] | None = None,
    limit: int = 10,
    min_session_drawers: int = 3,
) -> tuple[int, list[KennelDoctrineGap]]:
    """Collect session-heavy wings where doctrine capture is lagging."""
    drawers = kennel.drawers_with_context(wing_names=wing_names or None)
    by_wing: dict[str, list[kennel.DrawerContext]] = defaultdict(list)
    for drawer in drawers:
        by_wing[drawer.wing_name].append(drawer)

    analyzed = len(by_wing)
    gaps: list[KennelDoctrineGap] = []
    for wing_name, wing_drawers in by_wing.items():
        gap = _build_doctrine_gap(wing_name, wing_drawers)
        if gap is None:
            continue
        if gap.session_drawers < min_session_drawers:
            continue
        if gap.doctrine_drawers >= gap.session_drawers and gap.coverage_ratio >= 1:
            continue
        gaps.append(gap)

    gaps.sort(
        key=lambda g: (
            g.gap_score,
            g.session_drawers,
            -g.coverage_ratio,
            g.wing_name,
        ),
        reverse=True,
    )
    return analyzed, gaps[:limit]


def register_kennel_doctrine_gaps(agent: Any) -> None:
    """Register ``kennel_doctrine_gaps`` — session-sprawl audit."""

    @agent.tool
    async def kennel_doctrine_gaps(
        context: RunContext,
        wing: str = "",
        top_k: int = 10,
        scope: str = "all",
        min_session_drawers: int = 3,
    ) -> KennelDoctrineGapsOutput:
        """Find session-heavy wings where durable doctrine capture looks thin.

        This answers the question: where are we stockpiling transcript residue
        faster than we are distilling decisions, notes, and reusable doctrine?
        """
        if not is_enabled():
            return KennelDoctrineGapsOutput(
                wings_searched=[],
                total_wings_analyzed=0,
                total_gaps=0,
                error=DISABLED_TOOL_ERROR,
            )
        top_k = coerce_bounded_int(top_k, default=10, minimum=1, maximum=50)
        min_session_drawers = coerce_bounded_int(
            min_session_drawers,
            default=3,
            minimum=1,
            maximum=1000,
        )
        try:
            wings_to_search = _resolve_wings_for_audit(context, wing, scope)
            analyzed, gaps = collect_doctrine_gaps(
                wings_to_search or None,
                limit=top_k,
                min_session_drawers=min_session_drawers,
            )
            return KennelDoctrineGapsOutput(
                wings_searched=wings_to_search,
                total_wings_analyzed=analyzed,
                total_gaps=len(gaps),
                gaps=gaps,
            )
        except Exception as exc:  # noqa: BLE001
            return KennelDoctrineGapsOutput(
                wings_searched=[],
                total_wings_analyzed=0,
                total_gaps=0,
                error=f"kennel_doctrine_gaps failed: {exc!r}",
            )
