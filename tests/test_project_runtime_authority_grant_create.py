"""Tests for confirmed AuthorityGrant creation."""

from __future__ import annotations

import json

from code_puppy.plugins.project_runtime import (
    authority_check,
    authority_grant_create,
    authority_grant_create_plan,
    authority_validator,
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


def test_grant_create_requires_exact_confirmation(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run(state_file)
    before = state_file.read_text(encoding="utf-8")

    result = authority_grant_create.create_authority_grant(
        confirm_grant_id="wrong-grant",
        issued_at=ISSUED_AT,
    )
    output = authority_grant_create.format_result(result)

    assert not result.created
    assert "created                     : no" in output
    assert "confirmation mismatch" in output
    assert "mutates                     : no" in output
    assert state_file.read_text(encoding="utf-8") == before


def test_grant_create_persists_grant_and_audit_event(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run(state_file)
    plan = authority_grant_create_plan.plan_grant_create()
    assert plan.would_create_valid_record

    result = authority_grant_create.create_authority_grant(
        confirm_grant_id=GRANT_ID,
    )
    output = authority_grant_create.format_result(result)

    assert result.created
    assert result.grant_id == GRANT_ID
    assert result.run_id == "run-eligible"
    assert result.event_id.startswith("evt-")
    assert "created                     : yes" in output
    assert "creates_grant               : yes" in output
    assert "mutates                     : yes" in output
    assert "creates_audit_event         : yes" in output
    assert "authorizes                  : no" in output
    assert "wakes                       : no" in output
    assert "leases                      : no" in output
    assert "executes                    : no" in output
    state = _load_raw(state_file)
    assert state["authority_grants"][GRANT_ID]["run_id"] == "run-eligible"
    events = [
        event
        for event in state["events"].values()
        if event["event_type"] == "authority_grant_created"
    ]
    assert len(events) == 1
    assert events[0]["run_id"] == "run-eligible"
    assert events[0]["payload_summary"] == f"AuthorityGrant created: {GRANT_ID}"
    assert authority_validator.validate_authority().passed
    assert authority_check.check_authority().lease_issuable


def test_grant_create_command_requires_confirm_flag(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run(state_file)
    before = state_file.read_text(encoding="utf-8")

    try:
        commands.dispatch(["authority", "grant-create"])
    except ValueError as exc:
        assert "grant-create requires --confirm <grant_id>" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("expected grant-create to require confirmation")
    assert state_file.read_text(encoding="utf-8") == before


def test_grant_create_command_creates_once_then_blocks_duplicate(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run(state_file)

    first = commands.dispatch(["authority", "grant-create", "--confirm", GRANT_ID])
    after_first = _load_raw(state_file)
    second = commands.dispatch(["authority", "grant-create", "--confirm", GRANT_ID])
    after_second = _load_raw(state_file)

    assert "created                     : yes" in first
    assert "created                     : no" in second
    assert "grant_id already exists" in second
    assert len(after_first["authority_grants"]) == 1
    assert after_second["authority_grants"] == after_first["authority_grants"]
    assert after_second["events"] == after_first["events"]


def test_grant_create_blocks_invalid_registry_without_mutation(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run(state_file)
    state = _load_raw(state_file)
    state["authority_grants"] = {"broken": {"grant_id": "broken"}}
    _save_raw(state_file, state)
    before = state_file.read_text(encoding="utf-8")

    result = authority_grant_create.create_authority_grant(
        confirm_grant_id=GRANT_ID,
        issued_at=ISSUED_AT,
    )

    assert not result.created
    assert "current authority registry validation failed" in result.blockers
    assert state_file.read_text(encoding="utf-8") == before
