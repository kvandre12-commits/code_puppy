"""Tests for governed browser effect execution."""

from __future__ import annotations

import json

from code_puppy.plugins.project_runtime import browser_execution, lease_store, store

RUN_ID = "run-browser"
GRANT_ID = f"grant:{RUN_ID}:{browser_execution.BROWSER_ACTION_SCOPE}"
LEASE_ID = f"lease:{RUN_ID}:{browser_execution.BROWSER_ACTION_SCOPE}"
ISSUED_AT = "2026-01-01T00:00:00+00:00"
EXPIRES_AT = "2026-01-01T00:15:00+00:00"
NOW_AT = "2026-01-01T00:01:00+00:00"


def _use_tmp_state(tmp_path, monkeypatch):
    state_file = tmp_path / "project_runs.json"
    monkeypatch.setattr(store, "STATE_FILE", str(state_file))
    return state_file


def _load_raw(state_file):
    return json.loads(state_file.read_text(encoding="utf-8"))


def _save_raw(state_file, state):
    state_file.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def _create_ready_run():
    store.create_run(
        project="Code Puppy",
        objective="Open one governed browser URL",
        run_id=RUN_ID,
        status="ready",
    )


def _create_browser_grant():
    grant, _event = store.create_authority_grant_record(
        {
            "grant_id": GRANT_ID,
            "subject_identity": "unassigned_agent",
            "allowed_action_scope": browser_execution.BROWSER_ACTION_SCOPE,
            "allowed_capability_scope": browser_execution.BROWSER_CAPABILITY_SCOPE,
            "boundary": "project_run",
            "issuer": "operator_required",
            "issued_at": ISSUED_AT,
            "expires_at": EXPIRES_AT,
            "revoked_at": "",
            "project_id": "",
            "run_id": RUN_ID,
            "reason": "browser adapter theorem test",
            "precedent_id": "PRECEDENT-006",
        }
    )
    return grant


def _create_browser_lease(
    *,
    action_scope: str = browser_execution.BROWSER_ACTION_SCOPE,
    capability_scope: str = browser_execution.BROWSER_CAPABILITY_SCOPE,
):
    result = lease_store.create_lease_record(
        {
            "lease_id": LEASE_ID,
            "run_id": RUN_ID,
            "subject_identity": "unassigned_agent",
            "action_scope": action_scope,
            "capability_scope": capability_scope,
            "issued_at": ISSUED_AT,
            "expires_at": EXPIRES_AT,
            "consumed_at": "",
            "issued_event_id": "",
            "consumed_event_id": "",
            "reason": "browser adapter theorem test",
        }
    )
    return result.lease


def _create_valid_browser_context():
    _create_ready_run()
    _create_browser_grant()
    _create_browser_lease()


def _events_by_type(state, event_type: str):
    return [
        event for event in state["events"].values() if event["event_type"] == event_type
    ]


def test_browser_execution_consumes_scoped_lease_and_audits_exact_url(
    tmp_path, monkeypatch
):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_valid_browser_context()
    opened: list[str] = []

    result = browser_execution.execute_browser(
        confirm_lease_id=LEASE_ID,
        url=browser_execution.ALLOWED_URL,
        opener=opened.append,
        now_at=NOW_AT,
    )

    assert result.executed
    assert opened == [browser_execution.ALLOWED_URL]
    state = _load_raw(state_file)
    lease = state["leases"][LEASE_ID]
    assert lease["consumed_at"]
    assert lease["consumed_event_id"] == result.event_id
    events = _events_by_type(state, browser_execution.BROWSER_EFFECT_EVENT_TYPE)
    assert len(events) == 1
    assert events[0]["parent_event_id"] == lease["issued_event_id"]
    assert browser_execution.ALLOWED_URL in events[0]["payload_summary"]


def test_browser_execution_reused_lease_has_no_second_effect(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_valid_browser_context()
    opened: list[str] = []
    first = browser_execution.execute_browser(
        confirm_lease_id=LEASE_ID,
        url=browser_execution.ALLOWED_URL,
        opener=opened.append,
        now_at=NOW_AT,
    )
    after_first = _load_raw(state_file)

    second = browser_execution.execute_browser(
        confirm_lease_id=LEASE_ID,
        url=browser_execution.ALLOWED_URL,
        opener=opened.append,
        now_at=NOW_AT,
    )
    after_second = _load_raw(state_file)

    assert first.executed
    assert not second.executed
    assert "lease already consumed" in second.blockers
    assert opened == [browser_execution.ALLOWED_URL]
    assert after_second == after_first


def test_browser_execution_wrong_url_has_no_effect_or_mutation(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_valid_browser_context()
    before = state_file.read_text(encoding="utf-8")
    opened: list[str] = []

    result = browser_execution.execute_browser(
        confirm_lease_id=LEASE_ID,
        url="https://example.org/",
        opener=opened.append,
        now_at=NOW_AT,
    )

    assert not result.executed
    assert "browser URL scope mismatch" in result.blockers
    assert opened == []
    assert state_file.read_text(encoding="utf-8") == before


def test_browser_execution_wrong_lease_scope_has_no_effect_or_mutation(
    tmp_path, monkeypatch
):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run()
    _create_browser_grant()
    _create_browser_lease(action_scope="browser.open_tab")
    before = state_file.read_text(encoding="utf-8")
    opened: list[str] = []

    result = browser_execution.execute_browser(
        confirm_lease_id=LEASE_ID,
        url=browser_execution.ALLOWED_URL,
        opener=opened.append,
        now_at=NOW_AT,
    )

    assert not result.executed
    assert "lease action scope mismatch" in result.blockers
    assert opened == []
    assert state_file.read_text(encoding="utf-8") == before


def test_browser_execution_missing_authority_has_no_effect_or_mutation(
    tmp_path, monkeypatch
):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run()
    _create_browser_lease()
    before = state_file.read_text(encoding="utf-8")
    opened: list[str] = []

    result = browser_execution.execute_browser(
        confirm_lease_id=LEASE_ID,
        url=browser_execution.ALLOWED_URL,
        opener=opened.append,
        now_at=NOW_AT,
    )

    assert not result.executed
    assert "matching active authority grant missing" in result.blockers
    assert opened == []
    assert state_file.read_text(encoding="utf-8") == before


def test_browser_execution_expired_lease_has_no_effect_or_mutation(
    tmp_path, monkeypatch
):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_valid_browser_context()
    state = _load_raw(state_file)
    state["leases"][LEASE_ID]["expires_at"] = "2000-01-01T00:00:00+00:00"
    _save_raw(state_file, state)
    before = state_file.read_text(encoding="utf-8")
    opened: list[str] = []

    result = browser_execution.execute_browser(
        confirm_lease_id=LEASE_ID,
        url=browser_execution.ALLOWED_URL,
        opener=opened.append,
        now_at=NOW_AT,
    )

    assert not result.executed
    assert "lease expired" in result.blockers
    assert opened == []
    assert state_file.read_text(encoding="utf-8") == before


def test_browser_execution_revoked_authority_has_no_effect_or_mutation(
    tmp_path, monkeypatch
):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_valid_browser_context()
    state = _load_raw(state_file)
    state["authority_grants"][GRANT_ID]["revoked_at"] = "2026-01-01T00:00:30+00:00"
    _save_raw(state_file, state)
    before = state_file.read_text(encoding="utf-8")
    opened: list[str] = []

    result = browser_execution.execute_browser(
        confirm_lease_id=LEASE_ID,
        url=browser_execution.ALLOWED_URL,
        opener=opened.append,
        now_at=NOW_AT,
    )

    assert not result.executed
    assert "matching active authority grant missing" in result.blockers
    assert opened == []
    assert state_file.read_text(encoding="utf-8") == before


def test_browser_execution_missing_lease_has_no_effect(tmp_path, monkeypatch):
    _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run()
    _create_browser_grant()
    opened: list[str] = []

    result = browser_execution.execute_browser(
        confirm_lease_id=LEASE_ID,
        url=browser_execution.ALLOWED_URL,
        opener=opened.append,
        now_at=NOW_AT,
    )

    assert not result.executed
    assert result.blockers == ("lease missing",)
    assert opened == []
