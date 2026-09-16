"""Tests for governed Android device-boundary execution."""

from __future__ import annotations

import json

from code_puppy.plugins.project_runtime import android_execution, lease_store, store

RUN_ID = "run-android"
GRANT_ID = f"grant:{RUN_ID}:{android_execution.ANDROID_ACTION_SCOPE}"
LEASE_ID = f"lease:{RUN_ID}:{android_execution.ANDROID_ACTION_SCOPE}"
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
        objective="Launch one governed Android activity",
        run_id=RUN_ID,
        status="ready",
    )


def _create_android_grant():
    grant, _event = store.create_authority_grant_record(
        {
            "grant_id": GRANT_ID,
            "subject_identity": "unassigned_agent",
            "allowed_action_scope": android_execution.ANDROID_ACTION_SCOPE,
            "allowed_capability_scope": android_execution.ANDROID_CAPABILITY_SCOPE,
            "boundary": "project_run",
            "issuer": "operator_required",
            "issued_at": ISSUED_AT,
            "expires_at": EXPIRES_AT,
            "revoked_at": "",
            "project_id": "",
            "run_id": RUN_ID,
            "reason": "Android adapter theorem test",
            "precedent_id": "PRECEDENT-006",
        }
    )
    return grant


def _create_android_lease(
    *,
    action_scope: str = android_execution.ANDROID_ACTION_SCOPE,
    capability_scope: str = android_execution.ANDROID_CAPABILITY_SCOPE,
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
            "reason": "Android adapter theorem test",
        }
    )
    return result.lease


def _create_valid_android_context():
    _create_ready_run()
    _create_android_grant()
    _create_android_lease()


def _events_by_type(state, event_type: str):
    return [
        event for event in state["events"].values() if event["event_type"] == event_type
    ]


def test_android_execution_consumes_scoped_lease_and_audits_approved_activity(
    tmp_path, monkeypatch
):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_valid_android_context()
    launched: list[str] = []

    result = android_execution.execute_android(
        confirm_lease_id=LEASE_ID,
        component=android_execution.APPROVED_COMPONENT,
        launcher=launched.append,
        now_at=NOW_AT,
    )

    assert result.executed
    assert launched == [android_execution.APPROVED_COMPONENT]
    state = _load_raw(state_file)
    lease = state["leases"][LEASE_ID]
    assert lease["consumed_at"]
    assert lease["consumed_event_id"] == result.event_id
    events = _events_by_type(state, android_execution.ANDROID_EFFECT_EVENT_TYPE)
    assert len(events) == 1
    assert events[0]["parent_event_id"] == lease["issued_event_id"]
    assert android_execution.APPROVED_COMPONENT in events[0]["payload_summary"]


def test_android_execution_reused_lease_has_no_second_effect(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_valid_android_context()
    launched: list[str] = []
    first = android_execution.execute_android(
        confirm_lease_id=LEASE_ID,
        component=android_execution.APPROVED_COMPONENT,
        launcher=launched.append,
        now_at=NOW_AT,
    )
    after_first = _load_raw(state_file)

    second = android_execution.execute_android(
        confirm_lease_id=LEASE_ID,
        component=android_execution.APPROVED_COMPONENT,
        launcher=launched.append,
        now_at=NOW_AT,
    )
    after_second = _load_raw(state_file)

    assert first.executed
    assert not second.executed
    assert "lease already consumed" in second.blockers
    assert launched == [android_execution.APPROVED_COMPONENT]
    assert after_second == after_first


def test_android_execution_wrong_activity_has_no_effect_or_mutation(
    tmp_path, monkeypatch
):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_valid_android_context()
    before = state_file.read_text(encoding="utf-8")
    launched: list[str] = []

    result = android_execution.execute_android(
        confirm_lease_id=LEASE_ID,
        component="com.android.settings/.WirelessSettings",
        launcher=launched.append,
        now_at=NOW_AT,
    )

    assert not result.executed
    assert "Android activity scope mismatch" in result.blockers
    assert launched == []
    assert state_file.read_text(encoding="utf-8") == before


def test_android_execution_wrong_lease_scope_has_no_effect_or_mutation(
    tmp_path, monkeypatch
):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run()
    _create_android_grant()
    _create_android_lease(action_scope="android.launch_service")
    before = state_file.read_text(encoding="utf-8")
    launched: list[str] = []

    result = android_execution.execute_android(
        confirm_lease_id=LEASE_ID,
        component=android_execution.APPROVED_COMPONENT,
        launcher=launched.append,
        now_at=NOW_AT,
    )

    assert not result.executed
    assert "lease action scope mismatch" in result.blockers
    assert launched == []
    assert state_file.read_text(encoding="utf-8") == before


def test_android_execution_missing_authority_has_no_effect_or_mutation(
    tmp_path, monkeypatch
):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run()
    _create_android_lease()
    before = state_file.read_text(encoding="utf-8")
    launched: list[str] = []

    result = android_execution.execute_android(
        confirm_lease_id=LEASE_ID,
        component=android_execution.APPROVED_COMPONENT,
        launcher=launched.append,
        now_at=NOW_AT,
    )

    assert not result.executed
    assert "matching active authority grant missing" in result.blockers
    assert launched == []
    assert state_file.read_text(encoding="utf-8") == before


def test_android_execution_expired_lease_has_no_effect_or_mutation(
    tmp_path, monkeypatch
):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_valid_android_context()
    state = _load_raw(state_file)
    state["leases"][LEASE_ID]["expires_at"] = "2000-01-01T00:00:00+00:00"
    _save_raw(state_file, state)
    before = state_file.read_text(encoding="utf-8")
    launched: list[str] = []

    result = android_execution.execute_android(
        confirm_lease_id=LEASE_ID,
        component=android_execution.APPROVED_COMPONENT,
        launcher=launched.append,
        now_at=NOW_AT,
    )

    assert not result.executed
    assert "lease expired" in result.blockers
    assert launched == []
    assert state_file.read_text(encoding="utf-8") == before


def test_android_execution_revoked_authority_has_no_effect_or_mutation(
    tmp_path, monkeypatch
):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_valid_android_context()
    state = _load_raw(state_file)
    state["authority_grants"][GRANT_ID]["revoked_at"] = "2026-01-01T00:00:30+00:00"
    _save_raw(state_file, state)
    before = state_file.read_text(encoding="utf-8")
    launched: list[str] = []

    result = android_execution.execute_android(
        confirm_lease_id=LEASE_ID,
        component=android_execution.APPROVED_COMPONENT,
        launcher=launched.append,
        now_at=NOW_AT,
    )

    assert not result.executed
    assert "matching active authority grant missing" in result.blockers
    assert launched == []
    assert state_file.read_text(encoding="utf-8") == before


def test_android_execution_missing_lease_has_no_effect(tmp_path, monkeypatch):
    _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run()
    _create_android_grant()
    launched: list[str] = []

    result = android_execution.execute_android(
        confirm_lease_id=LEASE_ID,
        component=android_execution.APPROVED_COMPONENT,
        launcher=launched.append,
        now_at=NOW_AT,
    )

    assert not result.executed
    assert result.blockers == ("lease missing",)
    assert launched == []


def test_android_execution_launcher_failure_has_no_audit_or_lease_consumption(
    tmp_path, monkeypatch
):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_valid_android_context()
    before = state_file.read_text(encoding="utf-8")
    attempted: list[str] = []

    def fail_launch(component: str) -> bool:
        attempted.append(component)
        return False

    result = android_execution.execute_android(
        confirm_lease_id=LEASE_ID,
        component=android_execution.APPROVED_COMPONENT,
        launcher=fail_launch,
        now_at=NOW_AT,
    )

    assert not result.executed
    assert result.blockers == ("Android launcher failed",)
    assert attempted == [android_execution.APPROVED_COMPONENT]
    assert state_file.read_text(encoding="utf-8") == before
