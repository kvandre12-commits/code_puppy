"""Tests for the read-only Project Run Selection Policy report."""

from __future__ import annotations

import json

from code_puppy.plugins.project_runtime import commands, selection_policy, store


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


def test_run_selection_selects_oldest_eligible_candidate_read_only(
    tmp_path, monkeypatch
):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    store.create_run(
        project="Code Puppy",
        objective="High priority eligible",
        run_id="run-high",
        status="ready",
    )
    _patch_run(state_file, "run-high", updated_at="2026-01-01T00:01:00+00:00")
    store.create_run(
        project="SharpEdge",
        objective="Low priority eligible",
        run_id="run-low",
        status="ready",
    )
    _patch_run(state_file, "run-low", updated_at="2026-01-01T00:02:00+00:00")
    store.create_run(
        project="DroidPuppy",
        objective="Blocked but old",
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

    output = commands.dispatch(["run", "selection"])

    assert output.startswith("Project Run Selection")
    assert "validator: PASS" in output
    assert "policy   : fifo_updated_at_then_run_id" in output
    assert "Selected:" in output
    assert "- run-high" in output
    assert "reason   : selected oldest eligible candidate" in output
    assert "Considered:" in output
    assert "- run-low" in output
    assert "Excluded:" in output
    assert "- run-blocked" in output
    assert "blocked; scheduler cannot bypass blocker evidence" in output
    assert state_file.read_text(encoding="utf-8") == before


def test_run_selection_validator_fail_selects_nothing(tmp_path, monkeypatch):
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

    report = selection_policy.select_candidate()
    output = selection_policy.format_report(report)

    assert not report.validation_passed
    assert report.selected is None
    assert not report.considered
    assert "validator: FAIL" in output
    assert "reason   : validator FAIL prevents selection" in output
    assert "Selected:\n- (none)" in output
    assert "- run-ready" in output
    assert "validator FAIL blocks all runtime progression" in output
    assert "- run-invalid" in output
    assert "MARK_INVALID" in output
    assert state_file.read_text(encoding="utf-8") == before


def test_run_selection_rejects_arguments(tmp_path, monkeypatch):
    _use_tmp_state(tmp_path, monkeypatch)

    try:
        commands.dispatch(["run", "selection", "--dispatch"])
    except ValueError as exc:
        assert "selection does not accept arguments" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("expected selection command to reject arguments")
