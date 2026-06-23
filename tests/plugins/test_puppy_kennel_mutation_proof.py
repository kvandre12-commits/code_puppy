"""Proof harness tests for doctrine-guided mutation changes."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest


@pytest.fixture
def doctrine_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, object, object, object]:
    root = tmp_path / "kennel"
    repo_root = tmp_path / "code_puppy_backup_20260617"
    repo_root.mkdir()
    monkeypatch.setenv("PUPPY_KENNEL_ROOT", str(root))
    monkeypatch.chdir(repo_root)

    from code_puppy.plugins.puppy_kennel import config as kennel_config
    from code_puppy.plugins.puppy_kennel import decisions as decisions_mod
    from code_puppy.plugins.puppy_kennel import doctrine_consultation as consult_mod
    from code_puppy.plugins.puppy_kennel import doctrine_receipts as receipts_mod
    from code_puppy.plugins.puppy_kennel import kennel as kennel_mod
    from code_puppy.plugins.puppy_kennel import mutation_proof as proof_mod
    from code_puppy.plugins.puppy_kennel import state as state_mod

    importlib.reload(kennel_config)
    importlib.reload(state_mod)
    importlib.reload(kennel_mod)
    importlib.reload(receipts_mod)
    importlib.reload(decisions_mod)
    importlib.reload(consult_mod)
    importlib.reload(proof_mod)
    kennel_mod.initialize()
    return repo_root, decisions_mod, consult_mod, proof_mod


def test_doctrine_warning_changes_plan_and_patch(
    doctrine_env: tuple[Path, object, object, object],
) -> None:
    _, decisions_mod, consult_mod, proof_mod = doctrine_env

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

    from code_puppy.plugins.puppy_kennel import doctrine_receipts as receipts_mod

    warning = consult_mod.build_pre_tool_response("replace_in_file", tool_args)
    result = proof_mod.prove_doctrine_guided_mutation("replace_in_file", tool_args)
    receipts = receipts_mod.recent_doctrine_receipts(limit=5)

    assert warning is not None
    assert result is not None
    assert "[doctrine check] Potential conflict detected" in result.warning_message
    assert warning["context_message"] == result.warning_message
    assert result.changed_plan is True
    assert result.patch_differs is True
    assert result.original_plan != result.adapted_plan
    assert result.doctrine_decision_ids == ("playwright-optional-on-android",)

    original_new = result.original_tool_args["replacements"][0]["new_str"]
    adapted_new = result.adapted_tool_args["replacements"][0]["new_str"]

    assert '"playwright>=1.55"' in original_new
    assert '"playwright>=1.55"' not in adapted_new
    assert adapted_new == result.original_tool_args["replacements"][0]["old_str"]
    assert "avoid adding [playwright]" in result.adapted_plan
    assert len(receipts) == 2
    assert receipts[0].decision_id == "playwright-optional-on-android"
    assert receipts[0].adapted is True
    assert receipts[0].before_summary == result.original_plan
    assert receipts[0].after_summary == result.adapted_plan
    assert receipts[1].adapted is False


def test_proof_harness_returns_none_without_doctrine_conflict(
    doctrine_env: tuple[Path, object, object, object],
) -> None:
    _, decisions_mod, _consult_mod, proof_mod = doctrine_env

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

    result = proof_mod.prove_doctrine_guided_mutation(
        "replace_in_file",
        {
            "file_path": "pyproject.toml",
            "replacements": [
                {
                    "old_str": 'dependencies = [\n    "rich>=13.0",\n]\n',
                    "new_str": (
                        "dependencies = [\n"
                        '    "rich>=13.0",\n'
                        '    "requests>=2.32",\n'
                        "]\n"
                    ),
                }
            ],
        },
    )

    assert result is None
