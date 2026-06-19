"""Tests for the read-only Project Run lease draft report."""

from __future__ import annotations

import json

from code_puppy.plugins.project_runtime import commands, lease_draft, store


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


def test_lease_draft_reports_authority_request_without_issuing(tmp_path, monkeypatch):
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

    output = commands.dispatch(["run", "lease-draft"])

    assert output.startswith("Project Run Lease Draft")
    assert "validator               : PASS" in output
    assert "dispatch_plan_id        : dispatch-plan:run-eligible" in output
    assert "run_id                  : run-eligible" in output
    assert "run-blocked" not in output
    assert "requested_agent_identity: unassigned_agent" in output
    assert "requested_action_scope  : project_run.execute_bounded_step" in output
    assert "requested_capability    : project_runtime.step" in output
    assert "required_authority_check: identity_exists" in output
    assert "proposed_expiry         : one_step_or_15_minutes" in output
    assert "authorizes              : no" in output
    assert "mutates                 : no" in output
    assert "wakes                   : no" in output
    assert "leases                  : no" in output
    assert "executes                : no" in output
    assert state_file.read_text(encoding="utf-8") == before


def test_lease_draft_validator_fail_has_no_draft(tmp_path, monkeypatch):
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

    draft = lease_draft.draft_lease()
    output = lease_draft.format_draft(draft)

    assert not draft.validation_passed
    assert not draft.run_id
    assert "validator               : FAIL" in output
    assert "reason                  : validator FAIL prevents lease drafting" in output
    assert "Draft:\n- (none)" in output
    assert state_file.read_text(encoding="utf-8") == before


def test_lease_draft_rejects_arguments(tmp_path, monkeypatch):
    _use_tmp_state(tmp_path, monkeypatch)

    try:
        commands.dispatch(["run", "lease-draft", "--issue"])
    except ValueError as exc:
        assert "lease-draft does not accept arguments" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("expected lease-draft command to reject arguments")
