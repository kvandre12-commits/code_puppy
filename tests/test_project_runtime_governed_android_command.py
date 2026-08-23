"""End-to-end command proof for a governed Android intent effect adapter."""

from __future__ import annotations

import json

from code_puppy.plugins.project_runtime import android_execution, commands, store

RUN_ID = "run-android-cli"
GRANT_ID = f"grant:{RUN_ID}:{android_execution.ANDROID_ACTION_SCOPE}"
LEASE_ID = f"lease:{RUN_ID}:{android_execution.ANDROID_ACTION_SCOPE}"


def _use_tmp_state(tmp_path, monkeypatch):
    state_file = tmp_path / "project_runs.json"
    monkeypatch.setattr(store, "STATE_FILE", str(state_file))
    return state_file


def _load_raw(state_file):
    return json.loads(state_file.read_text(encoding="utf-8"))


def _events_by_type(state, event_type: str):
    return [
        event for event in state["events"].values() if event["event_type"] == event_type
    ]


def _create_ready_run():
    return commands.dispatch(
        [
            "run",
            "create",
            RUN_ID,
            "--project",
            "Code Puppy",
            "--objective",
            "Prove governed Android intent effect",
            "--status",
            "ready",
        ]
    )


def test_android_command_uses_same_authority_lease_audit_path(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    launched_commands: list[list[str]] = []

    class Completed:
        returncode = 0

    def fake_run(command, **_kwargs):
        launched_commands.append(list(command))
        return Completed()

    monkeypatch.setattr(android_execution.subprocess, "run", fake_run)

    assert "Created Project Run" in _create_ready_run()
    draft = commands.dispatch(["authority", "grant-draft", "--effect", "android"])
    assert f"grant_id               : {GRANT_ID}" in draft
    assert "allowed_action_scope   : android.launch_activity" in draft
    assert "allowed_capability     : android.activity.settings" in draft

    grant = commands.dispatch(
        ["authority", "grant-create", "--effect", "android", "--confirm", GRANT_ID]
    )
    assert "created                     : yes" in grant
    assert "executes                    : no" in grant

    check = commands.dispatch(["run", "authority-check", "--effect", "android"])
    assert "lease_issuable         : yes" in check
    assert "requested_action_scope : android.launch_activity" in check
    assert "requested_capability   : android.activity.settings" in check

    lease = commands.dispatch(
        ["run", "lease-issue", "--effect", "android", "--confirm", LEASE_ID]
    )
    assert "issued                      : yes" in lease
    assert "creates_audit_event         : yes" in lease
    assert "executes                    : no" in lease

    executed = commands.dispatch(
        [
            "run",
            "execute-android",
            "--confirm",
            LEASE_ID,
            "--component",
            android_execution.APPROVED_COMPONENT,
        ]
    )
    assert "executed                    : yes" in executed
    assert "bounded_effect              : yes" in executed
    assert "consumes_lease              : yes" in executed
    assert "creates_audit_event         : yes" in executed
    assert launched_commands == [
        ["am", "start", "-n", android_execution.APPROVED_COMPONENT]
    ]

    state = _load_raw(state_file)
    lease_record = state["leases"][LEASE_ID]
    assert lease_record["consumed_at"]
    assert lease_record["consumed_event_id"]
    android_events = _events_by_type(state, android_execution.ANDROID_EFFECT_EVENT_TYPE)
    assert len(android_events) == 1
    assert android_events[0]["parent_event_id"] == lease_record["issued_event_id"]
    assert android_execution.APPROVED_COMPONENT in android_events[0]["payload_summary"]

    after_first = _load_raw(state_file)
    second = commands.dispatch(
        [
            "run",
            "execute-android",
            "--confirm",
            LEASE_ID,
            "--component",
            android_execution.APPROVED_COMPONENT,
        ]
    )
    assert "executed                    : no" in second
    assert "lease already consumed" in second
    assert launched_commands == [
        ["am", "start", "-n", android_execution.APPROVED_COMPONENT]
    ]
    assert _load_raw(state_file) == after_first


def test_android_lease_requires_android_effect_selection(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run()
    commands.dispatch(
        ["authority", "grant-create", "--effect", "android", "--confirm", GRANT_ID]
    )
    before = state_file.read_text(encoding="utf-8")

    result = commands.dispatch(["run", "lease-issue", "--confirm", LEASE_ID])

    assert "issued                      : no" in result
    assert "confirmation mismatch" in result
    assert "lease:run-android-cli:project_run.execute_bounded_step" in result
    assert state_file.read_text(encoding="utf-8") == before


def test_android_command_rejects_wrong_component_before_device_effect(
    tmp_path, monkeypatch
):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    launched_commands: list[list[str]] = []
    monkeypatch.setattr(
        android_execution.subprocess,
        "run",
        lambda command, **_kwargs: launched_commands.append(list(command)),
    )

    _create_ready_run()
    commands.dispatch(
        ["authority", "grant-create", "--effect", "android", "--confirm", GRANT_ID]
    )
    commands.dispatch(
        ["run", "lease-issue", "--effect", "android", "--confirm", LEASE_ID]
    )
    before = state_file.read_text(encoding="utf-8")

    result = commands.dispatch(
        [
            "run",
            "execute-android",
            "--confirm",
            LEASE_ID,
            "--component",
            "com.android.settings/.WirelessSettings",
        ]
    )

    assert "executed                    : no" in result
    assert "Android activity scope mismatch" in result
    assert launched_commands == []
    assert state_file.read_text(encoding="utf-8") == before
