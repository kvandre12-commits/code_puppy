"""Tests for the read-only runnable candidate projection."""

from __future__ import annotations

import json

from code_puppy.plugins.project_runtime import commands, runtime_candidates, store


def _use_tmp_state(tmp_path, monkeypatch):
    state_file = tmp_path / "project_runs.json"
    monkeypatch.setattr(store, "STATE_FILE", str(state_file))
    return state_file


def _load_raw(state_file):
    return json.loads(state_file.read_text(encoding="utf-8"))


def _save_raw(state_file, state):
    state_file.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def _set_status(state_file, run_id: str, status: str) -> None:
    state = _load_raw(state_file)
    state["runs"][run_id]["status"] = status
    _save_raw(state_file, state)


def test_run_candidates_project_ready_and_sleeping_runs_read_only(
    tmp_path, monkeypatch
):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    store.create_run(
        project="Code Puppy",
        objective="Ready work",
        run_id="run-ready",
        status="ready",
    )
    store.create_run(
        project="SharpEdge",
        objective="Sleeping work",
        run_id="run-sleeping",
    )
    store.create_run(
        project="DroidPuppy",
        objective="Blocked work",
        run_id="run-blocked",
    )
    store.record_event("run-blocked", "run_blocked", payload_summary="waiting adb")
    _set_status(state_file, "run-blocked", "blocked")
    store.create_run(
        project="Robinhood Bridge",
        objective="Approval work",
        run_id="run-approval",
    )
    store.record_event(
        "run-approval", "approval_requested", payload_summary="operator approval"
    )
    _set_status(state_file, "run-approval", "waiting_approval")
    store.create_run(
        project="Docs",
        objective="Completed work",
        run_id="run-completed",
    )
    store.complete_run("run-completed", detail="done")
    before = state_file.read_text(encoding="utf-8")

    output = commands.dispatch(["run", "candidates"])

    assert output.startswith("Project Run Candidates")
    assert "validator: PASS" in output
    assert "Candidates:" in output
    assert "- run-ready" in output
    assert "  reason   : runnable: status 'ready' with validator PASS" in output
    assert "- run-sleeping" in output
    assert "  reason   : runnable: status 'sleeping' with validator PASS" in output
    assert "Excluded:" in output
    assert "- run-blocked" in output
    assert "blocked; scheduler cannot bypass blocker evidence" in output
    assert "- run-approval" in output
    assert "waiting for approval; scheduler cannot bypass approval" in output
    assert "- run-completed" in output
    assert "terminal completed run is not schedulable" in output
    assert state_file.read_text(encoding="utf-8") == before


def test_run_candidates_validator_fail_blocks_all_runtime_progression(
    tmp_path, monkeypatch
):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    store.create_run(
        project="Code Puppy",
        objective="Ready work",
        run_id="run-ready",
        status="ready",
    )
    store.create_run(
        project="Haunted",
        objective="Invalid work",
        run_id="run-haunted",
    )
    _set_status(state_file, "run-haunted", "goblin_mode")
    before = state_file.read_text(encoding="utf-8")

    projection = runtime_candidates.project_candidates()
    output = runtime_candidates.format_projection(projection)

    assert not projection.validation_passed
    assert not projection.candidates
    assert "validator: FAIL" in output
    assert "- run-ready" in output
    assert "validator FAIL blocks all runtime progression" in output
    assert "- run-haunted" in output
    assert "Every Project Run has exactly one valid current state." in output
    assert "remedy   : MARK_INVALID" in output
    assert "unknown run status 'goblin_mode'" in output
    assert state_file.read_text(encoding="utf-8") == before


def test_run_candidates_rejects_arguments(tmp_path, monkeypatch):
    _use_tmp_state(tmp_path, monkeypatch)

    try:
        commands.dispatch(["run", "candidates", "--mutate"])  # cute, but no
    except ValueError as exc:
        assert "candidates does not accept arguments" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("expected candidates command to reject arguments")
