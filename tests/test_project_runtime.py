"""Tests for Project OS runtime primitives."""

from __future__ import annotations

import json

from code_puppy.plugins.project_runtime import commands, store


def _use_tmp_state(tmp_path, monkeypatch):
    state_file = tmp_path / "project_runs.json"
    monkeypatch.setattr(store, "STATE_FILE", str(state_file))
    return state_file


def test_create_checkpoint_resume_and_complete_project_run(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)

    run = store.create_run(
        run_id="run-android-os-001",
        project="Code Puppy",
        objective="Build Android Project OS",
        work_items=["Provider registry", "Scheduler", "Run table"],
        checkpoint="scheduler doctrine complete",
        next_action="implement run table prototype",
    )

    assert run.run_id == "run-android-os-001"
    assert run.status == "sleeping"
    assert state_file.exists()

    loaded = store.get_run("run-android-os-001")
    assert loaded.project == "Code Puppy"
    assert loaded.objective == "Build Android Project OS"
    assert [item.title for item in loaded.work_items] == [
        "Provider registry",
        "Scheduler",
        "Run table",
    ]
    assert loaded.checkpoint == "scheduler doctrine complete"
    assert loaded.next_action == "implement run table prototype"

    checkpointed = store.checkpoint_run(
        "run-android-os-001",
        checkpoint="run table prototype persisted",
        next_action="wire slash command resume",
        status="sleeping",
    )
    assert checkpointed.checkpoint == "run table prototype persisted"
    assert checkpointed.next_action == "wire slash command resume"

    resumed = store.resume_run("run-android-os-001")
    assert resumed.status == "running"
    assert resumed.resumed_at

    completed = store.complete_run("run-android-os-001", detail="primitive proven")
    assert completed.status == "completed"
    assert completed.completed_at
    assert [event.action for event in completed.journal] == [
        "created",
        "checkpoint",
        "resumed",
        "completed",
    ]

    raw = json.loads(state_file.read_text(encoding="utf-8"))
    assert raw["runs"]["run-android-os-001"]["status"] == "completed"


def test_project_run_survives_reloading_without_agent_or_model(tmp_path, monkeypatch):
    _use_tmp_state(tmp_path, monkeypatch)

    store.create_run(
        run_id="run-survive-001",
        project="SharpEdge",
        objective="Ship cockpit",
        checkpoint="market doctrine loaded",
        next_action="resume build",
    )

    # Simulate agent/model replacement by discarding the returned object and
    # loading only from persisted Project Run state.
    reloaded = store.run_from_dict(store.load_state()["runs"]["run-survive-001"])

    assert reloaded.project == "SharpEdge"
    assert reloaded.status == "sleeping"
    assert reloaded.next_action == "resume build"
    assert not hasattr(reloaded, "agent")
    assert not hasattr(reloaded, "model")


def test_dispatch_create_status_checkpoint_resume_complete(tmp_path, monkeypatch):
    _use_tmp_state(tmp_path, monkeypatch)

    created = commands.dispatch(
        [
            "run",
            "create",
            "run-cli-001",
            "--project",
            "Code Puppy",
            "--objective",
            "Build Android Project OS",
            "--work",
            "Run table",
            "--checkpoint",
            "scheduler doctrine complete",
            "--next",
            "implement run table prototype",
        ]
    )
    assert "Created Project Run" in created
    assert "run-cli-001" in created

    status = commands.dispatch(["run", "status", "run-cli-001"])
    assert "Project Run: run-cli-001" in status
    assert "implement run table prototype" in status

    checkpointed = commands.dispatch(
        [
            "run",
            "checkpoint",
            "run-cli-001",
            "--checkpoint",
            "prototype exists",
            "--next",
            "resume it",
        ]
    )
    assert "Checkpointed Project Run" in checkpointed
    assert store.get_run("run-cli-001").checkpoint == "prototype exists"

    resumed = commands.dispatch(["run", "resume", "run-cli-001"])
    assert "Resumed Project Run" in resumed
    assert store.get_run("run-cli-001").status == "running"

    completed = commands.dispatch(
        ["run", "complete", "run-cli-001", "--detail", "done"]
    )
    assert "Completed Project Run" in completed
    assert store.get_run("run-cli-001").status == "completed"


def test_status_lists_runs_and_filters_status(tmp_path, monkeypatch):
    _use_tmp_state(tmp_path, monkeypatch)

    store.create_run(project="Code Puppy", objective="One", run_id="run-one")
    store.create_run(
        project="Code Puppy", objective="Two", run_id="run-two", status="blocked"
    )

    all_runs = commands.dispatch(["run", "status"])
    assert "run-one" in all_runs
    assert "run-two" in all_runs

    blocked = commands.dispatch(["run", "status", "--status", "blocked"])
    assert "run-two" in blocked
    assert "run-one" not in blocked


def test_non_project_command_is_ignored():
    assert commands.handle("/bridge list", "bridge") is None
