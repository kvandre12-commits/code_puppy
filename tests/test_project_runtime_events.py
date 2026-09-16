"""Tests for Project OS EventRecord and why/trace views."""

from __future__ import annotations

import json

import pytest

from code_puppy.plugins.project_runtime import commands, store


def _use_tmp_state(tmp_path, monkeypatch):
    state_file = tmp_path / "project_runs.json"
    monkeypatch.setattr(store, "STATE_FILE", str(state_file))
    return state_file


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
    for header in (
        "event_id",
        "parent_event_id",
        "timestamp",
        "event_type",
        "source",
        "payload_summary",
    ):
        assert header in events
    assert "run_created" in events
    assert "checkpoint_saved" in events
    assert "project_runtime" in events
    assert "event record exists" in events
    assert state_file.read_text(encoding="utf-8") == before


def test_event_type_catalog_contains_lifecycle_work_governance_and_blocking_types():
    event_types = {
        event_type.name: event_type for event_type in store.list_event_types()
    }

    assert {
        "run_created",
        "checkpoint_saved",
        "project_run_resumed",
        "project_run_slept",
        "project_run_completed",
        "work_item_completed",
        "approval_requested",
        "approval_granted",
        "run_blocked",
        "run_unblocked",
        "artifact_created",
        "objective_changed",
    } <= set(event_types)
    assert event_types["work_item_completed"].category == "work"
    assert event_types["approval_requested"].category == "governance"
    assert event_types["run_blocked"].category == "blocking"


def test_run_event_types_command_is_read_only(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)

    output = commands.dispatch(["run", "event-types"])

    assert output.startswith("Project Run Event Types")
    assert "lifecycle:" in output
    assert "work:" in output
    assert "governance:" in output
    assert "blocking:" in output
    assert "work_item_completed" in output
    assert "approval_granted" in output
    assert not state_file.exists()


def test_record_event_validates_and_persists_typed_event_records(tmp_path, monkeypatch):
    _use_tmp_state(tmp_path, monkeypatch)
    store.create_run(project="Code Puppy", objective="Events", run_id="run-types")

    event = store.record_event(
        "run-types",
        "work-item-completed",
        payload_summary="Run Table tests finished",
        source="tests",
    )

    assert event.event_type == "work_item_completed"
    assert event.source == "tests"
    assert event.payload_summary == "Run Table tests finished"
    assert event.parent_event_id == ""
    assert [record.event_type for record in store.list_events("run-types")] == [
        "run_created",
        "work_item_completed",
    ]

    with pytest.raises(ValueError, match="unknown event type"):
        store.record_event("run-types", "scheduler_did_magic")


def test_record_event_links_and_traces_causality_chain(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    store.create_run(project="Code Puppy", objective="Causality", run_id="run-chain")
    root = store.record_event(
        "run-chain",
        "approval_requested",
        payload_summary="Need operator approval",
        source="tests",
    )
    granted = store.record_event(
        "run-chain",
        "approval_granted",
        payload_summary="Operator approved",
        source="tests",
        parent_event_id=root.event_id,
    )
    unblocked = store.record_event(
        "run-chain",
        "run_unblocked",
        payload_summary="Approval dependency cleared",
        source="tests",
        parent_event_id=granted.event_id,
    )

    assert unblocked.parent_event_id == granted.event_id
    raw = json.loads(state_file.read_text(encoding="utf-8"))
    assert raw["events"][unblocked.event_id]["parent_event_id"] == granted.event_id

    trace = store.trace_event(unblocked.event_id)

    assert [event.event_id for event in trace] == [
        root.event_id,
        granted.event_id,
        unblocked.event_id,
    ]
    assert [event.event_type for event in trace] == [
        "approval_requested",
        "approval_granted",
        "run_unblocked",
    ]


def test_record_event_rejects_missing_parent_event(tmp_path, monkeypatch):
    _use_tmp_state(tmp_path, monkeypatch)
    store.create_run(project="Code Puppy", objective="Causality", run_id="run-chain")

    with pytest.raises(ValueError, match="parent Event Record not found"):
        store.record_event(
            "run-chain",
            "approval_granted",
            parent_event_id="evt-nope",
        )


def test_project_event_trace_command_is_read_only(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    store.create_run(project="Code Puppy", objective="Trace", run_id="run-trace")
    root = store.record_event(
        "run-trace",
        "approval_requested",
        payload_summary="Need approval",
    )
    child = store.record_event(
        "run-trace",
        "approval_granted",
        payload_summary="Approved",
        parent_event_id=root.event_id,
    )
    before = state_file.read_text(encoding="utf-8")

    output = commands.dispatch(["event", "trace", child.event_id])

    assert output.startswith("Project Event Trace")
    assert f"root: {root.event_id} [approval_requested]" in output
    assert f"caused: {child.event_id} [approval_granted]" in output
    assert f"parent={root.event_id}" in output
    assert "summary: Need approval" in output
    assert "summary: Approved" in output
    assert state_file.read_text(encoding="utf-8") == before


def test_run_why_explains_current_state_from_latest_event(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    store.create_run(
        project="Code Puppy",
        objective="Explain runs",
        run_id="run-why",
        checkpoint="event layer exists",
        next_action="add why command",
    )
    before = state_file.read_text(encoding="utf-8")

    output = commands.dispatch(["run", "why", "run-why"])

    assert output.startswith("Project Run Why")
    assert "run_id      : run-why" in output
    assert "project     : Code Puppy" in output
    assert "objective   : Explain runs" in output
    assert "status      : sleeping" in output
    assert "checkpoint  : event layer exists" in output
    assert "next_action : add why command" in output
    assert "latest_event:" in output
    assert "event_type      : run_created" in output
    assert "payload_summary : Project Run created" in output
    assert "causality_trace:" in output
    assert "latest event is a root event" in output
    assert "scheduler" not in output.lower()
    assert "wake" not in output.lower()
    assert state_file.read_text(encoding="utf-8") == before


def test_run_why_includes_latest_event_causality_trace(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    store.create_run(
        project="Code Puppy", objective="Trace why", run_id="run-why-chain"
    )
    root = store.record_event(
        "run-why-chain",
        "approval_requested",
        payload_summary="Need approval",
    )
    granted = store.record_event(
        "run-why-chain",
        "approval_granted",
        payload_summary="Approved",
        parent_event_id=root.event_id,
    )
    unblocked = store.record_event(
        "run-why-chain",
        "run_unblocked",
        payload_summary="Approval cleared",
        parent_event_id=granted.event_id,
    )
    before = state_file.read_text(encoding="utf-8")

    output = commands.dispatch(["run", "why", "run-why-chain"])

    assert f"event_id        : {unblocked.event_id}" in output
    assert f"parent_event_id : {granted.event_id}" in output
    assert f"root: {root.event_id} [approval_requested]" in output
    assert f"caused: {granted.event_id} [approval_granted]" in output
    assert f"caused: {unblocked.event_id} [run_unblocked]" in output
    assert "summary: Need approval" in output
    assert "summary: Approved" in output
    assert "summary: Approval cleared" in output
    assert state_file.read_text(encoding="utf-8") == before


def test_run_why_reports_no_event_records_honestly(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    store.create_run(project="Legacy", objective="No events", run_id="run-no-events")
    state = store.load_state()
    state["events"] = {}
    store.save_state(state)
    before = state_file.read_text(encoding="utf-8")

    output = commands.dispatch(["run", "why", "run-no-events"])

    assert output.startswith("Project Run Why")
    assert "run_id      : run-no-events" in output
    assert "status      : sleeping" in output
    assert "No Event Records yet." in output
    assert "latest_event:" not in output
    assert "causality_trace:" not in output
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
