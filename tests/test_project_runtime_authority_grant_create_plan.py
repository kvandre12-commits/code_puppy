"""Tests for read-only AuthorityGrant creation planning."""

from __future__ import annotations

import json

from code_puppy.plugins.project_runtime import (
    authority_grant_create_plan,
    commands,
    store,
)

ISSUED_AT = "2026-01-01T00:00:00+00:00"
GRANT_ID = "grant:run-eligible:project_run.execute_bounded_step"


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


def _create_ready_run(state_file):
    store.create_run(
        project="Code Puppy",
        objective="Eligible work",
        run_id="run-eligible",
        status="ready",
    )
    _patch_run(state_file, "run-eligible", updated_at="2026-01-01T00:01:00+00:00")


def _grant(grant_id: str = GRANT_ID) -> dict[str, str]:
    return {
        "grant_id": grant_id,
        "subject_identity": "unassigned_agent",
        "allowed_action_scope": "project_run.execute_bounded_step",
        "allowed_capability_scope": "project_runtime.step",
        "boundary": "project_run",
        "issuer": "operator_required",
        "issued_at": ISSUED_AT,
        "expires_at": "2099-01-01T00:00:00+00:00",
        "revoked_at": "",
        "project_id": "",
        "run_id": "run-eligible",
        "reason": "existing grant",
        "precedent_id": "PRECEDENT-006",
    }


def test_grant_create_plan_reports_valid_record_without_creating(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run(state_file)
    before = state_file.read_text(encoding="utf-8")

    plan = authority_grant_create_plan.plan_grant_create(issued_at=ISSUED_AT)
    output = authority_grant_create_plan.format_plan(plan)

    assert plan.would_create_valid_record
    assert output.startswith("Project Authority Grant Create Plan")
    assert "current_authority_validation : PASS" in output
    assert "would_create_valid_record   : yes" in output
    assert "would_duplicate_grant_id    : no" in output
    assert "would_conflict_active_grant : no" in output
    assert "would_violate_scope_boundary: no" in output
    assert "creates_grant               : no" in output
    assert "mutates                     : no" in output
    assert "authorizes                  : no" in output
    assert "leases                      : no" in output
    assert "executes                    : no" in output
    assert f"grant_id: {GRANT_ID}" in output
    assert "issued_at: 2026-01-01T00:00:00+00:00" in output
    assert "expires_at: 2026-01-01T00:15:00+00:00" in output
    assert "Blockers:\n- (none)" in output
    assert state_file.read_text(encoding="utf-8") == before


def test_grant_create_plan_blocks_duplicate_grant_id(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run(state_file)
    state = _load_raw(state_file)
    state["authority_grants"] = {GRANT_ID: _grant()}
    _save_raw(state_file, state)
    before = state_file.read_text(encoding="utf-8")

    output = authority_grant_create_plan.format_plan(
        authority_grant_create_plan.plan_grant_create(issued_at=ISSUED_AT)
    )

    assert "would_create_valid_record   : no" in output
    assert "would_duplicate_grant_id    : yes" in output
    assert "grant_id already exists" in output
    assert state_file.read_text(encoding="utf-8") == before


def test_grant_create_plan_blocks_active_conflict(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run(state_file)
    state = _load_raw(state_file)
    state["authority_grants"] = {"grant-existing": _grant("grant-existing")}
    _save_raw(state_file, state)
    before = state_file.read_text(encoding="utf-8")

    output = authority_grant_create_plan.format_plan(
        authority_grant_create_plan.plan_grant_create(issued_at=ISSUED_AT)
    )

    assert "would_create_valid_record   : no" in output
    assert "would_duplicate_grant_id    : no" in output
    assert "would_conflict_active_grant : yes" in output
    assert "active grant already covers requested authority" in output
    assert state_file.read_text(encoding="utf-8") == before


def test_grant_create_plan_blocks_invalid_current_registry(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run(state_file)
    state = _load_raw(state_file)
    state["authority_grants"] = {"broken": {"grant_id": "broken"}}
    _save_raw(state_file, state)
    before = state_file.read_text(encoding="utf-8")

    output = commands.dispatch(["authority", "grant-create-plan"])

    assert "current_authority_validation : FAIL" in output
    assert "would_create_valid_record   : no" in output
    assert "current authority registry validation failed" in output
    assert state_file.read_text(encoding="utf-8") == before


def test_grant_create_plan_validator_fail_has_no_plan(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run(state_file)
    store.create_run(
        project="Haunted",
        objective="Invalid work",
        run_id="run-invalid",
    )
    _patch_run(state_file, "run-invalid", status="goblin_mode")
    before = state_file.read_text(encoding="utf-8")

    output = authority_grant_create_plan.format_plan(
        authority_grant_create_plan.plan_grant_create(issued_at=ISSUED_AT)
    )

    assert "validator                    : FAIL" in output
    assert "Plan:\n- (none)" in output
    assert "validator FAIL prevents grant creation planning" in output
    assert state_file.read_text(encoding="utf-8") == before


def test_grant_create_plan_rejects_arguments(tmp_path, monkeypatch):
    _use_tmp_state(tmp_path, monkeypatch)

    try:
        commands.dispatch(["authority", "grant-create-plan", "--create"])
    except ValueError as exc:
        assert "grant-create-plan" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("expected grant-create-plan command to reject args")
