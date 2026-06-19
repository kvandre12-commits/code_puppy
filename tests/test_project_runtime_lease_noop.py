"""Tests for lease issuance and one-shot no-op execution."""

from __future__ import annotations

import json

import pytest

from code_puppy.plugins.project_runtime import (
    authority_grant_create,
    commands,
    lease_issue,
    lease_store,
    noop_execution,
    store,
)

GRANT_ID = "grant:run-eligible:project_run.execute_bounded_step"
LEASE_ID = "lease:run-eligible:project_run.execute_bounded_step"


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


def _create_grant():
    result = authority_grant_create.create_authority_grant(confirm_grant_id=GRANT_ID)
    assert result.created
    return result


def _issue_lease():
    result = lease_issue.issue_lease(confirm_lease_id=LEASE_ID)
    assert result.issued
    return result


def _events_by_type(state, event_type: str):
    return [
        event for event in state["events"].values() if event["event_type"] == event_type
    ]


def test_lease_issue_blocks_without_authority_and_does_not_mutate(
    tmp_path, monkeypatch
):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run(state_file)
    before = state_file.read_text(encoding="utf-8")

    output = commands.dispatch(["run", "lease-issue", "--confirm", LEASE_ID])

    assert "issued                      : no" in output
    assert "authority grant for requested action scope missing" in output
    assert "capability grant for requested capability scope missing" in output
    assert state_file.read_text(encoding="utf-8") == before


def test_lease_issue_requires_exact_confirmation(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run(state_file)
    _create_grant()
    before = state_file.read_text(encoding="utf-8")

    result = lease_issue.issue_lease(confirm_lease_id="wrong-lease")

    assert not result.issued
    assert "confirmation mismatch" in result.blockers
    assert state_file.read_text(encoding="utf-8") == before


def test_lease_issue_persists_one_lease_and_audit_without_execution(
    tmp_path, monkeypatch
):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run(state_file)
    _create_grant()

    output = commands.dispatch(["run", "lease-issue", "--confirm", LEASE_ID])

    assert "issued                      : yes" in output
    assert "creates_lease               : yes" in output
    assert "creates_audit_event         : yes" in output
    assert "executes                    : no" in output
    state = _load_raw(state_file)
    assert state["leases"][LEASE_ID]["run_id"] == "run-eligible"
    assert state["leases"][LEASE_ID]["consumed_at"] == ""
    assert len(_events_by_type(state, "lease_issued")) == 1
    assert _events_by_type(state, "noop_executed") == []


def test_lease_issue_duplicate_blocks_without_extra_event(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run(state_file)
    _create_grant()
    _issue_lease()
    after_first = _load_raw(state_file)

    second = commands.dispatch(["run", "lease-issue", "--confirm", LEASE_ID])
    after_second = _load_raw(state_file)

    assert "issued                      : no" in second
    assert "lease_id already exists" in second
    assert after_second["leases"] == after_first["leases"]
    assert after_second["events"] == after_first["events"]


def test_generic_lease_consumption_writes_one_bounded_effect_event(
    tmp_path, monkeypatch
):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run(state_file)
    _create_grant()
    _issue_lease()
    lease = lease_store.get_lease(LEASE_ID)

    result = lease_store.consume_lease_for_effect(
        lease,
        event_type="noop_executed",
        payload_summary="Adapter effect executed under lease",
    )

    state = _load_raw(state_file)
    lease = state["leases"][LEASE_ID]
    assert result.lease.consumed_at
    assert lease["consumed_event_id"] == result.event.event_id
    assert result.event.event_type == "noop_executed"
    assert result.event.parent_event_id == lease["issued_event_id"]
    assert result.event.payload_summary == "Adapter effect executed under lease"


def test_generic_lease_consumption_rejects_unknown_event_type_without_mutation(
    tmp_path, monkeypatch
):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run(state_file)
    _create_grant()
    _issue_lease()
    lease = lease_store.get_lease(LEASE_ID)
    before = state_file.read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="unknown event type"):
        lease_store.consume_lease_for_effect(
            lease,
            event_type="browser_did_magic",
            payload_summary="Bad adapter event",
        )

    assert state_file.read_text(encoding="utf-8") == before


def test_execute_noop_consumes_valid_lease_and_writes_one_audit_event(
    tmp_path, monkeypatch
):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run(state_file)
    _create_grant()
    _issue_lease()

    output = commands.dispatch(["run", "execute-noop", "--confirm", LEASE_ID])

    assert "executed                    : yes" in output
    assert "bounded_effect              : yes" in output
    assert "consumes_lease              : yes" in output
    assert "creates_audit_event         : yes" in output
    assert "creates_grant               : no" in output
    assert "leases                      : no" in output
    state = _load_raw(state_file)
    lease = state["leases"][LEASE_ID]
    assert lease["consumed_at"]
    assert lease["consumed_event_id"]
    noop_events = _events_by_type(state, "noop_executed")
    assert len(noop_events) == 1
    assert noop_events[0]["parent_event_id"] == lease["issued_event_id"]
    assert state["runs"]["run-eligible"]["status"] == "ready"


def test_execute_noop_missing_lease_has_no_effect(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run(state_file)
    _create_grant()
    before = state_file.read_text(encoding="utf-8")

    result = noop_execution.execute_noop(confirm_lease_id=LEASE_ID)

    assert not result.executed
    assert result.blockers == ("lease missing",)
    assert state_file.read_text(encoding="utf-8") == before


def test_execute_noop_expired_lease_has_no_effect(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run(state_file)
    _create_grant()
    _issue_lease()
    state = _load_raw(state_file)
    state["leases"][LEASE_ID]["expires_at"] = "2000-01-01T00:00:00+00:00"
    _save_raw(state_file, state)
    before = state_file.read_text(encoding="utf-8")

    output = commands.dispatch(["run", "execute-noop", "--confirm", LEASE_ID])

    assert "executed                    : no" in output
    assert "lease expired" in output
    assert state_file.read_text(encoding="utf-8") == before


def test_execute_noop_reused_lease_has_no_second_effect(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run(state_file)
    _create_grant()
    _issue_lease()
    first = commands.dispatch(["run", "execute-noop", "--confirm", LEASE_ID])
    after_first = _load_raw(state_file)

    second = commands.dispatch(["run", "execute-noop", "--confirm", LEASE_ID])
    after_second = _load_raw(state_file)

    assert "executed                    : yes" in first
    assert "executed                    : no" in second
    assert "lease already consumed" in second
    assert after_second == after_first


def test_execute_noop_revoked_authority_has_no_effect(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run(state_file)
    _create_grant()
    _issue_lease()
    state = _load_raw(state_file)
    state["authority_grants"][GRANT_ID]["revoked_at"] = "2099-01-01T00:00:00+00:00"
    _save_raw(state_file, state)
    before = state_file.read_text(encoding="utf-8")

    output = commands.dispatch(["run", "execute-noop", "--confirm", LEASE_ID])

    assert "executed                    : no" in output
    assert "matching active authority grant missing" in output
    assert state_file.read_text(encoding="utf-8") == before
