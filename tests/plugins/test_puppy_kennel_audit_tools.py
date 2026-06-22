"""Tests for puppy_kennel audit-style tools."""

from __future__ import annotations

import asyncio
import importlib
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


@pytest.fixture
def kennel_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Throwaway kennel dir, isolated per test."""
    root = tmp_path / "kennel"
    monkeypatch.setenv("PUPPY_KENNEL_ROOT", str(root))

    from code_puppy.plugins.puppy_kennel import audit as audit_mod
    from code_puppy.plugins.puppy_kennel import capture as capture_mod
    from code_puppy.plugins.puppy_kennel import config as kennel_config
    from code_puppy.plugins.puppy_kennel import kennel as kennel_mod
    from code_puppy.plugins.puppy_kennel import state as state_mod
    from code_puppy.plugins.puppy_kennel import tool_helpers as helpers_mod
    from code_puppy.plugins.puppy_kennel import tools as tools_mod

    importlib.reload(kennel_config)
    importlib.reload(state_mod)
    importlib.reload(kennel_mod)
    importlib.reload(helpers_mod)
    importlib.reload(capture_mod)
    importlib.reload(audit_mod)
    importlib.reload(tools_mod)
    kennel_mod.initialize()
    return root


class _FakeAgent:
    def __init__(self) -> None:
        self.registered: dict[str, Any] = {}

    def tool(self, fn):
        self.registered[fn.__name__] = fn
        return fn


def _ctx(agent_name: str = "code-puppy") -> Any:
    return SimpleNamespace(agent_name=agent_name, deps=None)


def test_kennel_recent_hinges_returns_newest_structured_checkpoints(
    kennel_root: Path,
) -> None:
    from code_puppy.plugins.puppy_kennel import tools

    agent = _FakeAgent()
    tools.register_kennel_capture_decision(agent)
    tools.register_kennel_recent_hinges(agent)
    capture = agent.registered["kennel_capture_decision"]
    recent_hinges = agent.registered["kennel_recent_hinges"]

    asyncio.run(capture(_ctx(), what="First hinge.", why="Because one."))
    time.sleep(1.01)
    asyncio.run(
        capture(
            _ctx(),
            what="Second hinge.",
            why="Because two.",
            outcome="Validated.",
        )
    )

    out = asyncio.run(recent_hinges(_ctx(), top_k=5))
    assert out.error is None
    assert out.total == 2
    assert out.hinges[0].summary == "Second hinge."
    assert out.hinges[0].what == "Second hinge."
    assert out.hinges[0].why == "Because two."
    assert out.hinges[0].outcome == "Validated."
    assert out.hinges[0].capture_kind == "decision_checkpoint"
    assert out.hinges[1].summary == "First hinge."


def test_kennel_decisions_missing_follow_up_flags_structured_and_legacy_notes(
    kennel_root: Path,
) -> None:
    from code_puppy.plugins.puppy_kennel import tools

    agent = _FakeAgent()
    tools.register_kennel_capture_decision(agent)
    tools.register_kennel_remember(agent)
    tools.register_kennel_decisions_missing_follow_up(agent)
    capture = agent.registered["kennel_capture_decision"]
    remember = agent.registered["kennel_remember"]
    missing = agent.registered["kennel_decisions_missing_follow_up"]

    asyncio.run(
        capture(
            _ctx(),
            what="Needs next step.",
            why="Rationale captured, but no follow-up yet.",
        )
    )
    asyncio.run(
        capture(
            _ctx(),
            what="Already queued.",
            why="This one has a next move.",
            follow_up="Implement the helper next.",
        )
    )
    asyncio.run(
        remember(_ctx(), "Legacy decision note with no next step.", room="decisions")
    )

    out = asyncio.run(missing(_ctx(), top_k=10))
    assert out.error is None
    assert out.total == 2
    summaries = {item.summary for item in out.items}
    assert "Needs next step." in summaries
    assert "Legacy decision note with no next step." in summaries
    assert all("follow-up" in item.reason.lower() for item in out.items)


def test_kennel_doctrine_gaps_spots_session_heavy_repo_wings(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import recorder, tools

    agent = _FakeAgent()
    tools.register_kennel_capture_decision(agent)
    tools.register_kennel_doctrine_gaps(agent)
    capture = agent.registered["kennel_capture_decision"]
    doctrine_gaps = agent.registered["kennel_doctrine_gaps"]

    for idx in range(4):
        recorder.record_run_end(
            agent_name="code-puppy",
            model_name="m",
            session_id="alpha-session",
            success=True,
            response_text=f"Session memory {idx}.",
        )
    asyncio.run(
        capture(
            _ctx(),
            what="One doctrine note.",
            why="Enough to prove a ratio, not enough to keep up.",
        )
    )

    out = asyncio.run(doctrine_gaps(_ctx(), scope="all", min_session_drawers=2))
    assert out.error is None
    assert out.total_wings_analyzed == 1
    assert out.total_gaps == 1
    gap = out.gaps[0]
    assert gap.session_drawers == 4
    assert gap.session_rooms == 1
    assert gap.doctrine_drawers == 1
    assert gap.largest_session_room == "session-alpha"
    assert gap.largest_session_room_drawers == 4
    assert gap.coverage_ratio == 0.25
    assert gap.gap_score == 3
    assert "session" in gap.assessment.lower()
