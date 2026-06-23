"""Tests for Decision v0 in puppy_kennel."""

from __future__ import annotations

import asyncio
import importlib
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


@pytest.fixture
def kennel_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Throwaway kennel dir, isolated per test."""
    root = tmp_path / "kennel"
    monkeypatch.setenv("PUPPY_KENNEL_ROOT", str(root))

    from code_puppy.plugins.puppy_kennel import config as kennel_config
    from code_puppy.plugins.puppy_kennel import decisions as decisions_mod
    from code_puppy.plugins.puppy_kennel import kennel as kennel_mod
    from code_puppy.plugins.puppy_kennel import state as state_mod
    from code_puppy.plugins.puppy_kennel import tools as tools_mod

    importlib.reload(kennel_config)
    importlib.reload(state_mod)
    importlib.reload(kennel_mod)
    importlib.reload(decisions_mod)
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


def test_decision_v0_records_can_be_listed_and_filtered_by_repo(
    kennel_root: Path,
) -> None:
    from code_puppy.plugins.puppy_kennel import tools

    agent = _FakeAgent()
    tools.register_kennel_upsert_decision(agent)
    tools.register_kennel_list_decisions(agent)
    tools.register_kennel_get_decision(agent)
    tools.register_kennel_get_active_decisions(agent)

    upsert = agent.registered["kennel_upsert_decision"]
    list_decisions = agent.registered["kennel_list_decisions"]
    get_decision = agent.registered["kennel_get_decision"]
    active_decisions = agent.registered["kennel_get_active_decisions"]

    records = [
        {
            "id": "playwright-optional-on-android",
            "title": "Playwright Optional On Android",
            "status": "active",
            "confidence": "high",
            "summary": "Browser automation dependencies must remain optional.",
            "rationale": "Android/Termux environments cannot reliably assume Playwright.",
            "affected_repos": ["code_puppy", "DroidPuppy"],
            "evidence_artifact_ids": [
                "PR-483",
                "PR-494",
                "PR-496",
                "clean-install-logs",
            ],
        },
        {
            "id": "android-bootstrap-lean-dependency-set",
            "title": "Android Bootstrap Uses Lean Dependency Set",
            "status": "active",
            "confidence": "high",
            "summary": "Bootstrap installs should prefer the leanest viable dependency set.",
            "rationale": "Core Android bootstrap must degrade gracefully and avoid desktop-only assumptions.",
            "affected_repos": ["code_puppy", "DroidPuppy"],
            "evidence_artifact_ids": [
                "termux-bootstrap-branch",
                "bootstrap-validation-runs",
            ],
        },
        {
            "id": "authority-validation-before-lease-issue",
            "title": "Governed Execution Requires Authority Validation Before Lease Issue",
            "status": "active",
            "confidence": "high",
            "summary": "Authority validation must happen before execution leases are issued.",
            "rationale": "Governed execution is only meaningful if lease issuance is gated by authority checks.",
            "affected_repos": ["code_puppy"],
            "evidence_artifact_ids": [
                "authority-check-implementation",
                "runtime-tests",
            ],
        },
    ]

    for record in records:
        out = asyncio.run(upsert(_ctx(), **record))
        assert out.error is None
        assert out.created is True
        assert out.decision is not None
        assert out.decision.id == record["id"]

    listed = asyncio.run(list_decisions(_ctx()))
    assert listed.error is None
    assert listed.total == 3
    assert {decision.id for decision in listed.decisions} == {
        "playwright-optional-on-android",
        "android-bootstrap-lean-dependency-set",
        "authority-validation-before-lease-issue",
    }

    detail = asyncio.run(
        get_decision(_ctx(), decision_id="playwright-optional-on-android")
    )
    assert detail.error is None
    assert detail.decision is not None
    assert detail.decision.id == "playwright-optional-on-android"
    assert "Decision: Playwright Optional On Android" in detail.rendered
    assert "Evidence: PR-483 PR-494 PR-496 clean-install-logs" in detail.rendered
    assert "Affected Repos: code_puppy DroidPuppy" in detail.rendered

    code_puppy_active = asyncio.run(active_decisions(_ctx(), repo="code_puppy"))
    assert code_puppy_active.error is None
    assert code_puppy_active.total == 3

    droidpuppy_active = asyncio.run(active_decisions(_ctx(), repo="DroidPuppy"))
    assert droidpuppy_active.error is None
    assert droidpuppy_active.total == 2
    assert {decision.id for decision in droidpuppy_active.decisions} == {
        "playwright-optional-on-android",
        "android-bootstrap-lean-dependency-set",
    }


def test_upsert_existing_decision_updates_in_place(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import tools

    agent = _FakeAgent()
    tools.register_kennel_upsert_decision(agent)
    tools.register_kennel_list_decisions(agent)
    tools.register_kennel_get_active_decisions(agent)

    upsert = agent.registered["kennel_upsert_decision"]
    list_decisions = agent.registered["kennel_list_decisions"]
    active_decisions = agent.registered["kennel_get_active_decisions"]

    created = asyncio.run(
        upsert(
            _ctx(),
            id="browser-optional",
            title="Browser Dependencies Optional",
            status="active",
            confidence="high",
            summary="Keep browser dependencies optional.",
            rationale="Android installs need graceful degradation.",
            affected_repos=["code_puppy"],
            evidence_artifact_ids=["PR-494"],
        )
    )
    assert created.error is None
    assert created.created is True

    updated = asyncio.run(
        upsert(
            _ctx(),
            id="browser-optional",
            title="Browser Dependencies Optional",
            status="superseded",
            confidence="high",
            summary="This decision has been replaced.",
            rationale="A newer installation strategy superseded it.",
            affected_repos=["code_puppy"],
            evidence_artifact_ids=["PR-494", "PR-999"],
            superseded_by=["lean-bootstrap-v2"],
        )
    )
    assert updated.error is None
    assert updated.created is False
    assert updated.decision is not None
    assert updated.decision.status == "superseded"
    assert updated.decision.superseded_by == ["lean-bootstrap-v2"]

    listed = asyncio.run(list_decisions(_ctx()))
    assert listed.total == 1
    assert listed.decisions[0].summary == "This decision has been replaced."

    active = asyncio.run(active_decisions(_ctx(), repo="code_puppy"))
    assert active.error is None
    assert active.total == 0


def test_upsert_decision_rejects_invalid_status(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import tools

    agent = _FakeAgent()
    tools.register_kennel_upsert_decision(agent)
    upsert = agent.registered["kennel_upsert_decision"]

    out = asyncio.run(
        upsert(
            _ctx(),
            title="Bad Decision",
            rationale="Oops.",
            status="eternal",
        )
    )
    assert out.error is not None
    assert "Invalid status" in out.error
