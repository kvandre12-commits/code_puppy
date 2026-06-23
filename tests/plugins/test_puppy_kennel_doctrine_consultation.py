"""Tests for mutation-time doctrine consultation in puppy_kennel."""

from __future__ import annotations

import asyncio
import importlib
from pathlib import Path

import pytest


@pytest.fixture
def doctrine_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, object, object, object]:
    """Isolated kennel + repo-family cwd for doctrine consultation tests."""
    root = tmp_path / "kennel"
    repo_root = tmp_path / "code_puppy_backup_20260617"
    repo_root.mkdir()
    monkeypatch.setenv("PUPPY_KENNEL_ROOT", str(root))
    monkeypatch.chdir(repo_root)

    from code_puppy.plugins.puppy_kennel import config as kennel_config
    from code_puppy.plugins.puppy_kennel import decisions as decisions_mod
    from code_puppy.plugins.puppy_kennel import doctrine_consultation as consult_mod
    from code_puppy.plugins.puppy_kennel import kennel as kennel_mod
    from code_puppy.plugins.puppy_kennel import register_callbacks as callbacks_mod
    from code_puppy.plugins.puppy_kennel import state as state_mod

    importlib.reload(kennel_config)
    importlib.reload(state_mod)
    importlib.reload(kennel_mod)
    importlib.reload(decisions_mod)
    importlib.reload(consult_mod)
    importlib.reload(callbacks_mod)
    kennel_mod.initialize()
    return repo_root, decisions_mod, consult_mod, callbacks_mod


def test_dependency_edit_surfaces_doctrine_warning_for_matching_package(
    doctrine_env: tuple[Path, object, object, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, decisions_mod, consult_mod, callbacks_mod = doctrine_env
    warnings: list[str] = []
    monkeypatch.setattr(consult_mod, "emit_warning", warnings.append)

    decisions_mod.upsert_decision(
        decisions_mod.DecisionRecord(
            id="playwright-optional-on-android",
            title="Playwright Optional On Android",
            status="active",
            confidence="high",
            summary="Browser automation dependencies stay optional.",
            rationale="Android/Termux environments cannot reliably assume Playwright.",
            affected_repos=["code_puppy"],
            evidence_artifact_ids=["PR-483", "PR-494", "PR-496"],
            created_at="",
            last_reviewed_at="",
            supersedes=[],
            superseded_by=[],
        )
    )

    tool_args = {
        "file_path": "pyproject.toml",
        "replacements": [
            {
                "old_str": 'dependencies = [\n    "rich>=13.0",\n]\n',
                "new_str": (
                    'dependencies = [\n    "rich>=13.0",\n    "playwright>=1.55",\n]\n'
                ),
            }
        ],
    }

    response = consult_mod.build_pre_tool_response("replace_in_file", tool_args)
    assert response is not None
    assert "context_message" in response
    message = response["context_message"]
    assert "[doctrine check] Potential conflict detected" in message
    assert "Target: pyproject.toml" in message
    assert "Proposed dependency signal: playwright" in message
    assert "Decision: Playwright Optional On Android" in message
    assert "Decision ID: playwright-optional-on-android" in message
    assert "Confidence: high" in message
    assert "Evidence: PR-483, PR-494, PR-496" in message
    assert "Drill-down: /kennel doctrine playwright-optional-on-android" in message
    assert (
        'kennel_get_decision(decision_id="playwright-optional-on-android")' in message
    )
    assert "warning only" in message
    assert warnings == [message]

    callback_response = asyncio.run(
        callbacks_mod._on_pre_tool_call("replace_in_file", tool_args)
    )
    assert callback_response == response


def test_non_conflicting_dependency_edit_returns_no_warning(
    doctrine_env: tuple[Path, object, object, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, decisions_mod, consult_mod, _ = doctrine_env
    warnings: list[str] = []
    monkeypatch.setattr(consult_mod, "emit_warning", warnings.append)

    decisions_mod.upsert_decision(
        decisions_mod.DecisionRecord(
            id="playwright-optional-on-android",
            title="Playwright Optional On Android",
            status="active",
            confidence="high",
            summary="Browser automation dependencies stay optional.",
            rationale="Android/Termux environments cannot reliably assume Playwright.",
            affected_repos=["code_puppy"],
            evidence_artifact_ids=["PR-494"],
            created_at="",
            last_reviewed_at="",
            supersedes=[],
            superseded_by=[],
        )
    )

    response = consult_mod.build_pre_tool_response(
        "create_file",
        {
            "file_path": "pyproject.toml",
            "content": (
                '[project]\nname = "demo"\ndependencies = [\n    "requests>=2.32",\n]\n'
            ),
        },
    )

    assert response is None
    assert warnings == []


def test_non_dependency_edit_is_ignored(
    doctrine_env: tuple[Path, object, object, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, decisions_mod, consult_mod, _ = doctrine_env
    warnings: list[str] = []
    monkeypatch.setattr(consult_mod, "emit_warning", warnings.append)

    decisions_mod.upsert_decision(
        decisions_mod.DecisionRecord(
            id="playwright-optional-on-android",
            title="Playwright Optional On Android",
            status="active",
            confidence="high",
            summary="Browser automation dependencies stay optional.",
            rationale="Android/Termux environments cannot reliably assume Playwright.",
            affected_repos=["code_puppy"],
            evidence_artifact_ids=["PR-494"],
            created_at="",
            last_reviewed_at="",
            supersedes=[],
            superseded_by=[],
        )
    )

    response = consult_mod.build_pre_tool_response(
        "replace_in_file",
        {
            "file_path": "README.md",
            "replacements": [{"old_str": "old", "new_str": "playwright"}],
        },
    )

    assert response is None
    assert warnings == []
