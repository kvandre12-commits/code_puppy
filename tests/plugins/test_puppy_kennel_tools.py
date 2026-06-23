"""Tests for the full puppy_kennel tool surface.

Covers ``kennel_remember``, ``kennel_recent``, ``kennel_list_wings``,
``kennel_stats``, ``kennel_inventory``, plus the shared wing/scope
resolution helpers.
The original ``kennel_recall`` tests live in ``test_puppy_kennel_phase2``.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


@pytest.fixture
def kennel_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Throwaway kennel dir, isolated per test."""
    root = tmp_path / "kennel"
    monkeypatch.setenv("PUPPY_KENNEL_ROOT", str(root))

    import importlib

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
    importlib.reload(tools_mod)
    kennel_mod.initialize()
    return root


class _FakeAgent:
    """Captures @agent.tool-decorated functions for direct invocation."""

    def __init__(self) -> None:
        self.registered: dict[str, Any] = {}

    def tool(self, fn):
        self.registered[fn.__name__] = fn
        return fn


def _ctx(agent_name: str = "code-puppy") -> Any:
    return SimpleNamespace(agent_name=agent_name, deps=None)


# --------------------------------------------------------------------------- #
# Wing/scope resolution helpers
# --------------------------------------------------------------------------- #


def test_resolve_wing_shortcuts(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import tool_helpers

    cwd = Path.cwd()
    # Phase 5: blank default now routes to repo, not agent.
    assert tool_helpers.resolve_wing("", "code-puppy", cwd).startswith("repo:")
    assert tool_helpers.resolve_wing("repo", "code-puppy", cwd).startswith("repo:")
    assert tool_helpers.resolve_wing("agent", "code-puppy", cwd) == "agent:code-puppy"
    assert tool_helpers.resolve_wing("user", "code-puppy", cwd) == "user:default"
    assert tool_helpers.resolve_wing("custom:name", "code-puppy", cwd) == "custom:name"


def test_resolve_scope_combinations(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import tool_helpers

    cwd = Path.cwd()
    # Explicit wing wins over scope.
    assert tool_helpers.resolve_scope("user", "repo", "a", cwd) == ["user:default"]
    # scope='all' returns empty list (no filter)
    assert tool_helpers.resolve_scope("", "all", "a", cwd) == []
    # scope='default' returns three-wing set
    assert len(tool_helpers.resolve_scope("", "default", "a", cwd)) == 3
    # scope='user' single wing
    assert tool_helpers.resolve_scope("", "user", "a", cwd) == ["user:default"]


# --------------------------------------------------------------------------- #
# kennel_remember
# --------------------------------------------------------------------------- #


def test_kennel_remember_writes_to_repo_wing_by_default(kennel_root: Path) -> None:
    """Phase 5: default wing flipped from 'agent' to 'repo'.

    Project-scoped notes are by far the most common use case for
    ``kennel_remember``, so the default should match.
    """
    from code_puppy.plugins.puppy_kennel import kennel, tools

    agent = _FakeAgent()
    tools.register_kennel_remember(agent)
    remember = agent.registered["kennel_remember"]

    out = asyncio.run(remember(_ctx(), "Quagga is an extinct subspecies of zebra."))
    assert out.error is None
    assert out.drawer_id > 0
    assert out.wing.startswith("repo:")
    assert out.room == "notes"
    assert out.bytes_stored > 0
    assert kennel.count_drawers() == 1


def test_kennel_remember_wing_shortcuts(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import tools

    agent = _FakeAgent()
    tools.register_kennel_remember(agent)
    remember = agent.registered["kennel_remember"]

    out_user = asyncio.run(
        remember(
            _ctx(), "Mike prefers vim keybindings.", wing="user", room="preferences"
        )
    )
    assert out_user.wing == "user:default"
    assert out_user.room == "preferences"

    out_repo = asyncio.run(remember(_ctx(), "Auth uses JWT.", wing="repo"))
    assert out_repo.wing.startswith("repo:")


def test_kennel_remember_explicit_wing_passes_through(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import tools

    agent = _FakeAgent()
    tools.register_kennel_remember(agent)
    remember = agent.registered["kennel_remember"]

    out = asyncio.run(remember(_ctx(), "Custom note.", wing="team:platform"))
    assert out.wing == "team:platform"


def test_kennel_remember_empty_content_returns_error(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import kennel, tools

    agent = _FakeAgent()
    tools.register_kennel_remember(agent)
    remember = agent.registered["kennel_remember"]

    out = asyncio.run(remember(_ctx(), ""))
    assert out.error is not None
    assert out.drawer_id == 0
    assert kennel.count_drawers() == 0


def test_kennel_remember_blank_room_falls_back_to_notes(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import tools

    agent = _FakeAgent()
    tools.register_kennel_remember(agent)
    remember = agent.registered["kennel_remember"]

    out = asyncio.run(remember(_ctx(), "Hello.", room="   "))
    assert out.error is None


# --------------------------------------------------------------------------- #
# structured checkpoint capture
# --------------------------------------------------------------------------- #


def test_kennel_capture_decision_writes_structured_decision_note(
    kennel_root: Path,
) -> None:
    from code_puppy.plugins.puppy_kennel import kennel, tools

    agent = _FakeAgent()
    tools.register_kennel_capture_decision(agent)
    capture = agent.registered["kennel_capture_decision"]

    out = asyncio.run(
        capture(
            _ctx(),
            what="Switched governance agents to canonical context packet writes.",
            why="Transcript-only context was losing durable state and approval seams.",
            evidence="Validated with packet tests + fresh orchestration run.",
            outcome="Future sessions can recover plan/state/approval directly.",
            follow_up="Promote packet bootstrap helper next.",
            who="code-puppy",
            when="2026-06-22T17:45:00Z",
        )
    )

    assert out.error is None
    assert out.drawer_id > 0
    assert out.room == "decisions"
    assert out.capture_kind == "decision_checkpoint"
    hits = kennel.search_drawers("canonical context packet", limit=5)
    assert len(hits) == 1
    content = hits[0].content
    assert "When: 2026-06-22T17:45:00Z" in content
    assert "Who: code-puppy" in content
    assert (
        "What: Switched governance agents to canonical context packet writes."
        in content
    )
    assert (
        "Why: Transcript-only context was losing durable state and approval seams."
        in content
    )
    assert "Evidence: Validated with packet tests + fresh orchestration run." in content
    assert (
        "Outcome: Future sessions can recover plan/state/approval directly." in content
    )
    assert "Follow-up: Promote packet bootstrap helper next." in content


def test_kennel_capture_decision_requires_what_and_why(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import kennel, tools

    agent = _FakeAgent()
    tools.register_kennel_capture_decision(agent)
    capture = agent.registered["kennel_capture_decision"]

    out_missing_what = asyncio.run(capture(_ctx(), what="", why="Because."))
    out_missing_why = asyncio.run(capture(_ctx(), what="Thing.", why="   "))

    assert out_missing_what.error is not None
    assert out_missing_why.error is not None
    assert kennel.count_drawers() == 0


# --------------------------------------------------------------------------- #
# kennel_recent
# --------------------------------------------------------------------------- #


def test_kennel_recent_returns_newest_first(kennel_root: Path) -> None:
    import time

    from code_puppy.plugins.puppy_kennel import recorder, tools

    recorder.record_run_end(
        agent_name="code-puppy",
        model_name="m",
        session_id="s1",
        success=True,
        response_text="First memory.",
    )
    time.sleep(1.01)  # Distinct timestamps (we store seconds-precision).
    recorder.record_run_end(
        agent_name="code-puppy",
        model_name="m",
        session_id="s2",
        success=True,
        response_text="Second memory.",
    )

    agent = _FakeAgent()
    tools.register_kennel_recent(agent)
    recent = agent.registered["kennel_recent"]

    out = asyncio.run(recent(_ctx(), top_k=5))
    assert out.total == 2
    assert out.drawers[0].content == "Second memory."
    assert out.drawers[1].content == "First memory."


def test_kennel_recent_scope_user(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import tools

    agent = _FakeAgent()
    tools.register_kennel_remember(agent)
    tools.register_kennel_recent(agent)
    remember = agent.registered["kennel_remember"]
    recent = agent.registered["kennel_recent"]

    asyncio.run(remember(_ctx(), "User pref A", wing="user"))
    asyncio.run(remember(_ctx(), "User pref B", wing="user"))
    asyncio.run(remember(_ctx(), "Agent diary entry", wing="agent"))

    out = asyncio.run(recent(_ctx(), scope="user"))
    assert out.wings_searched == ["user:default"]
    assert out.total == 2
    for d in out.drawers:
        assert d.content.startswith("User pref")


def test_kennel_recent_top_k_clamped(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import tools

    agent = _FakeAgent()
    tools.register_kennel_recent(agent)
    recent = agent.registered["kennel_recent"]

    out = asyncio.run(recent(_ctx(), top_k=9999))
    assert isinstance(out.drawers, list)


def test_kennel_recent_empty_kennel(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import tools

    agent = _FakeAgent()
    tools.register_kennel_recent(agent)
    recent = agent.registered["kennel_recent"]

    out = asyncio.run(recent(_ctx()))
    assert out.total == 0
    assert out.drawers == []


# --------------------------------------------------------------------------- #
# kennel_list_wings
# --------------------------------------------------------------------------- #


def test_list_wings_empty_kennel(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import tools

    agent = _FakeAgent()
    tools.register_kennel_list_wings(agent)
    fn = agent.registered["kennel_list_wings"]

    out = asyncio.run(fn(_ctx()))
    assert out.total_wings == 0
    assert out.wings == []


def test_list_wings_with_counts(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import recorder, tools

    recorder.record_run_end(
        agent_name="code-puppy",
        model_name="m",
        session_id="s1",
        success=True,
        response_text="hello",
    )
    agent = _FakeAgent()
    tools.register_kennel_list_wings(agent)
    fn = agent.registered["kennel_list_wings"]

    out = asyncio.run(fn(_ctx()))
    # Phase 5: single-write to repo wing only.
    assert out.total_wings == 1
    names = {w.name for w in out.wings}
    assert any(n.startswith("repo:") for n in names)
    assert "agent:code-puppy" not in names
    for w in out.wings:
        assert w.drawer_count == 1


# --------------------------------------------------------------------------- #
# kennel_stats
# --------------------------------------------------------------------------- #


def test_kennel_stats_basic(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import recorder, tools

    recorder.record_run_end(
        agent_name="code-puppy",
        model_name="m",
        success=True,
        response_text="x",
    )
    agent = _FakeAgent()
    tools.register_kennel_stats(agent)
    fn = agent.registered["kennel_stats"]

    out = asyncio.run(fn(_ctx()))
    assert out.error is None
    # Phase 5: single-write to repo wing only.
    assert out.total_drawers == 1
    assert out.total_wings == 1
    assert out.db_size_bytes > 0
    assert out.db_path.endswith("kennel.db")


# --------------------------------------------------------------------------- #
# kennel_inventory
# --------------------------------------------------------------------------- #


def test_kennel_inventory_summarizes_wings_and_rooms(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import recorder, tools

    agent = _FakeAgent()
    tools.register_kennel_remember(agent)
    tools.register_kennel_inventory(agent)
    remember = agent.registered["kennel_remember"]
    inventory = agent.registered["kennel_inventory"]

    recorder.record_run_end(
        agent_name="code-puppy",
        model_name="m",
        session_id="alpha-session",
        success=True,
        response_text="Repo memory one.",
    )
    recorder.record_run_end(
        agent_name="code-puppy",
        model_name="m",
        session_id="beta-session",
        success=True,
        response_text="Repo memory two.",
    )
    asyncio.run(
        remember(_ctx(), "Architecture decision.", wing="repo", room="decisions")
    )
    asyncio.run(
        remember(
            _ctx(), "User likes terse status notes.", wing="user", room="preferences"
        )
    )

    out = asyncio.run(inventory(_ctx(), scope="all", max_wings=10, max_rooms=10))
    assert out.error is None
    assert out.total_wings == 2
    assert out.total_rooms == 4
    wing_names = {w.name for w in out.wing_summaries}
    assert any(name.startswith("repo:") for name in wing_names)
    assert "user:default" in wing_names
    room_names = {(r.wing_name, r.room_name) for r in out.room_summaries}
    assert ("user:default", "preferences") in room_names
    assert any(room == "decisions" for _, room in room_names)


# --------------------------------------------------------------------------- #
# kennel_debug_echo
# --------------------------------------------------------------------------- #


def test_kennel_debug_echo_reports_drop_and_keep_rows(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import kennel, recorder, tools
    from code_puppy.plugins.puppy_kennel.wings import repo_wing

    repo = repo_wing()
    kennel.write_note(
        wing_name=repo,
        room_name="decisions",
        content=(
            "What: Canonical packet/object context won over transcript-only session slices for operator workflows.\n"
            "Why: Transcript context is too lossy and too implicit for downstream agents.\n"
            "Follow-up: Capture durable state in packet/object form."
        ),
        role="note",
    )
    recorder.record_run_end(
        agent_name="code-puppy",
        model_name="m",
        success=True,
        response_text=(
            "We backfilled the packet-first workflow context doctrine so transcript residue stops pretending to be durable state. "
            + " lorem ipsum" * 20
        ),
    )
    recorder.record_run_end(
        agent_name="code-puppy",
        model_name="m",
        success=True,
        response_text=(
            "Fresh unrelated context about adoption metrics and next validation steps. "
            + " lorem ipsum" * 20
        ),
    )

    agent = _FakeAgent()
    tools.register_kennel_debug_echo(agent)
    debug_echo = agent.registered["kennel_debug_echo"]

    dropped_only = asyncio.run(debug_echo(_ctx(), top_k=10, only_dropped=True))
    all_rows = asyncio.run(debug_echo(_ctx(), top_k=10, only_dropped=False))

    assert dropped_only.error is None
    assert dropped_only.only_dropped is True
    assert dropped_only.total == 1
    assert dropped_only.returned == 1
    assert dropped_only.rows[0].dropped is True
    assert dropped_only.rows[0].reason == "recap-marker-overlap"

    assert all_rows.error is None
    assert all_rows.only_dropped is False
    assert all_rows.total == 2
    assert all_rows.returned == 2
    assert any(row.dropped for row in all_rows.rows)
    assert any(not row.dropped for row in all_rows.rows)


# --------------------------------------------------------------------------- #
# register_tools_callback contract
# --------------------------------------------------------------------------- #


def test_register_tools_callback_exposes_full_surface() -> None:
    from code_puppy.plugins.puppy_kennel import tools

    specs = tools.register_tools_callback()
    names = {s["name"] for s in specs}
    assert names == {
        "kennel_recall",
        "kennel_remember",
        "kennel_recent",
        "kennel_list_wings",
        "kennel_stats",
        "kennel_inventory",
        "kennel_debug_echo",
        "kennel_capture_decision",
        "kennel_upsert_decision",
        "kennel_list_decisions",
        "kennel_get_decision",
        "kennel_get_active_decisions",
        "kennel_recent_hinges",
        "kennel_decisions_missing_follow_up",
        "kennel_doctrine_gaps",
    }
    for spec in specs:
        assert callable(spec["register_func"])
