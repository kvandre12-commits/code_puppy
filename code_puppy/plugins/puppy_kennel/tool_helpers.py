"""Shared helpers for agent-facing puppy_kennel tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from .wings import (
    USER_WING,
    agent_wing,
    default_recall_scope,
    repo_wing,
)


def agent_name_from_context(context: RunContext) -> str:
    """Best-effort extraction of the calling agent's name from run context."""
    for attr in ("agent_name", "name"):
        val = getattr(context, attr, None)
        if val:
            return str(val)
    deps = getattr(context, "deps", None)
    if deps is not None:
        for attr in ("agent_name", "name"):
            val = getattr(deps, attr, None)
            if val:
                return str(val)
    return "unknown"


def resolve_wing(value: str, agent_name: str, cwd: Any) -> str:
    """Turn a wing shortcut into a concrete wing name."""
    v = (value or "").strip()
    if v == "" or v == "repo":
        return repo_wing(cwd)
    if v == "agent":
        return agent_wing(agent_name)
    if v == "user":
        return USER_WING
    return v


def resolve_scope(wing: str, scope: str, agent_name: str, cwd: Any) -> list[str]:
    """Turn (wing, scope) into the list of wings to search."""
    w = (wing or "").strip()
    if w:
        return [resolve_wing(w, agent_name, cwd)]
    if scope == "repo":
        return [repo_wing(cwd)]
    if scope == "agent":
        return [agent_wing(agent_name)]
    if scope == "user":
        return [USER_WING]
    if scope == "all":
        return []
    return default_recall_scope(agent_name, cwd)


def coerce_bounded_int(
    value: Any,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    """Best-effort int coercion with inclusive bounds and sane fallback."""
    try:
        return max(minimum, min(int(value), maximum))
    except (TypeError, ValueError):
        return default
