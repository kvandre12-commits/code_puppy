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
    assert [event["event_type"] for event in raw["events"].values()] == [
        "run_created",
        "checkpoint_saved",
        "project_run_resumed",
        "project_run_completed",
    ]


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

    inspected = commands.dispatch(["run", "inspect", "run-cli-001"])
    assert "Project Run Inspect" in inspected
    assert "run_id             : run-cli-001" in inspected

    events = commands.dispatch(["run", "events", "run-cli-001"])
    assert "Project Run Events" in events
    assert "run_created" in events

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


def test_run_list_renders_read_only_run_table(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)

    store.create_run(
        project="Code Puppy",
        objective="Build Android Project OS",
        run_id="run-android-os-001",
        next_action="implement run table prototype",
    )
    store.create_run(
        project="SharpEdge",
        objective="Market cockpit",
        run_id="run-sharpedge-001",
        next_action="wait for market open",
        status="waiting_event",
    )
    before = state_file.read_text(encoding="utf-8")

    table = commands.dispatch(["run", "list"])

    assert table.startswith("Run Table")
    for header in (
        "run_id",
        "project",
        "objective",
        "status",
        "next_action",
        "updated_at",
    ):
        assert header in table
    assert "run-android-os-001" in table
    assert "Code Puppy" in table
    assert "Build Android Project OS" in table
    assert "sleeping" in table
    assert "implement run table prototype" in table
    assert "run-sharpedge-001" in table
    assert state_file.read_text(encoding="utf-8") == before


def test_run_list_filters_status(tmp_path, monkeypatch):
    _use_tmp_state(tmp_path, monkeypatch)

    store.create_run(project="Code Puppy", objective="Ready", run_id="run-ready")
    store.create_run(
        project="DroidPuppy",
        objective="Reconnect ADB",
        run_id="run-blocked",
        status="blocked",
    )

    table = commands.dispatch(["run", "list", "--status", "blocked"])

    assert "run-blocked" in table
    assert "run-ready" not in table


def test_run_inspect_renders_read_only_operator_view(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)

    store.create_run(
        project="Code Puppy",
        objective="Build Android Project OS",
        run_id="run-inspect-001",
        checkpoint="run table exists",
        next_action="add inspect view",
    )
    store.checkpoint_run(
        "run-inspect-001",
        checkpoint="inspect view implemented",
        next_action="add events layer",
    )
    before = state_file.read_text(encoding="utf-8")

    inspected = commands.dispatch(["run", "inspect", "run-inspect-001"])

    assert inspected.startswith("Project Run Inspect")
    assert "run_id             : run-inspect-001" in inspected
    assert "project            : Code Puppy" in inspected
    assert "objective          : Build Android Project OS" in inspected
    assert "status             : sleeping" in inspected
    assert "checkpoint         : inspect view implemented" in inspected
    assert "next_action        : add events layer" in inspected
    assert "blockers           : (none recorded)" in inspected
    assert "required_approvals : (none recorded)" in inspected
    assert "last_event         : " in inspected
    assert "checkpoint_saved: inspect view implemented" in inspected
    assert "journal_summary    : 2 event(s)" in inspected
    assert "created" in inspected
    assert "checkpoint" in inspected
    assert state_file.read_text(encoding="utf-8") == before


def test_run_inspect_explains_unrecorded_blockers_and_approvals(tmp_path, monkeypatch):
    _use_tmp_state(tmp_path, monkeypatch)

    store.create_run(
        project="DroidPuppy",
        objective="Reconnect ADB",
        run_id="run-blocked",
        status="blocked",
    )
    store.create_run(
        project="SharpEdge",
        objective="Submit order draft",
        run_id="run-approval",
        status="waiting_approval",
    )

    blocked = commands.dispatch(["run", "inspect", "run-blocked"])
    approval = commands.dispatch(["run", "inspect", "run-approval"])

    assert "blockers           : (not recorded yet)" in blocked
    assert "required_approvals : (none recorded)" in blocked
    assert "blockers           : (none recorded)" in approval
    assert "required_approvals : (not recorded yet)" in approval


def test_run_events_renders_read_only_event_records(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)

    store.create_run(
        project="Code Puppy",
        objective="Build observability",
        run_id="run-events-001",
        checkpoint="run exists",
    )
    store.checkpoint_run(
        "run-events-001",
        checkpoint="event record exists",
        next_action="add queue later",
    )
    before = state_file.read_text(encoding="utf-8")

    events = commands.dispatch(["run", "events", "run-events-001"])

    assert events.startswith("Project Run Events")
    assert "run_id: run-events-001" in events
    for header in ("event_id", "timestamp", "event_type", "source", "payload_summary"):
        assert header in events
    assert "run_created" in events
    assert "checkpoint_saved" in events
    assert "project_runtime" in events
    assert "event record exists" in events
    assert state_file.read_text(encoding="utf-8") == before


def test_store_lists_event_records_by_run_id(tmp_path, monkeypatch):
    _use_tmp_state(tmp_path, monkeypatch)

    store.create_run(project="A", objective="One", run_id="run-a")
    store.create_run(project="B", objective="Two", run_id="run-b")
    store.checkpoint_run("run-a", checkpoint="only A")

    events = store.list_events("run-a")

    assert [event.run_id for event in events] == ["run-a", "run-a"]
    assert [event.event_type for event in events] == [
        "run_created",
        "checkpoint_saved",
    ]
    assert all(event.event_id.startswith("evt-") for event in events)


def test_non_project_command_is_ignored():
    assert commands.handle("/bridge list", "bridge") is None
