from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path

from code_puppy.plugins.upstream_maintenance.maintenance import (
    apply_fast_forward,
    check_due,
    format_report,
    inspect_repository,
    run_maintenance,
)


def completed(args: list[str], stdout: str = "", returncode: int = 0):
    return subprocess.CompletedProcess(args, returncode, stdout=stdout, stderr="")


class FakeGit:
    def __init__(self, responses: dict[tuple[str, ...], str | tuple[int, str]]):
        self.responses = responses
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, args: list[str], root: Path):
        del root
        key = tuple(args)
        self.calls.append(key)
        response = self.responses.get(key, "")
        if isinstance(response, tuple):
            return completed(args, response[1], response[0])
        return completed(args, response)


def repository_responses(*, branch: str, dirty: bool, ahead: int, behind: int):
    return {
        ("branch", "--show-current"): f"{branch}\n",
        ("status", "--porcelain"): " M local.py\n" if dirty else "",
        ("rev-parse", "HEAD"): "local-sha\n",
        ("rev-parse", "--verify", "origin/main"): "remote-sha\n",
        ("rev-list", "--left-right", "--count", "HEAD...origin/main"): (
            f"{ahead} {behind}\n"
        ),
    }


def test_check_due_is_throttled():
    state = {"checked_at_unix": 1_000}
    assert check_due(state, 1_030, 3_600) is False
    assert check_due(state, 5_000, 3_600) is True


def test_clean_main_behind_is_apply_eligible(tmp_path):
    git = FakeGit(repository_responses(branch="main", dirty=False, ahead=0, behind=2))

    repository = inspect_repository(tmp_path, run_git=git)

    assert repository["update_available"] is True
    assert repository["apply_eligible"] is True


def test_feature_branch_is_never_apply_eligible(tmp_path):
    git = FakeGit(
        repository_responses(
            branch="android-share-packet", dirty=False, ahead=0, behind=2
        )
    )

    repository = inspect_repository(tmp_path, run_git=git)
    applied, detail = apply_fast_forward(tmp_path, repository, run_git=git)

    assert repository["apply_eligible"] is False
    assert applied is False
    assert "blocked" in detail
    assert not any(call[:2] == ("merge", "--ff-only") for call in git.calls)


def test_dirty_main_is_never_apply_eligible(tmp_path):
    git = FakeGit(repository_responses(branch="main", dirty=True, ahead=0, behind=1))

    repository = inspect_repository(tmp_path, run_git=git)

    assert repository["apply_eligible"] is False


def test_fast_forward_uses_ff_only(tmp_path):
    responses = repository_responses(branch="main", dirty=False, ahead=0, behind=1)
    responses[("merge", "--ff-only", "origin/main")] = "Updating local..remote\n"
    git = FakeGit(responses)
    repository = inspect_repository(tmp_path, run_git=git)

    applied, detail = apply_fast_forward(tmp_path, repository, run_git=git)

    assert applied is True
    assert "Updating" in detail
    assert ("merge", "--ff-only", "origin/main") in git.calls


def test_run_maintenance_defaults_to_check_only(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    state = tmp_path / "state.json"
    responses = repository_responses(branch="main", dirty=False, ahead=0, behind=1)
    responses[("fetch", "--quiet", "origin", "main")] = ""
    git = FakeGit(responses)
    monkeypatch.delenv("CODE_PUPPY_AUTO_UPDATE", raising=False)
    monkeypatch.setattr(
        "code_puppy.plugins.upstream_maintenance.maintenance.audit_capabilities",
        lambda: {"missing_required": [], "optional_missing": [], "notes": []},
    )
    monkeypatch.setattr(
        "code_puppy.plugins.upstream_maintenance.maintenance.shutil.which",
        lambda command: f"/bin/{command}",
    )

    result = run_maintenance(
        root=root,
        force=True,
        now=1234,
        path=state,
        run_git=git,
    )

    assert result["repository"]["update_available"] is True
    assert result["repository"]["auto_apply_enabled"] is False
    assert result["repository"]["applied"] is False
    assert not any(call[:2] == ("merge", "--ff-only") for call in git.calls)
    assert (
        json.loads(state.read_text())["schema"] == "code_puppy.upstream_maintenance.v1"
    )


def test_startup_schedules_background_worker(monkeypatch):
    from code_puppy.plugins.upstream_maintenance import register_callbacks

    ran = asyncio.Event()

    async def fake_worker():
        ran.set()

    monkeypatch.setattr(register_callbacks, "_startup_worker", fake_worker)

    async def exercise():
        register_callbacks._on_startup()
        await asyncio.wait_for(ran.wait(), timeout=1)
        await asyncio.sleep(0)

    asyncio.run(exercise())


def test_report_explains_feature_branch_gate():
    report = format_report(
        {
            "capabilities": {
                "missing_required": [],
                "optional_missing": ["playwright"],
                "notes": ["Playwright is optional on Android."],
            },
            "repository": {
                "available": True,
                "upstream_ref": "origin/main",
                "ahead": 1,
                "behind": 2,
                "dirty": False,
                "branch": "feature",
                "target_branch": "main",
                "applied": False,
                "update_available": True,
            },
        }
    )

    assert "feature branch feature left untouched" in report
    assert "Playwright is optional on Android" in report
