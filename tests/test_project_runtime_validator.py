"""Tests for the read-only Project OS validator."""

from __future__ import annotations

import json

from code_puppy.plugins.project_runtime import commands, store, validator


def _use_tmp_state(tmp_path, monkeypatch):
    state_file = tmp_path / "project_runs.json"
    monkeypatch.setattr(store, "STATE_FILE", str(state_file))
    return state_file


def _load_raw(state_file):
    return json.loads(state_file.read_text(encoding="utf-8"))


def _save_raw(state_file, state):
    state_file.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def test_project_validate_passes_clean_state_read_only(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    store.create_run(project="Code Puppy", objective="Validate", run_id="run-valid")
    store.resume_run("run-valid")
    store.complete_run("run-valid", detail="done")
    before = state_file.read_text(encoding="utf-8")

    output = commands.dispatch(["validate"])

    assert output.startswith("Project OS Validation")
    assert "status : PASS" in output
    assert "checked: 1 run(s), 3 event(s)" in output
    assert "No violations." in output
    assert state_file.read_text(encoding="utf-8") == before


def test_validator_reports_unknown_event_type_and_missing_run(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    store.create_run(project="Code Puppy", objective="Validate", run_id="run-valid")
    state = _load_raw(state_file)
    state["events"]["evt-bad"] = {
        "event_id": "evt-bad",
        "run_id": "run-missing",
        "event_type": "goblin_mode",
        "timestamp": "2026-01-01T00:00:00+00:00",
        "source": "test",
    }
    _save_raw(state_file, state)

    report = validator.validate_state()

    assert not report.passed
    laws = [violation.law for violation in report.violations]
    assert "Every Event Record has exactly one known Event Type." in laws
    assert "Every Event Record belongs to exactly one existing Project Run." in laws
    rendered = validator.format_report(report)
    assert "status : FAIL" in rendered
    assert "event_id=evt-bad" in rendered
    assert "run_id=run-missing" in rendered
    assert "goblin_mode" in rendered


def test_validator_reports_missing_parent_event(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    store.create_run(project="Code Puppy", objective="Validate", run_id="run-parent")
    state = _load_raw(state_file)
    state["events"]["evt-child"] = {
        "event_id": "evt-child",
        "run_id": "run-parent",
        "event_type": "checkpoint_saved",
        "timestamp": "2026-01-01T00:00:00+00:00",
        "source": "test",
        "parent_event_id": "evt-missing",
    }
    _save_raw(state_file, state)

    output = commands.dispatch(["validate"])

    assert "status : FAIL" in output
    assert "Event causality must point to an existing Event Record." in output
    assert "parent_event_id 'evt-missing' does not exist" in output
    assert "event_id=evt-child" in output


def test_validator_reports_causality_cycle(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    store.create_run(project="Code Puppy", objective="Validate", run_id="run-cycle")
    state = _load_raw(state_file)
    state["events"]["evt-a"] = {
        "event_id": "evt-a",
        "run_id": "run-cycle",
        "event_type": "checkpoint_saved",
        "timestamp": "2026-01-01T00:00:00+00:00",
        "source": "test",
        "parent_event_id": "evt-b",
    }
    state["events"]["evt-b"] = {
        "event_id": "evt-b",
        "run_id": "run-cycle",
        "event_type": "checkpoint_saved",
        "timestamp": "2026-01-01T00:01:00+00:00",
        "source": "test",
        "parent_event_id": "evt-a",
    }
    _save_raw(state_file, state)

    output = commands.dispatch(["validate"])

    assert "status : FAIL" in output
    assert "Event causality must remain acyclic." in output
    assert "cycle detected" in output


def test_validator_reports_invalid_run_status(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    store.create_run(project="Code Puppy", objective="Validate", run_id="run-status")
    state = _load_raw(state_file)
    state["runs"]["run-status"]["status"] = "haunted"
    _save_raw(state_file, state)

    output = commands.dispatch(["validate"])

    assert "status : FAIL" in output
    assert "Every Project Run has exactly one valid current state." in output
    assert "unknown run status" in output
    assert "run_id=run-status" in output


def test_validator_reports_completed_then_resumed(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    store.create_run(project="Code Puppy", objective="Validate", run_id="run-zombie")
    store.resume_run("run-zombie")
    store.complete_run("run-zombie", detail="done")
    state = _load_raw(state_file)
    state["events"]["evt-zombie"] = {
        "event_id": "evt-zombie",
        "run_id": "run-zombie",
        "event_type": "project_run_resumed",
        "timestamp": "2099-01-01T00:00:00+00:00",
        "source": "test",
    }
    _save_raw(state_file, state)

    output = commands.dispatch(["validate"])

    assert "status : FAIL" in output
    assert "Terminal states are not resumable by default." in output
    assert "project_run_resumed appears after terminal event" in output
    assert "event_id=evt-zombie" in output


def test_validator_reports_blocked_resume_without_unblock(tmp_path, monkeypatch):
    _use_tmp_state(tmp_path, monkeypatch)
    store.create_run(project="Code Puppy", objective="Validate", run_id="run-blocked")
    store.record_event("run-blocked", "run_blocked", payload_summary="blocked")
    store.record_event("run-blocked", "project_run_resumed", payload_summary="oops")

    output = commands.dispatch(["validate"])

    assert "status : FAIL" in output
    assert "A blocked run cannot resume without run_unblocked causality." in output
    assert "project_run_resumed appears after blocker" in output


def test_validator_reports_waiting_approval_resume_without_approval(
    tmp_path, monkeypatch
):
    _use_tmp_state(tmp_path, monkeypatch)
    store.create_run(project="Code Puppy", objective="Validate", run_id="run-approval")
    store.record_event(
        "run-approval", "approval_requested", payload_summary="need approval"
    )
    store.record_event("run-approval", "project_run_resumed", payload_summary="oops")

    output = commands.dispatch(["validate"])

    assert "status : FAIL" in output
    assert (
        "A waiting_approval run cannot resume without approval_granted causality."
        in output
    )
    assert "project_run_resumed appears after approval request" in output


def test_validator_reports_current_status_without_event_evidence(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    store.create_run(
        project="Code Puppy", objective="Validate", run_id="run-no-evidence"
    )
    state = _load_raw(state_file)
    state["runs"]["run-no-evidence"]["status"] = "running"
    _save_raw(state_file, state)

    output = commands.dispatch(["validate"])

    assert "status : FAIL" in output
    assert "Every state transition is caused by an Event Record." in output
    assert "status 'running' has no project_run_resumed evidence" in output
