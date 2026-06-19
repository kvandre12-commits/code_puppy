"""Tests for the read-only Project Run authority check report."""

from __future__ import annotations

import json

from code_puppy.plugins.project_runtime import authority_check, commands, store


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


def test_authority_check_reports_missing_grants_without_issuing(tmp_path, monkeypatch):
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

    output = commands.dispatch(["run", "authority-check"])

    assert output.startswith("Project Run Authority Check")
    assert "validator               : PASS" in output
    assert "lease_draft_id         : lease-draft:run-eligible" in output
    assert "run_id                 : run-eligible" in output
    assert "run-blocked" not in output
    assert "requested_agent_identity: unassigned_agent" in output
    assert "requested_action_scope : project_run.execute_bounded_step" in output
    assert "requested_capability   : project_runtime.step" in output
    assert "identity_present       : no" in output
    assert "authority_grant_present: no" in output
    assert "capability_grant_present: no" in output
    assert "lease_issuable         : no" in output
    assert "authorizes             : no" in output
    assert "mutates                : no" in output
    assert "wakes                  : no" in output
    assert "leases                 : no" in output
    assert "executes               : no" in output
    assert "identity store not implemented" in output
    assert "authority grant store not implemented" in output
    assert "capability grant store not implemented" in output
    assert state_file.read_text(encoding="utf-8") == before


def test_authority_check_validator_fail_has_no_check(tmp_path, monkeypatch):
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

    check = authority_check.check_authority()
    output = authority_check.format_check(check)

    assert not check.validation_passed
    assert not check.run_id
    assert "validator               : FAIL" in output
    assert (
        "reason                  : validator FAIL prevents authority checking" in output
    )
    assert "Check:\n- (none)" in output
    assert "validator FAIL" in output
    assert state_file.read_text(encoding="utf-8") == before


def test_authority_check_rejects_arguments(tmp_path, monkeypatch):
    _use_tmp_state(tmp_path, monkeypatch)

    try:
        commands.dispatch(["run", "authority-check", "--authorize"])
    except ValueError as exc:
        assert "authority-check does not accept arguments" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("expected authority-check command to reject arguments")
