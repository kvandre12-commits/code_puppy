"""Tests for the read-only Project Run dispatch plan report."""

from __future__ import annotations

import json

from code_puppy.plugins.project_runtime import commands, dispatch_plan, store


def _use_tmp_state(tmp_path, monkeypatch):
    state_file = tmp_path / "project_runs.json"
    monkeypatch.setattr(store, "STATE_FILE", str(state_file))
    return state_file


def _load_raw(state_file):
    return json.loads(state_file.read_text(encoding="utf-8"))


def _save_raw(state_file, state):
    state_file.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def _patch_run(state_file, run_id: str, **updates: str) -> None:
    state = _load_raw(state_file)
    state["runs"][run_id].update(updates)
    _save_raw(state_file, state)


def test_dispatch_plan_reports_selected_run_without_effects(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    store.create_run(
        project="Code Puppy",
        objective="Eligible work",
        run_id="run-eligible",
        status="ready",
    )
    _patch_run(state_file, "run-eligible", updated_at="2026-01-01T00:01:00+00:00")
    store.create_run(
        project="DroidPuppy",
        objective="Blocked but older",
        run_id="run-blocked",
    )
    store.record_event("run-blocked", "run_blocked", payload_summary="blocked")
    _patch_run(
        state_file,
        "run-blocked",
        status="blocked",
        updated_at="2026-01-01T00:00:00+00:00",
    )
    before = state_file.read_text(encoding="utf-8")

    output = commands.dispatch(["run", "dispatch-plan"])

    assert output.startswith("Project Run Dispatch Plan")
    assert "validator       : PASS" in output
    assert "selection_policy: fifo_updated_at_then_run_id" in output
    assert "run_id              : run-eligible" in output
    assert "run-blocked" not in output
    assert "dispatch_action     : prepare_agent_lease_draft" in output
    assert "required_lease_scope: one_bounded_project_run_step" in output
    assert "proof_event_type    : dispatch_planned" in output
    assert "mutates             : no" in output
    assert "wakes               : no" in output
    assert "leases              : no" in output
    assert "executes            : no" in output
    assert state_file.read_text(encoding="utf-8") == before


def test_dispatch_plan_validator_fail_has_no_plan(tmp_path, monkeypatch):
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
        run_id="run-invalid",
    )
    _patch_run(state_file, "run-invalid", status="goblin_mode")
    before = state_file.read_text(encoding="utf-8")

    plan = dispatch_plan.plan_dispatch()
    output = dispatch_plan.format_plan(plan)

    assert not plan.validation_passed
    assert plan.selected is None
    assert "validator       : FAIL" in output
    assert "reason          : validator FAIL prevents dispatch planning" in output
    assert "Plan:\n- (none)" in output
    assert state_file.read_text(encoding="utf-8") == before


def test_dispatch_plan_rejects_arguments(tmp_path, monkeypatch):
    _use_tmp_state(tmp_path, monkeypatch)

    try:
        commands.dispatch(["run", "dispatch-plan", "--do-it"])
    except ValueError as exc:
        assert "dispatch-plan does not accept arguments" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("expected dispatch-plan command to reject arguments")
