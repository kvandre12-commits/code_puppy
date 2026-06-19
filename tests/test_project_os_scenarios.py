"""Project OS scenario/case-law tests.

These tests exercise complete stories instead of individual validator clauses.
"""

from __future__ import annotations

import json

from code_puppy.plugins.project_runtime import commands, store


def _use_tmp_state(tmp_path, monkeypatch):
    state_file = tmp_path / "project_runs.json"
    monkeypatch.setattr(store, "STATE_FILE", str(state_file))
    return state_file


def _load_raw(state_file):
    return json.loads(state_file.read_text(encoding="utf-8"))


def _save_raw(state_file, state):
    state_file.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def _set_run_status(state_file, run_id: str, status: str) -> None:
    state = _load_raw(state_file)
    state["runs"][run_id]["status"] = status
    _save_raw(state_file, state)


def test_scenario_approval_gate_passes(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    store.create_run(
        project="Code Puppy",
        objective="Approval-gated runtime work",
        run_id="run-scenario-approval",
    )
    requested = store.record_event(
        "run-scenario-approval",
        "approval_requested",
        payload_summary="Need operator approval",
        source="agent:code-puppy-26c058",
    )
    granted = store.record_event(
        "run-scenario-approval",
        "approval_granted",
        payload_summary="Approved by owner",
        source="human:local_owner",
        parent_event_id=requested.event_id,
    )
    unblocked = store.record_event(
        "run-scenario-approval",
        "run_unblocked",
        payload_summary="Approval cleared blocker",
        source="system:project_runtime",
        parent_event_id=granted.event_id,
    )
    store.record_event(
        "run-scenario-approval",
        "project_run_resumed",
        payload_summary="Resumed after approval",
        source="agent:code-puppy-26c058",
        parent_event_id=unblocked.event_id,
    )
    _set_run_status(state_file, "run-scenario-approval", "running")

    output = commands.dispatch(["validate"])

    assert "status : PASS" in output
    assert "No violations." in output


def test_scenario_illegal_blocked_resume_fails(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    store.create_run(
        project="Code Puppy",
        objective="Illegal resume story",
        run_id="run-scenario-illegal-resume",
    )
    blocked = store.record_event(
        "run-scenario-illegal-resume",
        "run_blocked",
        payload_summary="ADB unavailable",
        source="agent:code-puppy-26c058",
    )
    store.record_event(
        "run-scenario-illegal-resume",
        "project_run_resumed",
        payload_summary="Resumed anyway",
        source="agent:code-puppy-26c058",
        parent_event_id=blocked.event_id,
    )
    _set_run_status(state_file, "run-scenario-illegal-resume", "running")

    output = commands.dispatch(["validate"])

    assert "status : FAIL" in output
    assert "A blocked run cannot resume without run_unblocked causality." in output
    assert "precedent: PRECEDENT-002" in output
    assert "project_run_resumed appears after blocker" in output


def test_scenario_project_continuity_survives_agent_model_replacement(
    tmp_path, monkeypatch
):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    store.create_run(
        project="Code Puppy",
        objective="Continue across workers",
        run_id="run-scenario-continuity",
        checkpoint="initial worker checkpoint",
        next_action="resume with replacement worker",
    )
    store.checkpoint_run(
        "run-scenario-continuity",
        checkpoint="agent replaced; model replaced; state persisted",
        next_action="resume run",
    )

    reloaded = store.get_run("run-scenario-continuity")
    assert not hasattr(reloaded, "agent")
    assert not hasattr(reloaded, "model")

    store.resume_run("run-scenario-continuity")
    output = commands.dispatch(["validate"])

    assert "status : PASS" in output
    assert "No violations." in output
    assert state_file.exists()


def test_scenario_governance_failure_missing_approver_attribution_fails(
    tmp_path, monkeypatch
):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    store.create_run(
        project="Code Puppy",
        objective="Governance failure story",
        run_id="run-scenario-governance",
    )
    requested = store.record_event(
        "run-scenario-governance",
        "approval_requested",
        payload_summary="Need approval",
        source="agent:code-puppy-26c058",
    )
    state = _load_raw(state_file)
    state["events"]["evt-no-approver"] = {
        "event_id": "evt-no-approver",
        "run_id": "run-scenario-governance",
        "event_type": "approval_granted",
        "timestamp": "2099-01-01T00:00:00+00:00",
        "source": "",
        "payload_summary": "Approved by nobody in particular",
        "parent_event_id": requested.event_id,
    }
    _save_raw(state_file, state)

    output = commands.dispatch(["validate"])

    assert "status : FAIL" in output
    assert "Every Event Record must have source attribution." in output
    assert "precedent: PRECEDENT-003" in output
    assert "event_id=evt-no-approver" in output
