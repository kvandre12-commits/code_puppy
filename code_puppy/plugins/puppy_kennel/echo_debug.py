"""Debug surface for inspecting kennel assistant de-echo decisions."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import RunContext

from . import packer
from .state import DISABLED_TOOL_ERROR, is_enabled
from .tool_helpers import coerce_bounded_int


class KennelEchoDebugRow(BaseModel):
    drawer_id: int
    agent: str | None = None
    ts: str
    dropped: bool
    reason: str
    exact_overlap_count: int
    token_overlap_count: int
    overlap_count: int
    has_recap_marker: bool
    matched_anchors: list[str] = Field(default_factory=list)
    matched_tokens: list[str] = Field(default_factory=list)
    preview: str


class KennelEchoDebugOutput(BaseModel):
    total: int
    returned: int
    only_dropped: bool
    rows: list[KennelEchoDebugRow] = Field(default_factory=list)
    error: str | None = None


def register_kennel_debug_echo(agent: Any) -> None:
    """Register ``kennel_debug_echo`` — inspect recall de-echo decisions."""

    @agent.tool
    async def kennel_debug_echo(
        context: RunContext,
        top_k: int = 10,
        only_dropped: bool = True,
    ) -> KennelEchoDebugOutput:
        """Inspect why recent assistant drawers were kept or dropped.

        Useful when tuning or auditing the packer's assistant de-echo heuristic.

        Args:
            top_k: Number of rows to return (1-50, default 10).
            only_dropped: If true, show only filtered drawers. If false, show
                both kept and dropped decisions.
        """
        del context  # unused; kept for consistent tool signature
        if not is_enabled():
            return KennelEchoDebugOutput(
                total=0,
                returned=0,
                only_dropped=bool(only_dropped),
                error=DISABLED_TOOL_ERROR,
            )
        top_k = coerce_bounded_int(top_k, default=10, minimum=1, maximum=50)
        try:
            rows = packer.debug_assistant_echo()
            if only_dropped:
                rows = [row for row in rows if bool(row.get("dropped"))]
            sliced = rows[:top_k]
            return KennelEchoDebugOutput(
                total=len(rows),
                returned=len(sliced),
                only_dropped=bool(only_dropped),
                rows=[KennelEchoDebugRow(**row) for row in sliced],
            )
        except Exception as exc:  # noqa: BLE001
            return KennelEchoDebugOutput(
                total=0,
                returned=0,
                only_dropped=bool(only_dropped),
                error=f"kennel_debug_echo failed: {exc!r}",
            )
